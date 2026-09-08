"""Read-only index over the canonical public scientific relationship graph.

The index never derives scientific membership from labels, finding-wide joins,
or presentation data.  Direct placement comes only from the graph's explicitly
projectable placement edges; context remains separately discoverable.
"""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from functools import cache
import hashlib
import json
from pathlib import Path
import sqlite3


GRAPH_SCHEMA_VERSION = "atlas-normalized-relationship-graph-1.17.0"
ACTIVE_MAPPING_STATUSES = {"EXACT_SOURCE", "OWNER_APPROVED"}
REFERENCE_CONTEXT_REGION = "Background literature"
OTHER_LOCALIZATION_REGION = "Other brain region / localization"
UNLINKED_LOCALIZATION_REGION = "No linked localization"
REFERENCE_MAPPING_STATUSES = {
    *ACTIVE_MAPPING_STATUSES, "DETERMINISTIC_EXACT_LABEL", "SOURCE_EXPLICIT",
}
OWNER_REVIEW_REFERENCE_KINDS = {
    "FINDING_SIGN", "OCCURRENCE_SIGN", "SOURCE_SIGN_REVIEW_TOKEN",
    "STATISTIC_OCCURRENCE", "STATISTIC_SIGN",
}
PHASE_MAPPING_STATUSES = {
    "EXACT_SOURCE", "OWNER_APPROVED", "SOURCE_NATIVE_UNGROUPED",
}
ANATOMY_MAPPING_STATUSES = {*ACTIVE_MAPPING_STATUSES, "SOURCE_EXPLICIT"}
LATERALIZATION_LABELS = {
    "contra": "Contralateral", "ipsi": "Ipsilateral",
    "dominant": "Dominant hemisphere", "nondominant": "Non-dominant hemisphere",
    "left": "Left hemisphere", "right": "Right hemisphere",
    "bilateral": "Bilateral", "nonlat": "Does not lateralize",
    "variable": "Variable lateralization",
    "unspecified": "Side unspecified",
}
PRESENTATION_DISPOSITIONS = {
    "PRIMARY_RESULT_PLACEMENT", "REFERENCE_CONTEXT",
}
DIRECT_RELATION_SCOPES = {
    "SIGN_OCCURRENCE": {
        "SOURCE_REPORTED", "ONSET", "SYMPTOMATOGENIC", "STIMULATION",
        "LESION", "NETWORK",
    },
}
PHASE_REFERENCE_KINDS = {
    "FINDING_PHASE": "FINDING",
    "STATISTIC_PHASE": "STATISTIC",
    "OCCURRENCE_PHASE": "SIGN_OCCURRENCE",
    "SIGN_PHASE": "SIGN",
}
ANATOMY_DISPLAY_REGION_BASES = (
    "DIRECT_MAJOR_REGION_IDENTITY",
    "EXPLICIT_ONE_HOP_ANATOMY_RELATIONSHIP",
    "EXPLICIT_PARENT_REGION_RELATIONSHIP",
    "EXPLICIT_SOURCE_ANALYTIC_REGION",
    "OWNER_APPROVED_ATLAS_DISPLAY_ASSIGNMENT",
)
PLACEMENT_EDGE_FIELDS = (
    "placement_edge_id", "evidence_link_id", "source_evidence_link_id",
    "subject_kind",
    "evidence_context_id", "finding_ref", "sign_id", "source_sign_id",
    "occurrence_id", "sequence_component_id", "sequence_id", "ordinal",
    "simultaneous_group_id", "alternative_group_id", "source_role",
    "assertion_id", "axis", "relation_scope", "target_kind", "anatomy_id",
    "display_region_link_id", "display_region_id", "display_region_basis",
    "lateralization_code", "target_usable", "source_id", "source_sha256", "source_version",
    "locator", "source_excerpt", "source_native_sign_term",
    "source_native_axis_text", "source_native_axis_text_status",
    "source_native_locator", "mapping_lineage",
    "evidence_role", "evidence_partition", "independent_evidence",
    "presentation_disposition", "projectable", "mapping_status",
    "projectability_basis", "activation_state",
    "migration_origin",
)
MEMBERSHIP_EDGE_FIELDS = (
    "membership_edge_id", "public_sign_id", "axis", "finding_ref",
    "statistic_id", "source_work_id", "evidence_context_id",
    "source_sign_id", "result_occurrence_id", "ownership_kind",
    "ownership_id", "sign_relation", "sign_mapping_status",
    "relationship_disposition", "target_usable", "evidence_role",
    "evidence_partition", "independent_evidence", "presentation_disposition",
)
MEMBERSHIP_OWNERSHIP_KINDS = {
    "COHORT_FALLBACK_EVIDENCE", "SUBJECT_AXIS_EVIDENCE",
    "STATISTIC_AXIS_EVIDENCE_CONTEXT",
}
MEMBERSHIP_DISPOSITIONS = {
    "ATOMIC_AXIS_EVIDENCE", "COHORT_FALLBACK_RELATIONSHIP",
    "DIRECT_TARGET_RELATIONSHIP", "EXPLICIT_NONASSOCIATION",
    "EXPLICIT_NO_USABLE_TARGET", "NONPROJECTABLE_AXIS_EVIDENCE",
}
OWNERSHIP_RECEIPT_FIELDS = (
    "ownership_id", "ownership_kind", "evidence_context_id", "assertion_id",
    "subject_kind", "finding_ref", "source_sign_id", "occurrence_id", "axis",
    "relation_scope", "target_kind", "anatomy_id", "lateralization_code",
    "target_usable", "projectable", "projectability_basis", "mapping_status",
    "activation_state", "source_evidence_link_id", "source_id",
    "source_sha256", "source_version", "locator", "source_excerpt",
    "source_native_sign_term", "source_native_axis_text",
    "source_native_axis_text_status", "source_native_locator",
    "mapping_lineage", "evidence_role", "evidence_partition",
    "independent_evidence", "presentation_disposition",
    "migration_origin", "relationship_disposition",
)
CLASSIFICATION_ASSIGNMENT_FIELDS = (
    "assignment_id", "public_sign_id", "scheme_id", "node_id",
    "resolution_status", "hierarchy_path_node_ids",
)
WEIGHTED_AXIS_SUMMARY_FIELDS = (
    "summary_id", "public_sign_id", "axis", "preferred_label",
    "pattern_status", "pattern_label", "plain_summary",
    "categorization_state", "relationship_ids", "target_relationship_ids",
    "primary_target_relationship_ids", "reference_context_relationship_ids",
    "modifier_relationship_ids", "contributions",
)
WEIGHTED_CONTRIBUTION_FIELDS = (
    "contribution_id", "work_id", "relationship_ids",
    "target_relationship_ids", "statistic_ids", "evidence_roles",
    "evidence_partitions", "evidence_class", "authority_category",
    "weight_components", "potential_weight", "final_weight", "weight_status",
)
CLASSIFICATION_SOURCE_MAPPING_FIELDS = (
    "source_node_id", "source_scheme_id", "public_node_id", "relation",
    "mapping_status", "registry_sha256", "provenance", "activation_state",
)
CLASSIFICATION_TERMINOLOGY_FIELDS = (
    "terminology_evidence_id", "source_node_id", "source_scheme_id",
    "public_scheme_id", "public_node_id", "relation", "mapping_status",
    "source_id", "source_sha256", "source_path", "source_native_term",
    "source_native_statement", "source_locators", "source_attributes",
    "registry_sha256", "review_sha256", "integration_manifest_sha256",
    "mapping_lineage", "activation_state",
)
CITATION_LINK_FIELDS = (
    "citation_link_id", "citation_id", "finding_ref", "evidence_role",
    "citation_relation", "citation_as_printed", "source_locator",
    "source_excerpt", "cited_work_id", "resolution_status",
    "resolution_basis", "independent_evidence", "activation_state",
)
STATISTIC_OCCURRENCE_ASSIGNMENT_FIELDS = (
    "assignment_id", "statistic_id", "finding_ref", "source_sign_id",
    "source_sign_relation", "result_occurrence_id", "public_sign_id",
    "resolution_status", "resolution_basis", "mapping_status",
    "candidate_result_occurrence_ids", "source_native_statistic_text",
    "source_native_locator", "source_native_excerpt", "evidence_role",
    "evidence_partition", "independent_evidence", "provenance",
    "activation_state",
)
COHORT_FALLBACK_ASSERTION_FIELDS = (
    "fallback_assertion_id", "context_evidence_link_id", "assertion_id",
    "evidence_context_id", "finding_ref", "axis", "anatomy_id",
    "display_region_link_id", "display_region_id", "display_region_basis",
    "lateralization_code", "target_usable", "relation_scope", "fallback_status",
    "superseding_placement_edge_ids", "searchable",
    "source_native_axis_text", "source_native_axis_text_status",
    "source_native_locator", "mapping_lineage", "evidence_role",
    "evidence_partition", "independent_evidence", "presentation_disposition",
    "projectable",
    "activation_state",
)
COHORT_FALLBACK_OCCURRENCE_REFERENCE_FIELDS = (
    "occurrence_reference_id", "fallback_assertion_id",
    "context_evidence_link_id", "assertion_id", "identity_edge_id",
    "result_occurrence_id", "finding_ref", "source_sign_id", "public_sign_id",
    "fallback_status", "superseding_placement_edge_ids", "searchable",
    "target_usable", "source_native_sign_term", "mapping_lineage", "evidence_role",
    "evidence_partition", "independent_evidence", "presentation_disposition",
    "activation_state",
)
RESULT_RELATIONSHIP_FIELDS = (
    "relationship_id", "relationship_kind", "work_id", "report_id",
    "work_title", "work_authors", "work_publication_year", "work_citation_text",
    "bibliography_status", "source_attribution_status",
    "cited_work_occurrences", "report_unit_id",
    "report_unit_label", "report_document_class", "report_evidence_class",
    "result_occurrence_id", "source_version", "public_sign_id", "axis",
    "source_native_sign_term", "source_native_relationship_term",
    "source_native_term_status", "source_locator", "source_excerpt",
    "dictionary_domain", "dictionary_item_id", "relationship_role",
    "relationship_status", "evidence_role", "evidence_partition",
    "independent_evidence", "presentation_disposition", "target_usable",
    "projectable", "statistic_ids", "finding_ref", "result_component_id",
    "context_modifier_ids",
)
RESULT_RELATIONSHIP_KINDS = (
    "SIGN_IDENTITY", "AXIS_EVIDENCE", "COHORT_FALLBACK", "PHASE",
    "OCCURRENCE_CLASSIFICATION", "STATISTIC_REFERENCE", "CONTEXT_MODIFIER",
)
CITED_WORK_OCCURRENCE_FIELDS = (
    "citation_relation", "citation_as_printed", "source_locator",
    "source_excerpt", "cited_work_id", "work_title", "work_authors",
    "work_publication_year", "work_citation_text", "bibliography_status",
)
ANATOMY_EVIDENCE_TRAVERSAL_FIELDS = (
    "traversal_id", "owner_relationship_id", "source_anatomy_node_id",
    "target_anatomy_node_id",
    "target_atlas_family_id", "target_atlas_native_id", "target_anatomy_label",
    "hop_count", "path_relationship_ids", "path_anatomy_node_ids",
    "path_anatomy_node_labels", "organizational_only", "discoverable",
    "retrieval_scope", "path_relations", "path_directions",
)
PUBLIC_NODE_FIELDS = {
    "event_groups": ("node_kind", "node_id", "label", "ordinal", "members"),
    "signs": (
        "node_kind", "node_id", "label", "sign_id", "identity_kind",
    ),
    "statistics": (
        "node_kind", "node_id", "label", "statistic_id", "measure",
        "numerator", "denominator", "analysis_unit", "comparator",
        "uncertainty", "uncertainty_details", "metric_type", "value_text",
        "numeric_value", "unit", "numerator_value", "denominator_value",
        "population", "subgroup", "timepoint", "endpoint", "phase",
        "anatomy_laterality_context", "evidence_role", "evidence_partition",
        "independent_evidence", "citation", "source_locator",
        "source_excerpt", "restates_statistic_id", "citation_storage_role",
    ),
    "anatomy": (
        "node_kind", "node_id", "label", "anatomy_node_id",
        "atlas_family_id", "atlas_native_id", "parent_node_id",
        "major_region_anatomy_node_id", "display_region_id",
        "atlas_id", "atlas_version", "source_native_definition", "source_locator",
    ),
    "classifications": (
        "node_kind", "node_id", "label", "classification_node_id",
        "scheme_id", "parent_node_id", "node_type", "ordinal",
    ),
    "phases": (
        "node_kind", "node_id", "label", "phase_id", "phase_code",
        "ordinal",
    ),
}
CONTEXT_LOCAL_AXIS_FIELDS = (
    "context_axis_join_id", "result_evidence_context_id",
    "result_occurrence_id", "finding_ref", "source_sha256", "public_sign_id",
    "localization_relationship_kind", "localization_relationship_id",
    "localization_evidence_context_id", "anatomy_id",
    "localization_relation_scope", "lateralization_relationship_kind",
    "lateralization_relationship_id", "lateralization_evidence_context_id",
    "lateralization_code", "lateralization_relation_scope", "join_status",
)
SOURCE_ANATOMY_CONTEXT_FIELDS = (
    "evidence_link_id", "finding_ref", "result_occurrence_id", "work_id",
    "report_id", "public_sign_id", "source_native_sign_term",
    "source_native_anatomy_term", "source_native_term_status",
    "source_locator", "source_excerpt", "relationship_role",
    "relationship_status", "anatomy_node_id", "evidence_role",
    "context_kind", "retrieval_scope", "evidence_partition",
    "presentation_disposition", "target_usable", "projectable",
    "statistic_ids", "result_component_id",
)

GRAPH_PAYLOAD_FIELDS = (
    "schema_version", "projection_contract", "nodes", "result_relationships",
    "classification_assignments", "anatomy_evidence_traversals",
    "source_anatomy_contexts", "weighted_axis_summaries", "release",
    "semantic_digest",
)
GRAPH_DIGEST_FIELDS = (
    "nodes", "projection_contract", "result_relationships",
    "classification_assignments", "anatomy_evidence_traversals",
    "source_anatomy_contexts", "weighted_axis_summaries",
)
PROJECTION_CONTRACT = {
    "result_relationship_contract": {
        "authoritative_graph_group": "result_relationships",
        "authoritative_database_view": "public_result_scientific_relationship",
        "field_order": list(RESULT_RELATIONSHIP_FIELDS),
        "owner_tuple": [
            "work_id", "report_id", "finding_ref", "result_occurrence_id",
            "result_component_id",
        ],
        "cited_work_occurrence_contract": {
            "field_order": list(CITED_WORK_OCCURRENCE_FIELDS),
            "source_native_citation_fallback": {
                "evidence_partition": "BACKGROUND_LITERATURE",
                "citation_text_source": "EXACT_SOURCE_NATIVE_CITATION_AS_PRINTED",
                "public_text_fields": [
                    "citation_as_printed", "work_citation_text",
                ],
                "structured_identity_fields": "NULL",
                "host_work_identity_unchanged": True,
            },
        },
        "source_native_tuple": [
            "source_native_sign_term", "source_native_relationship_term",
            "source_native_term_status", "source_locator", "source_excerpt",
        ],
        "unatomized_relationship_term_contract": (
            "NULL_RELATIONSHIP_TERM_ONLY_WHEN_STATUS_IS_"
            "UNAVAILABLE_NOT_ATOMICALLY_STORED_AND_EXACT_OWNER_TUPLE_"
            "RETAINS_SOURCE_LOCATOR_EXCERPT_AND_TYPED_TARGET_AUTHORITY;"
            "KINDS_AXIS_OR_EXPLICIT_PHASE_NOT_REPORTED"
        ),
        "dictionary_tuple": ["dictionary_domain", "dictionary_item_id"],
        "statistic_values_duplicated": False,
        "statistic_reference_field": "statistic_ids",
        "legacy_relationship_tables_are_active_authority": False,
    },
    "axis_target_usability": {
        "field": "target_usable", "field_type": "JSON_BOOLEAN",
        "localization": "ACTIVE_NON_NULL_ANATOMY_NODE_REQUIRED",
        "lateralization": "NON_NULL_CODE_OTHER_THAN_UNSPECIFIED",
        "explicit_nonassociation_code": "nonlat",
        "surfaces": [
            "direct_placement_edges", "context_placement_edges",
            "axis_evidence_ownership_receipts",
            "axis_evidence_membership_edges", "cohort_fallback_assertions",
            "cohort_fallback_occurrence_references", "result_relationships",
        ],
    },
    "presentation_disposition_contract": {
        "PRIMARY_RESULT_PLACEMENT": [
            "PRIMARY_EVIDENCE", "CASE_EVIDENCE", "REVIEW_EVIDENCE",
            "GUIDELINE_EVIDENCE",
        ],
        "REFERENCE_CONTEXT": ["BACKGROUND_LITERATURE", "OTHER_CONTEXT"],
        "reference_context_primary_weight": 0,
        "reference_context_can_create_primary_placement": False,
    },
    "direct_relation_scope_allowlist": {
        kind: sorted(scopes) for kind, scopes in DIRECT_RELATION_SCOPES.items()
    },
    "context_placement_relation_scopes": [
        "COHORT_CONTEXT", "COMPARATOR_CONTEXT",
    ],
    "modifier_subject_contract": {
        "FINDING_CONTEXT": {
            "sequence_id": "NULL", "source_occurrence_id": "NULL",
            "affected_occurrence_ids": "EMPTY",
        },
        "SEQUENCE_CONTEXT": {
            "sequence_id": "REQUIRED", "source_occurrence_id": "REQUIRED",
            "affected_occurrence_ids": "NONEMPTY_SAME_SEQUENCE",
        },
    },
    "statistic_evidence_context_cardinality": "EXACTLY_ONE",
    "statistic_axis_evidence_context_cardinality": "ZERO_OR_MORE",
    "evidence_synthesis_membership_contract": {
        "authoritative_graph_group": "axis_evidence_membership_edges",
        "authoritative_database_view": "public_sign_axis_evidence_membership",
        "subject_ownership_graph_group": "axis_evidence_ownership_receipts",
        "subject_ownership_database_view": "public_subject_axis_evidence_owner",
        "subject_ownership_id_rule": "EXACT_SOURCE_AXIS_EVIDENCE_LINK_ID",
        "summary_membership_edge_field": "axis_evidence_membership_edge_ids",
        "finding_membership_origins": [
            "COHORT_FALLBACK_EVIDENCE",
            "SUBJECT_AXIS_EVIDENCE", "STATISTIC_AXIS_EVIDENCE_CONTEXT",
        ],
        "ownership_kind_allowlist": [
            "COHORT_FALLBACK_EVIDENCE", "STATISTIC_AXIS_EVIDENCE_CONTEXT",
            "SUBJECT_AXIS_EVIDENCE",
        ],
        "relationship_disposition_allowlist": [
            "ATOMIC_AXIS_EVIDENCE", "COHORT_FALLBACK_RELATIONSHIP",
            "DIRECT_TARGET_RELATIONSHIP",
            "EXPLICIT_NONASSOCIATION", "EXPLICIT_NO_USABLE_TARGET",
            "NONPROJECTABLE_AXIS_EVIDENCE",
        ],
        "statistic_membership_rule": (
            "STATISTIC_SIGN_INTERSECT_STATISTIC_AXIS_EVIDENCE_CONTEXT"
        ),
        "work_membership_rule": (
            "DISTINCT_SOURCE_WORK_OF_TYPED_FINDING_OR_STATISTIC_EVIDENCE"
        ),
        "direct_target_authority": "public_projectable_axis_evidence",
        "cohort_fallback_target_authority": (
            "public_cohort_fallback_occurrence_reference_view WHERE "
            "fallback_status=ACTIVE_FALLBACK AND searchable=1 JOINED_TO_"
            "EXACT_COHORT_ASSERTION_TARGET"
        ),
        "cohort_fallback_occurrence_reference_authority": (
            "public_cohort_fallback_occurrence_reference_view"
        ),
        "effective_target_rule": (
            "AXIS_EVIDENCE_UNION_ACTIVE_COHORT_OCCURRENCE_REFERENCE_"
            "JOINED_TO_ITS_ASSERTION_TARGET"
        ),
        "summary_target_exclusions": ["target_usable=false"],
        "summary_target_relationship_references": {
            "relationship_ids": "EXACT_IDS_IN_RESULT_RELATIONSHIPS",
            "relationship_kinds": (
                "EXACT_DEDUPLICATED_RESULT_RELATIONSHIP_KINDS"
            ),
            "placement_edge_ids": (
                "AXIS_EVIDENCE_RELATIONSHIP_ID_SUBSET"
            ),
            "cohort_fallback_edge_ids": (
                "COHORT_FALLBACK_RELATIONSHIP_ID_SUBSET"
            ),
        },
        "no_usable_target_weight": (
            "RETAIN_CONTRIBUTION_WITH_ZERO_FINAL_WEIGHT"
        ),
        "axis_without_typed_evidence": "NO_CONTRIBUTION",
    },
    "result_occurrence_identity_cardinality": "EXACTLY_ONE",
    "source_sign_mapping_role": "ORGANIZATIONAL_ONLY",
    "source_native_display_contract": (
        "DISPLAY_SOURCE_NATIVE_TERM_AND_LOCATOR;CANONICAL_CONCEPTS_ARE_TAGS"
    ),
    "context_local_cross_axis_contract": {
        "authoritative_graph_group": "context_local_axis_relationships",
        "authoritative_database_view": "public_context_local_axis_relationship",
        "join_key": [
            "result_occurrence_id", "finding_ref", "source_sha256",
            "public_sign_id",
        ],
        "result_evidence_context_id_rule": "ECTX:RESULT:<result_occurrence_id>",
        "relationship_kind_allowlist": [
            "AXIS_EVIDENCE", "COHORT_FALLBACK",
        ],
        "missing_lateralization_status": (
            "NO_SAME_RESULT_OCCURRENCE_LATERALIZATION"
        ),
        "cross_sign_or_finding_inheritance": False,
    },
    "cohort_fallback_contract": {
        "context_relation_scope": "COHORT_CONTEXT",
        "direct_scientific_projectability": False,
        "target_ownership_graph_group": "cohort_fallback_assertions",
        "occurrence_reference_graph_group": (
            "cohort_fallback_occurrence_references"
        ),
        "target_rows_per_source_assertion": "EXACTLY_ONE",
        "occurrence_reference_target_fields": "NONE",
        "active_status": "ACTIVE_FALLBACK",
        "superseded_status": "SUPERSEDED_BY_DIRECT",
        "supersession_rule": (
            "INDEPENDENT_SOURCE_CONTEXT_NOT_SUPERSEDED_BY_DIRECT_TARGET"
        ),
        "propagation_can_create_or_delete_localization": False,
    },
    "evidence_partition_contract": {
        "PRIMARY_RESULT": "PRIMARY_EVIDENCE",
        "CASE_OBSERVATION": "CASE_EVIDENCE",
        "REVIEW_SYNTHESIS": "REVIEW_EVIDENCE",
        "GUIDELINE_RECOMMENDATION": "GUIDELINE_EVIDENCE",
        "CITED_STUDY_RESTATEMENT": "BACKGROUND_LITERATURE",
        "PRIMARY_RESULT_SAME_SOURCE_RESTATEMENT": "BACKGROUND_LITERATURE",
        "EDUCATIONAL_STATEMENT": "OTHER_CONTEXT",
        "background_independent_weight": False,
        "educational_independent_weight": False,
    },
    "classification_assignment_cardinality": (
        "EXACTLY_ONE_ASSIGNMENT_PER_PUBLIC_SIGN_PER_SCHEME"
    ),
    "classification_public_schemes": [
        "ILAE_SEIZURE_2025", "LUDERS_UNIFIED",
    ],
    "classification_source_mapping_contract": {
        "authoritative_graph_group": "classification_source_mappings",
        "authoritative_database_table": "public_classification_source_node_map",
        "source_scheme_ids": [
            "ILAE_SEIZURE_2025", "LUDERS_5D_2005", "LUDERS_SSC_1998",
        ],
        "public_luders_scheme_id": "LUDERS_UNIFIED",
        "mapping_cardinality": "EXACTLY_ONE_PER_INCLUDED_SOURCE_NODE",
        "legacy_term_retention_rule": "RETAIN_SOURCE_TERM_UNDER_MAPPED_PARENT",
        "structural_container_relation": "STRUCTURAL_SCHEME_CONTAINER",
        "structural_containers_are_clinical_candidates": False,
        "parallel_public_luders_schemes": False,
    },
    "ilae_2022_terminology_evidence_contract": {
        "authoritative_database_view": "public_classification_terminology_evidence",
        "authoritative_graph_group": "classification_terminology_evidence",
        "source_scheme_id": "ILAE_SEMIOLOGY_GLOSSARY_2022",
        "public_scheme_id": "ILAE_SEIZURE_2025",
        "mapping_cardinality": "EXACTLY_ONE_PER_SOURCE_CONCEPT",
        "public_scheme_count_added": 0,
    },
    "classification_resolution": (
        "UNIQUE_MOST_SPECIFIC_SUPPORTED_DESCENDANT_OR_GROUPED_REVIEW;"
        "ZERO_SUPPORT_IS_NOT_CLASSIFIED"
    ),
    "citation_link_cardinality": (
        "ZERO_OR_MORE_VERIFIED_STRUCTURED_OCCURRENCES_PER_FINDING"
    ),
    "inherited_phase_support_cardinality": (
        "EXACTLY_ONE_ACTIVE_SAME_FINDING_SAME_PHASE"
    ),
    "phase_evidence_cardinality": "ONE_OR_MORE_PER_VISIBLE_SUBJECT",
    "not_reported_phase_exclusivity": "EXCLUSIVE_PER_SUBJECT",
    "reference_edge_serialization": {
        "activation_state": "ACTIVE_ONLY",
        "allowed_mapping_statuses": [
            "DETERMINISTIC_EXACT_LABEL", "EXACT_SOURCE", "OWNER_APPROVED",
            "OWNER_REVIEW_REQUIRED", "SOURCE_EXPLICIT", "SOURCE_NATIVE_UNGROUPED",
        ],
        "owner_review_required": {
            "allowed_edge_kinds": sorted(OWNER_REVIEW_REFERENCE_KINDS),
            "relationship_meaning": "RETAINED_EVIDENCE_TO_REVIEW_TOKEN_ONLY",
            "resolved_classification_eligible": False,
            "axis_target_eligible": False,
        },
        "source_explicit": {"allowed_edge_kinds": ["SIGN_CLASSIFICATION"]},
    },
    "anatomy_display_region_scope": "PRESENTATION_FILTER_ONLY",
    "anatomy_evidence_traversal_contract": {
        "authoritative_graph_group": "anatomy_evidence_traversals",
        "authoritative_database_view": "public_anatomy_evidence_traversal",
        "field_order": list(ANATOMY_EVIDENCE_TRAVERSAL_FIELDS),
        "edge_eligibility": (
            "ACTIVE_AND_PROJECTS_EVIDENCE_AND_"
            "SOURCE_EXPLICIT_OR_OWNER_APPROVED"
        ),
        "direction": "TYPED_EXTENT_DIRECTION_WITH_SYMMETRIC_EQUIVALENCE_OR_OVERLAP",
        "maximum_hops": None,
        "multi_hop_eligibility": "SOURCED_EXACT_OR_CONTAINMENT_CHAIN",
        "terminal_only_scopes": ["OVERLAP", "RELATED"],
        "overlap_after_containment_allowed": False,
        "retrieval_scope_field": "retrieval_scope",
        "cycles_allowed": False,
        "parent_node_id_inference_allowed": False,
        "label_inference_allowed": False,
        "organizational_only": True,
        "source_evidence_cloned": False,
    },
    "source_anatomy_context_contract": {
        "authoritative_graph_group": "source_anatomy_contexts",
        "field_order": list(SOURCE_ANATOMY_CONTEXT_FIELDS),
        "counted_unit": "SOURCE_CONTEXT",
        "identity_field": "evidence_link_id",
        "retrieval_scope": "SOURCE_ONLY",
        "canonical_region_membership": False,
        "source_target_qualification_unchanged": True,
        "occurrence_filters_require_explicit_owner": True,
        "statistic_values_copied": False,
    },
    "anatomy_display_region_basis_allowlist": list(
        ANATOMY_DISPLAY_REGION_BASES
    ),
    "localization_display_region_contract": (
        "EXPLICIT_LINK_OR_UNRESOLVED_NONFILTERABLE"
    ),
}
DATABASE_GRAPH_GROUPS = (
    *(("NODE", name, "nodes") for name in (
        "works", "sources", "findings", "signs", "source_signs", "statistics",
        "sequences", "occurrences", "anatomy", "classifications",
        "phases", "evidence_contexts",
    )),
    ("REFERENCE_EDGE", "reference_edges", "reference_edges"),
    ("RESULT_RELATIONSHIP", "result_relationships", "result_relationships"),
    (
        "AXIS_EVIDENCE_OWNER", "axis_evidence_ownership_receipts",
        "axis_evidence_ownership_receipts",
    ),
    (
        "AXIS_EVIDENCE_MEMBERSHIP", "axis_evidence_membership_edges",
        "axis_evidence_membership_edges",
    ),
    (
        "CONTEXT_LOCAL_AXIS", "context_local_axis_relationships",
        "context_local_axis_relationships",
    ),
    ("CONTEXT_PLACEMENT", "context_placement_edges", "context_placement_edges"),
    ("CONTEXT_MODIFIER", "context_modifier_edges", "context_modifier_edges"),
    (
        "COHORT_FALLBACK_ASSERTION", "cohort_fallback_assertions",
        "cohort_fallback_assertions",
    ),
    (
        "COHORT_FALLBACK_OCCURRENCE_REFERENCE",
        "cohort_fallback_occurrence_references",
        "cohort_fallback_occurrence_references",
    ),
    (
        "STATISTIC_OCCURRENCE_ASSIGNMENT", "statistic_occurrence_assignments",
        "statistic_occurrence_assignments",
    ),
    (
        "CLASSIFICATION_SOURCE_MAP", "classification_source_mappings",
        "classification_source_mappings",
    ),
    (
        "CLASSIFICATION_TERMINOLOGY", "classification_terminology_evidence",
        "classification_terminology_evidence",
    ),
    (
        "CLASSIFICATION_ASSIGNMENT", "classification_assignments",
        "classification_assignments",
    ),
    ("CITATION_LINK", "citation_links", "citation_links"),
    ("ANATOMY_RELATIONSHIP", "anatomy_relationship_edges", "anatomy_relationship_edges"),
    ("ANATOMY_TRAVERSAL", "anatomy_evidence_traversals", "anatomy_evidence_traversals"),
    ("ANATOMY_DISPLAY_REGION", "anatomy_display_region_links", "anatomy_display_region_links"),
)
REFERENCE_ENDPOINT_KINDS = {
    "CLASSIFICATION_PARENT": ("CLASSIFICATION", "CLASSIFICATION"),
    "FINDING_CITED_WORK": ("FINDING", "WORK"),
    "FINDING_CLASSIFICATION": ("FINDING", "CLASSIFICATION"),
    "FINDING_SIGN": ("FINDING", "SIGN"),
    "FINDING_SOURCE": ("FINDING", "SOURCE"),
    "FINDING_SOURCE_SIGN": ("FINDING", "SOURCE_SIGN"),
    "FINDING_PHASE": ("FINDING", "PHASE"),
    "OCCURRENCE_CLASSIFICATION": ("SIGN_OCCURRENCE", "CLASSIFICATION"),
    "OCCURRENCE_SIGN": ("SIGN_OCCURRENCE", "SIGN"),
    "OCCURRENCE_SOURCE_SIGN": ("SIGN_OCCURRENCE", "SOURCE_SIGN"),
    "OCCURRENCE_PHASE": ("SIGN_OCCURRENCE", "PHASE"),
    "SEQUENCE_FINDING": ("SEQUENCE", "FINDING"),
    "SEQUENCE_OCCURRENCE": ("SEQUENCE", "SIGN_OCCURRENCE"),
    "SIGN_CLASSIFICATION": ("SIGN", "CLASSIFICATION"),
    "SIGN_PHASE": ("SIGN", "PHASE"),
    "SOURCE_SIGN_CONTEXT_SIGN": ("SOURCE_SIGN", "SIGN"),
    "SOURCE_SIGN_CLASSIFICATION": ("SOURCE_SIGN", "CLASSIFICATION"),
    "SOURCE_SIGN_CANONICAL_COMPONENT": ("SOURCE_SIGN", "SIGN"),
    "SOURCE_SIGN_REVIEW_TOKEN": ("SOURCE_SIGN", "SIGN"),
    "SOURCE_WORK": ("SOURCE", "WORK"),
    "STATISTIC_EVIDENCE_CONTEXT": ("STATISTIC", "EVIDENCE_CONTEXT"),
    "STATISTIC_AXIS_EVIDENCE_CONTEXT": ("STATISTIC", "EVIDENCE_CONTEXT"),
    "STATISTIC_FINDING": ("STATISTIC", "FINDING"),
    "STATISTIC_OCCURRENCE": ("STATISTIC", "SIGN_OCCURRENCE"),
    "STATISTIC_PHASE": ("STATISTIC", "PHASE"),
    "STATISTIC_SIGN": ("STATISTIC", "SIGN"),
    "STATISTIC_SOURCE_SIGN": ("STATISTIC", "SOURCE_SIGN"),
}


def canonical_json_sha256(value):
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def graph_semantic_digest(payload):
    return canonical_json_sha256({
        field: deepcopy(payload.get(field)) for field in GRAPH_DIGEST_FIELDS
    })


def assert_bundle_integrity(bundle):
    """Reproduce the frozen graph and public-bundle semantic digests."""
    graph = bundle.get("scientific_relationship_graph") or {}
    expected_graph = str(graph.get("semantic_digest") or "")
    actual_graph = graph_semantic_digest(graph)
    if expected_graph != actual_graph:
        raise ValueError(
            "Scientific graph digest mismatch: "
            f"semantic={expected_graph} actual={actual_graph}"
        )
    if str((graph.get("release") or {}).get("bundle_schema_version") or "") != str(
        bundle.get("schema_version") or ""
    ):
        raise ValueError("Bundle and graph release schema versions differ.")
    bound = deepcopy(bundle)
    expected_bundle = str(bound.pop("semantic_digest", "") or "")
    actual_bundle = canonical_json_sha256(bound)
    if expected_bundle != actual_bundle:
        raise ValueError(
            "Bundle semantic digest mismatch: "
            f"expected={expected_bundle} actual={actual_bundle}"
        )
    return {
        "graph_sha256": actual_graph,
        "bundle_semantic_digest": actual_bundle,
    }


def _unique(values):
    return list(OrderedDict.fromkeys(value for value in values if value not in (None, "")))


class PublicRelationshipGraph:
    """Normalized, immutable-reference view used by every public consumer."""

    def __init__(self, payload):
        if not isinstance(payload, dict) or not payload:
            raise ValueError("The public bundle has no scientific relationship graph.")
        if set(payload) != set(GRAPH_PAYLOAD_FIELDS):
            raise ValueError("Scientific relationship graph fields differ.")
        if str(payload.get("schema_version") or "") != GRAPH_SCHEMA_VERSION:
            raise ValueError("Scientific relationship graph schema version differs.")
        self.payload = payload
        self._validate_required_projection_contract()
        self._initialize_passive_graph()
        return
        node_groups = payload.get("nodes") or {}
        self.node_groups = {name: tuple(rows or []) for name, rows in node_groups.items()}
        self.works = self._nodes_by("works", "work_id")
        self.sources = self._nodes_by("sources", "source_sha256")
        self.findings = self._nodes_by("findings", "finding_ref")
        self.signs = self._nodes_by("signs", "sign_id")
        self.source_signs = self._nodes_by("source_signs", "source_sign_id")
        self.statistics = self._nodes_by("statistics", "statistic_id")
        self.sequences = self._nodes_by("sequences", "sequence_id")
        self.occurrences = self._nodes_by("occurrences", "occurrence_id")
        self.anatomy = self._nodes_by("anatomy", "anatomy_node_id")
        self.display_region_labels = {}
        for row in self.anatomy.values():
            region_id = str(row.get("display_region_id") or "")
            anatomy_id = str(row.get("anatomy_node_id") or "")
            if (
                not region_id
                or str(row.get("major_region_anatomy_node_id") or "")
                != anatomy_id
            ):
                continue
            label = str(row.get("label") or "")
            if label:
                prior = self.display_region_labels.setdefault(region_id, label)
                if prior != label:
                    raise ValueError("A display-region identity has conflicting labels.")
        self.classifications = self._nodes_by(
            "classifications", "classification_node_id"
        )
        self.phases = self._nodes_by("phases", "phase_id")
        self.evidence_contexts = self._nodes_by(
            "evidence_contexts", "evidence_context_id"
        )
        self.nodes_by_kind = {
            "WORK": self.works, "SOURCE": self.sources, "FINDING": self.findings,
            "SIGN": self.signs, "SOURCE_SIGN": self.source_signs,
            "STATISTIC": self.statistics, "SEQUENCE": self.sequences,
            "SIGN_OCCURRENCE": self.occurrences, "ANATOMY": self.anatomy,
            "CLASSIFICATION": self.classifications,
            "PHASE": self.phases,
            "EVIDENCE_CONTEXT": self.evidence_contexts,
        }
        for node_kind, nodes in self.nodes_by_kind.items():
            for node_id, row in nodes.items():
                if (
                    str(row.get("node_id") or "") != node_id
                    or str(row.get("node_kind") or "") != node_kind
                ):
                    raise ValueError(
                        f"{node_kind} node identity or type disagrees with its group."
                    )
        for context in self.evidence_contexts.values():
            finding = self.findings.get(str(context.get("finding_ref") or ""))
            if (
                not finding
                or str(context.get("source_sha256") or "")
                != str(finding.get("source_sha256") or "")
            ):
                raise ValueError(
                    "An evidence context does not belong to its source finding."
                )
            context_kind = str(context.get("context_kind") or "")
            statistic_id = str(context.get("statistic_id") or "")
            assertion_id = str(context.get("assertion_id") or "")
            axis = str(context.get("axis") or "")
            if context_kind == "AXIS_ASSERTION":
                if statistic_id or not assertion_id or axis not in {
                    "LOCALIZATION", "LATERALIZATION",
                }:
                    raise ValueError("An axis evidence context has invalid ownership fields.")
            elif context_kind == "STATISTIC_SOURCE_RECORD":
                statistic = self.statistics.get(statistic_id)
                if (
                    not statistic or assertion_id or axis
                    or str(statistic.get("finding_ref") or "")
                    != str(context.get("finding_ref") or "")
                    or str(context.get("provenance_relation") or "")
                    not in {"DIRECT", "INHERIT_FINDING"}
                    or not str(context.get("evidence_role") or "")
                ):
                    raise ValueError(
                        "A statistic evidence context has invalid ownership fields."
                    )
            else:
                raise ValueError("Evidence context has an unknown context kind.")
        for source in self.sources.values():
            if str(source.get("source_work_id") or "") not in self.works:
                raise ValueError("A source report names an absent work node.")
        for finding in self.findings.values():
            if str(finding.get("source_sha256") or "") not in self.sources:
                raise ValueError("A finding names an absent source node.")
        for statistic in self.statistics.values():
            if str(statistic.get("finding_ref") or "") not in self.findings:
                raise ValueError("A statistic names an absent finding node.")
        for classification in self.classifications.values():
            parent_id = str(classification.get("parent_node_id") or "")
            parent = self.classifications.get(parent_id) if parent_id else None
            if parent_id and (
                not parent
                or str(parent.get("scheme_id") or "")
                != str(classification.get("scheme_id") or "")
            ):
                raise ValueError("A classification parent is absent or cross-scheme.")
        for anatomy in self.anatomy.values():
            parent_id = str(anatomy.get("parent_node_id") or "")
            major_id = str(anatomy.get("major_region_anatomy_node_id") or "")
            if (
                (parent_id and parent_id not in self.anatomy)
                or (major_id and major_id not in self.anatomy)
            ):
                raise ValueError("An anatomy hierarchy reference is absent.")
        for phase_id, phase in self.phases.items():
            if (
                str(phase.get("node_id") or "") != phase_id
                or str(phase.get("phase_id") or "") != phase_id
                or phase_id != f'PHASE:{phase.get("phase_code") or ""}'
                or not str(phase.get("label") or "")
                or not isinstance(phase.get("ordinal"), int)
                or str(phase.get("category_kind") or "")
                != "CLINICAL_PHASE_FILTER"
                or str(phase.get("activation_state") or "") != "ACTIVE"
            ):
                raise ValueError("A phase node violates the controlled phase contract.")
        self.anatomy_display_region_links = tuple(
            payload.get("anatomy_display_region_links") or []
        )
        self.anatomy_display_region_by_id = {}
        self.anatomy_display_region_by_anatomy = {}
        for row in self.anatomy_display_region_links:
            link_id = str(row.get("display_region_link_id") or "")
            anatomy_id = str(row.get("anatomy_node_id") or "")
            required = (
                "anatomy_node_id", "display_region_id", "source_id",
                "source_sha256", "locator", "source_excerpt", "policy_sha256",
            )
            support_relationship_ids = row.get("support_relationship_ids")
            if (
                not link_id or link_id in self.anatomy_display_region_by_id
                or any(row.get(field) in (None, "") for field in required)
                or not isinstance(support_relationship_ids, list)
                or len(support_relationship_ids) != len({
                    str(value) for value in support_relationship_ids
                })
                or anatomy_id not in self.anatomy
                or anatomy_id in self.anatomy_display_region_by_anatomy
                or str(row.get("display_region_id") or "")
                not in self.display_region_labels
                or str(row.get("relationship_scope") or "")
                != "PRESENTATION_FILTER_ONLY"
                or str(row.get("display_region_basis") or "")
                not in ANATOMY_DISPLAY_REGION_BASES
                or str(row.get("mapping_status") or "") != "OWNER_APPROVED"
                or str(row.get("activation_state") or "") != "ACTIVE"
            ):
                raise ValueError(
                    "An anatomy display-region link violates its provenance contract."
                )
            self.anatomy_display_region_by_id[link_id] = row
            self.anatomy_display_region_by_anatomy[anatomy_id] = row
        self.anatomy_relationship_edges = tuple(
            row for row in payload.get("anatomy_relationship_edges") or []
            if row.get("projects_evidence") is True
            and self._active(row, ANATOMY_MAPPING_STATUSES)
        )
        self.anatomy_relationship_by_id = {
            str(row["relationship_id"]): row
            for row in self.anatomy_relationship_edges
        }
        if len(self.anatomy_relationship_by_id) != len(
            self.anatomy_relationship_edges
        ):
            raise ValueError("Anatomy relationship identities are duplicated.")
        self._validate_anatomy_display_region_support()
        self.anatomy_evidence_traversals = self._contract_rows(
            "anatomy_evidence_traversals",
            ANATOMY_EVIDENCE_TRAVERSAL_FIELDS,
            "traversal_id",
        )

        self.reference_edges = tuple(payload.get("reference_edges") or [])
        reference_ids = [str(row.get("edge_id") or "") for row in self.reference_edges]
        if not all(reference_ids) or len(set(reference_ids)) != len(reference_ids):
            raise ValueError("Reference edge identities are duplicated.")
        self.reference_edges_by_kind = {}
        self.reference_edges_from = {}
        self.reference_edges_to = {}
        for row in self.reference_edges:
            self._validate_reference_edge(row)
            kind = str(row["edge_kind"])
            self.reference_edges_by_kind.setdefault(kind, []).append(row)
            self.reference_edges_from.setdefault(
                (kind, str(row["source_node_id"])), []
            ).append(row)
            self.reference_edges_to.setdefault(
                (kind, str(row["target_node_id"])), []
            ).append(row)
        self.finding_source_sign_pairs = {
            (str(row["source_node_id"]), str(row["target_node_id"]))
            for row in self.reference_edges_by_kind.get("FINDING_SOURCE_SIGN", ())
        }
        self._validate_reference_ownership()
        self._validate_phase_ownership()

        self.classification_source_mappings = self._contract_rows(
            "classification_source_mappings",
            CLASSIFICATION_SOURCE_MAPPING_FIELDS,
            "source_node_id",
        )
        self.classification_terminology_evidence = self._contract_rows(
            "classification_terminology_evidence",
            CLASSIFICATION_TERMINOLOGY_FIELDS,
            "terminology_evidence_id",
        )
        self.classification_assignments = self._contract_rows(
            "classification_assignments",
            CLASSIFICATION_ASSIGNMENT_FIELDS,
            "assignment_id",
        )
        self._validate_classification_surfaces()
        self.citation_links = self._contract_rows(
            "citation_links", CITATION_LINK_FIELDS, "citation_link_id"
        )
        self._validate_citation_links()
        self.statistic_occurrence_assignments = self._contract_rows(
            "statistic_occurrence_assignments",
            STATISTIC_OCCURRENCE_ASSIGNMENT_FIELDS,
            "assignment_id",
        )
        self._validate_statistic_occurrence_assignments()
        self.context_local_axis_relationships = self._contract_rows(
            "context_local_axis_relationships",
            CONTEXT_LOCAL_AXIS_FIELDS,
            "context_axis_join_id",
        )
        self.cohort_fallback_assertions = self._contract_rows(
            "cohort_fallback_assertions",
            COHORT_FALLBACK_ASSERTION_FIELDS,
            "fallback_assertion_id",
        )
        self.cohort_fallback_by_id = {
            str(row["fallback_assertion_id"]): row
            for row in self.cohort_fallback_assertions
        }
        self.cohort_fallback_occurrence_references = self._contract_rows(
            "cohort_fallback_occurrence_references",
            COHORT_FALLBACK_OCCURRENCE_REFERENCE_FIELDS,
            "occurrence_reference_id",
        )

        self.direct_placement_edges = tuple(payload.get("direct_placement_edges") or [])
        if len({str(row.get("placement_edge_id") or "") for row in self.direct_placement_edges}) != len(
            self.direct_placement_edges
        ):
            raise ValueError("Direct placement identities are duplicated.")
        self.direct_placement_by_id = {
            str(row["placement_edge_id"]): row
            for row in self.direct_placement_edges
        }
        self.direct_placements_by_evidence = {}
        for row in self.direct_placement_edges:
            self._validate_placement(row, direct=True)
            self.direct_placements_by_evidence.setdefault(
                str(row["evidence_link_id"]), []
            ).append(row)
        self.source_placement_for_derived = {}
        for row in self.direct_placement_edges:
            self._validate_projectability_chain(row)
        self.direct_placements_by_sign = {}
        self.direct_placements_by_finding = {}
        self.direct_placements_by_context = {}
        for row in self.direct_placement_edges:
            self.direct_placements_by_sign.setdefault(str(row["sign_id"]), []).append(row)
            self.direct_placements_by_finding.setdefault(
                str(row["finding_ref"]), []
            ).append(row)
            self.direct_placements_by_context.setdefault(
                str(row["evidence_context_id"]), []
            ).append(row)
        self.context_placement_edges = tuple(
            payload.get("context_placement_edges") or []
        )
        if len({
            str(row.get("placement_edge_id") or "")
            for row in self.context_placement_edges
        }) != len(self.context_placement_edges):
            raise ValueError("Context placement identities are duplicated.")
        for row in self.context_placement_edges:
            self._validate_placement(row, direct=False)
        self._validate_context_relationship_surfaces()
        self.axis_evidence_ownership_receipts = tuple(
            payload.get("axis_evidence_ownership_receipts") or []
        )
        self.axis_evidence_ownership_by_id = {}
        for row in self.axis_evidence_ownership_receipts:
            self._validate_axis_evidence_ownership_receipt(row)
            ownership_id = str(row["ownership_id"])
            if ownership_id in self.axis_evidence_ownership_by_id:
                raise ValueError("Axis-evidence ownership receipts are duplicated.")
            self.axis_evidence_ownership_by_id[ownership_id] = row
        for row in self.axis_evidence_ownership_receipts:
            parent_id = str(row.get("source_evidence_link_id") or "")
            if parent_id and parent_id not in self.axis_evidence_ownership_by_id:
                raise ValueError(
                    "Derived axis-evidence receipt has no exported source owner."
                )
        self.axis_evidence_membership_edges = tuple(
            payload.get("axis_evidence_membership_edges") or []
        )
        membership_ids = [
            str(row.get("membership_edge_id") or "")
            for row in self.axis_evidence_membership_edges
        ]
        if (
            not all(membership_ids)
            or len(membership_ids) != len(set(membership_ids))
        ):
            raise ValueError("Axis-evidence membership identities are duplicated.")
        self.axis_evidence_memberships_by_sign_axis = {}
        self.axis_evidence_memberships_by_sign_axis_work = {}
        self.axis_evidence_memberships_by_finding = {}
        self.axis_evidence_memberships_by_statistic = {}
        for row in self.axis_evidence_membership_edges:
            self._validate_axis_evidence_membership(row)
            key = (str(row["public_sign_id"]), str(row["axis"]))
            self.axis_evidence_memberships_by_sign_axis.setdefault(
                key, []
            ).append(row)
            self.axis_evidence_memberships_by_sign_axis_work.setdefault(
                (*key, str(row["source_work_id"])), []
            ).append(row)
            self.axis_evidence_memberships_by_finding.setdefault(
                str(row["finding_ref"]), []
            ).append(row)
            statistic_id = str(row.get("statistic_id") or "")
            if statistic_id:
                self.axis_evidence_memberships_by_statistic.setdefault(
                    statistic_id, []
                ).append(row)
        subject_ownership_ids = {
            str(row["ownership_id"])
            for row in self.axis_evidence_membership_edges
            if str(row["ownership_kind"]) == "SUBJECT_AXIS_EVIDENCE"
        }
        if subject_ownership_ids != set(self.axis_evidence_ownership_by_id):
            raise ValueError(
                "Subject membership and ownership-receipt identities differ."
            )
        self.context_modifier_edges = tuple(payload.get("context_modifier_edges") or [])
        if len({str(row.get("modifier_edge_id") or "") for row in self.context_modifier_edges}) != len(
            self.context_modifier_edges
        ):
            raise ValueError("Context modifier identities are duplicated.")
        for row in self.context_modifier_edges:
            if (
                row.get("projectable") is not False
                or not self._active(row)
                or str(row.get("subject_kind") or "") not in {
                    "FINDING_CONTEXT", "SEQUENCE_CONTEXT"
                }
                or str(row.get("relation_scope") or "") != "PROPAGATION"
                or str(row.get("modifier_type") or "") != "PROPAGATION"
            ):
                raise ValueError("A context modifier violates the nonprojectable contract.")
            required = (
                "modifier_edge_id", "evidence_context_id", "finding_ref",
                "assertion_id", "source_id", "source_sha256", "source_version",
                "locator", "source_excerpt", "modifier_text",
            )
            if any(row.get(field) in (None, "") for field in required):
                raise ValueError("A context modifier lacks source assertion provenance.")
            finding = self.findings.get(str(row.get("finding_ref") or ""))
            source_id = str(row.get("source_id") or "")
            source_sha256 = str(row.get("source_sha256") or "")
            source = self.sources.get(source_id)
            if (
                not finding or not source or source_id != source_sha256
                or source_sha256 != str(finding.get("source_sha256") or "")
                or str(row.get("source_version") or "")
                != str(source.get("source_version") or "")
            ):
                raise ValueError(
                    "Context modifier provenance disagrees with its source owner."
                )
            context = self.evidence_contexts.get(
                str(row.get("evidence_context_id") or "")
            )
            if not context or any(
                str(context.get(field) or "") != str(row.get(field) or "")
                for field in (
                    "assertion_id", "finding_ref", "axis", "source_sha256",
                    "locator", "source_excerpt",
                )
            ):
                raise ValueError(
                    "Context modifier provenance disagrees with its evidence context."
                )
            missing_occurrences = set(
                str(value) for value in row.get("affected_occurrence_ids") or []
            ) - set(self.occurrences)
            if missing_occurrences:
                raise ValueError("A context modifier references an absent occurrence.")
            if str(row.get("subject_kind") or "") == "SEQUENCE_CONTEXT":
                sequence_id = str(row.get("sequence_id") or "")
                sequence = self.sequences.get(sequence_id)
                source_occurrence = self.occurrences.get(
                    str(row.get("source_occurrence_id") or "")
                )
                affected_occurrences = [
                    self.occurrences[str(value)]
                    for value in row.get("affected_occurrence_ids") or []
                ]
                if (
                    not sequence or not source_occurrence
                    or not affected_occurrences
                    or str(sequence.get("finding_ref") or "")
                    != str(row.get("finding_ref") or "")
                    or any(
                        str(occurrence.get("finding_ref") or "")
                        != str(row.get("finding_ref") or "")
                        or str(occurrence.get("sequence_id") or "") != sequence_id
                        for occurrence in [source_occurrence, *affected_occurrences]
                    )
                ):
                    raise ValueError(
                        "A sequence modifier violates sequence occurrence ownership."
                    )
            elif (
                row.get("sequence_id") not in (None, "")
                or row.get("source_occurrence_id") not in (None, "")
                or bool(row.get("affected_occurrence_ids"))
            ):
                raise ValueError(
                    "A finding-context modifier contains sequence occurrence fields."
                )
        self.result_relationships = self._contract_rows(
            "result_relationships", RESULT_RELATIONSHIP_FIELDS,
            "relationship_id",
        )
        self._build_relationship_index()

    def _validate_required_projection_contract(self):
        """Gate the shipped interface without duplicating its scientific policy."""
        contract = self.payload.get("projection_contract")
        if not isinstance(contract, dict):
            raise ValueError("Scientific graph lacks its projection contract.")
        result = contract.get("result_relationship_contract") or {}
        cited_work = result.get("cited_work_occurrence_contract") or {}
        citation_fallback = cited_work.get("source_native_citation_fallback") or {}
        traversal = contract.get("anatomy_evidence_traversal_contract") or {}
        source_context = contract.get("source_anatomy_context_contract") or {}
        weighted = contract.get("weighted_axis_summary_contract") or {}
        weighted_projection = weighted.get("authoritative_database_projection") or {}
        if (
            str(result.get("authoritative_graph_group") or "")
            != "result_relationships"
            or str(result.get("authoritative_database_view") or "")
            != "public_result_scientific_relationship"
            or tuple(result.get("field_order") or ())
            != RESULT_RELATIONSHIP_FIELDS
            or tuple(result.get("relationship_kinds") or ())
            != RESULT_RELATIONSHIP_KINDS
            or result.get("unatomized_relationship_term_contract")
            != PROJECTION_CONTRACT["result_relationship_contract"][
                "unatomized_relationship_term_contract"
            ]
            or result.get("statistic_values_duplicated") is not False
            or result.get("legacy_relationship_tables_are_active_authority")
            is not False
            or tuple(cited_work.get("field_order") or ())
            != CITED_WORK_OCCURRENCE_FIELDS
            or citation_fallback.get("evidence_partition")
            != "BACKGROUND_LITERATURE"
            or citation_fallback.get("citation_text_source")
            != "EXACT_SOURCE_NATIVE_CITATION_AS_PRINTED"
            or tuple(citation_fallback.get("public_text_fields") or ())
            != ("citation_as_printed", "work_citation_text")
            or citation_fallback.get("structured_identity_fields") != "NULL"
            or citation_fallback.get("host_work_identity_unchanged") is not True
            or str(traversal.get("authoritative_graph_group") or "")
            != "anatomy_evidence_traversals"
            or tuple(traversal.get("field_order") or ())
            != ANATOMY_EVIDENCE_TRAVERSAL_FIELDS
            or traversal.get("maximum_hops") is not None
            or traversal.get("multi_hop_eligibility")
            != "SOURCED_EXACT_OR_CONTAINMENT_CHAIN"
            or tuple(traversal.get("terminal_only_scopes") or ())
            != ("OVERLAP", "RELATED")
            or traversal.get("overlap_after_containment_allowed") is not False
            or traversal.get("retrieval_scope_field") != "retrieval_scope"
            or traversal.get("source_evidence_cloned") is not False
            or str(source_context.get("authoritative_graph_group") or "")
            != "source_anatomy_contexts"
            or tuple(source_context.get("field_order") or ())
            != SOURCE_ANATOMY_CONTEXT_FIELDS
            or source_context.get("counted_unit") != "SOURCE_CONTEXT"
            or source_context.get("identity_field") != "evidence_link_id"
            or source_context.get("retrieval_scope") != "SOURCE_ONLY"
            or source_context.get("canonical_region_membership") is not False
            or source_context.get("source_target_qualification_unchanged") is not True
            or source_context.get("occurrence_filters_require_explicit_owner") is not True
            or source_context.get("statistic_values_copied") is not False
            or tuple(weighted.get("summary_field_order") or ())
            != WEIGHTED_AXIS_SUMMARY_FIELDS
            or tuple(weighted.get("contribution_field_order") or ())
            != WEIGHTED_CONTRIBUTION_FIELDS
            or str(weighted_projection.get("section_name") or "")
            != "WEIGHTED_AXIS_SUMMARY"
            or str(weighted_projection.get("group_name") or "")
            != "weighted_axis_summaries"
        ):
            raise ValueError(
                "Scientific graph does not declare the passive public relationship interface."
            )
        self.projection_contract = contract

    def _initialize_passive_graph(self):
        """Load public dictionaries and index shipped relationships by reference."""
        node_groups = self.payload.get("nodes")
        if not isinstance(node_groups, dict):
            raise ValueError("Scientific graph lacks its public dictionaries.")
        self.node_groups = {
            name: tuple(rows or []) for name, rows in node_groups.items()
        }
        if set(self.node_groups) != set(PUBLIC_NODE_FIELDS):
            raise ValueError("Scientific graph public dictionary groups differ.")
        for group, rows in self.node_groups.items():
            expected = set(PUBLIC_NODE_FIELDS[group])
            if any(set(row) != expected for row in rows):
                raise ValueError(f"{group} public dictionary fields differ.")
        self.signs = self._nodes_by("signs", "sign_id")
        self.statistics = self._nodes_by("statistics", "statistic_id")
        self.anatomy = self._nodes_by("anatomy", "anatomy_node_id")
        self.classifications = self._nodes_by(
            "classifications", "classification_node_id"
        )
        self.phases = self._nodes_by("phases", "phase_id")

        # Private owner dictionaries are deliberately unavailable to readers.
        self.works = {}
        self.sources = {}
        self.findings = {}
        self.source_signs = {}
        self.sequences = {}
        self.occurrences = {}
        self.evidence_contexts = {}
        self.reference_edges = ()
        self.reference_edges_by_kind = {}
        self.reference_edges_from = {}
        self.reference_edges_to = {}
        self.direct_placement_edges = ()
        self.context_placement_edges = ()
        self.context_modifier_edges = ()
        self.axis_evidence_membership_edges = ()
        self.axis_evidence_ownership_receipts = ()
        self.context_local_axis_relationships = ()
        self.cohort_fallback_assertions = ()
        self.cohort_fallback_occurrence_references = ()
        self.statistic_occurrence_assignments = ()
        self.citation_links = ()
        self.classification_source_mappings = ()
        self.classification_terminology_evidence = ()
        self.anatomy_relationship_edges = ()

        self.display_region_labels = {}
        self.anatomy_display_region_by_anatomy = {}
        for anatomy_id, row in self.anatomy.items():
            region_id = str(row.get("display_region_id") or "")
            if region_id:
                self.anatomy_display_region_by_anatomy[anatomy_id] = {
                    "display_region_id": region_id,
                }
            if (
                region_id
                and str(row.get("major_region_anatomy_node_id") or "")
                == anatomy_id
                and str(row.get("label") or "")
            ):
                prior = self.display_region_labels.setdefault(
                    region_id, str(row["label"])
                )
                if prior != str(row["label"]):
                    raise ValueError(
                        "A public display-region identity has conflicting labels."
                    )

        self.result_relationships = self._contract_rows(
            "result_relationships", RESULT_RELATIONSHIP_FIELDS,
            "relationship_id",
        )
        self._build_relationship_index()
        self.anatomy_evidence_traversals = self._contract_rows(
            "anatomy_evidence_traversals",
            ANATOMY_EVIDENCE_TRAVERSAL_FIELDS,
            "traversal_id",
        )
        self._index_anatomy_evidence_traversals()
        self.source_anatomy_contexts = self._contract_rows(
            "source_anatomy_contexts", SOURCE_ANATOMY_CONTEXT_FIELDS,
            "evidence_link_id",
        )

        self.classification_assignments = self._contract_rows(
            "classification_assignments", CLASSIFICATION_ASSIGNMENT_FIELDS,
            "assignment_id",
        )
        self._index_public_classification_assignments()
        self.weighted_axis_summaries = self._contract_rows(
            "weighted_axis_summaries", WEIGHTED_AXIS_SUMMARY_FIELDS,
            "summary_id",
        )
        self._index_weighted_axis_summaries()

    def _index_weighted_axis_summaries(self):
        """Validate exporter-owned synthesis references without recomputing it."""
        by_sign_axis = {}
        for summary in self.weighted_axis_summaries:
            sign_id = str(summary.get("public_sign_id") or "")
            axis = str(summary.get("axis") or "")
            key = (sign_id, axis)
            if sign_id not in self.signs or axis not in {
                "LOCALIZATION", "LATERALIZATION",
            } or key in by_sign_axis:
                raise ValueError("A weighted summary has an invalid sign-axis identity.")
            relationship_ids = self._validated_relationship_ids(
                summary, "relationship_ids"
            )
            target_ids = self._validated_relationship_ids(
                summary, "target_relationship_ids", relationship_ids
            )
            primary_target_ids = self._validated_relationship_ids(
                summary, "primary_target_relationship_ids", target_ids
            )
            reference_ids = self._validated_relationship_ids(
                summary, "reference_context_relationship_ids", relationship_ids
            )
            modifier_ids = self._validated_relationship_ids(
                summary, "modifier_relationship_ids", relationship_ids
            )
            if any(
                str(self.result_relationship_by_id[value].get("relationship_kind") or "")
                not in {"AXIS_EVIDENCE", "COHORT_FALLBACK"}
                for value in target_ids
            ) or any(
                self.result_relationship_by_id[value].get("target_usable") is not True
                or str(self.result_relationship_by_id[value].get(
                    "presentation_disposition"
                ) or "") != "PRIMARY_RESULT_PLACEMENT"
                for value in primary_target_ids
            ) or any(
                str(self.result_relationship_by_id[value].get(
                    "presentation_disposition"
                ) or "") != "REFERENCE_CONTEXT"
                for value in reference_ids
            ) or any(
                str(self.result_relationship_by_id[value].get("relationship_kind") or "")
                != "CONTEXT_MODIFIER"
                for value in modifier_ids
            ):
                raise ValueError("A weighted summary changes relationship presentation roles.")
            contribution_ids = set()
            contributions = summary.get("contributions")
            if not isinstance(contributions, list):
                raise ValueError("A weighted summary has no contribution array.")
            for contribution in contributions:
                if not isinstance(contribution, dict) or set(contribution) != set(
                    WEIGHTED_CONTRIBUTION_FIELDS
                ):
                    raise ValueError("Weighted contribution fields differ.")
                contribution_id = str(contribution.get("contribution_id") or "")
                work_id = str(contribution.get("work_id") or "")
                if (
                    not contribution_id or contribution_id in contribution_ids
                    or not work_id
                    or not isinstance(contribution.get("weight_components"), dict)
                ):
                    raise ValueError("A weighted contribution identity is invalid.")
                contribution_ids.add(contribution_id)
                owned_ids = self._validated_relationship_ids(
                    contribution, "relationship_ids", relationship_ids
                )
                owned_target_ids = self._validated_relationship_ids(
                    contribution, "target_relationship_ids", target_ids
                )
                if not owned_target_ids.issubset(owned_ids):
                    raise ValueError("A contribution target is not owned by that contribution.")
                statistic_ids = contribution.get("statistic_ids")
                if (
                    not isinstance(statistic_ids, list)
                    or len(statistic_ids) != len({str(value) for value in statistic_ids})
                    or any(str(value) not in self.statistics for value in statistic_ids)
                    or any(
                        not isinstance(contribution.get(field), list)
                        for field in ("evidence_roles", "evidence_partitions")
                    )
                ):
                    raise ValueError("A weighted contribution changes its typed evidence.")
                try:
                    final_weight = float(contribution.get("final_weight") or 0)
                except (TypeError, ValueError) as exc:
                    raise ValueError("A weighted contribution has no numeric final weight.") from exc
                if final_weight > 0 and not owned_target_ids.intersection(
                    primary_target_ids
                ):
                    raise ValueError(
                        "A positive contribution has no primary usable relationship."
                    )
            by_sign_axis[key] = summary
        self.weighted_axis_summary_by_sign_axis = by_sign_axis

    def _validated_relationship_ids(self, row, field, allowed=None):
        values = row.get(field)
        if not isinstance(values, list):
            raise ValueError(f"{field} is not a relationship identity array.")
        identities = [str(value) for value in values]
        if (
            any(not value for value in identities)
            or len(identities) != len(set(identities))
            or any(value not in self.result_relationship_by_id for value in identities)
            or (allowed is not None and not set(identities).issubset(set(allowed)))
        ):
            raise ValueError(f"{field} contains invalid result relationship identities.")
        return set(identities)

    def _index_public_classification_assignments(self):
        """Index the canonical one-assignment-per-sign/scheme navigation rows."""
        declared = tuple(
            str(value) for value in
            self.projection_contract.get("classification_public_schemes") or ()
        )
        if not declared:
            raise ValueError("Scientific graph declares no public classifications.")
        assignments = {}
        for row in self.classification_assignments:
            sign_id = str(row.get("public_sign_id") or "")
            scheme_id = str(row.get("scheme_id") or "")
            status = str(row.get("resolution_status") or "")
            node_id = str(row.get("node_id") or "")
            key = (sign_id, scheme_id)
            if (
                sign_id not in self.signs
                or scheme_id not in declared
                or status not in {
                    "RESOLVED", "OWNER_REVIEW_REQUIRED", "NOT_CLASSIFIED",
                }
                or not isinstance(row.get("hierarchy_path_node_ids"), list)
                or (status == "RESOLVED" and (
                    node_id not in self.classifications
                    or str(self.classifications[node_id].get("scheme_id") or "")
                    != scheme_id
                ))
                or (status != "RESOLVED" and node_id)
            ):
                raise ValueError(
                    "A public classification assignment violates its navigation contract."
                )
            assignments.setdefault(key, []).append(row)
        expected = {
            (sign_id, scheme_id)
            for sign_id in self.signs for scheme_id in declared
        }
        if set(assignments) != expected:
            raise ValueError(
                "Public classification assignments do not cover every sign and scheme once."
            )
        self.classification_assignment_by_sign_scheme = {
            key: tuple(rows) for key, rows in assignments.items()
        }
        self.classification_terminology_by_node = {}

    def _validate_axis_evidence_ownership_receipt(self, row):
        if set(row) != set(OWNERSHIP_RECEIPT_FIELDS):
            raise ValueError("Axis-evidence ownership receipt fields differ from contract.")
        self._validate_presentation_fields(row)
        ownership_id = str(row.get("ownership_id") or "")
        context_id = str(row.get("evidence_context_id") or "")
        finding_ref = str(row.get("finding_ref") or "")
        source_sign_id = str(row.get("source_sign_id") or "")
        axis = str(row.get("axis") or "")
        subject_kind = str(row.get("subject_kind") or "")
        anatomy_id = str(row.get("anatomy_id") or "")
        lateralization = str(row.get("lateralization_code") or "")
        projectable = row.get("projectable") is True
        if (
            not ownership_id
            or str(row.get("ownership_kind") or "")
            != "SUBJECT_AXIS_EVIDENCE"
            or subject_kind != "SIGN_OCCURRENCE"
            or finding_ref not in self.findings
            or (
                source_sign_id
                and (
                    source_sign_id not in self.source_signs
                    or (finding_ref, source_sign_id)
                    not in self.finding_source_sign_pairs
                )
            )
            or axis not in {"LOCALIZATION", "LATERALIZATION"}
            or (bool(anatomy_id) == bool(lateralization))
            or str(row.get("target_kind") or "")
            != ("ANATOMY" if anatomy_id else "LATERALIZATION")
            or (anatomy_id and anatomy_id not in self.anatomy)
            or (lateralization and lateralization not in LATERALIZATION_LABELS)
            or str(row.get("activation_state") or "") != "ACTIVE"
            or not str(row.get("projectability_basis") or "")
            or not str(row.get("migration_origin") or "")
            or not str(row.get("source_native_sign_term") or "")
            or not str(row.get("source_native_axis_text_status") or "")
            or not str(row.get("source_native_locator") or "")
            or not str(row.get("mapping_lineage") or "")
            or not str(row.get("evidence_role") or "")
            or not str(row.get("evidence_partition") or "")
            or not isinstance(row.get("independent_evidence"), bool)
        ):
            raise ValueError("Axis-evidence ownership receipt violates its type contract.")
        finding = self.findings[finding_ref]
        source_id = str(row.get("source_id") or "")
        source = self.sources.get(source_id)
        context = self.evidence_contexts.get(context_id)
        if (
            not source or source_id != str(row.get("source_sha256") or "")
            or source_id != str(finding.get("source_sha256") or "")
            or str(row.get("source_version") or "")
            != str(source.get("source_version") or "")
            or not context
            or any(
                str(context.get(field) or "") != str(row.get(field) or "")
                for field in (
                    "assertion_id", "finding_ref", "axis", "source_sha256",
                    "locator", "source_excerpt",
                )
            )
        ):
            raise ValueError(
                "Axis-evidence ownership receipt disagrees with source provenance."
            )
        occurrence_id = str(row.get("occurrence_id") or "")
        occurrence = self.occurrences.get(occurrence_id)
        occurrence_source_signs = {
            str(value)
            for value in (occurrence or {}).get("source_component_sign_ids") or []
        }
        if (
            not occurrence
            or str(occurrence.get("finding_ref") or "") != finding_ref
            or (source_sign_id and source_sign_id not in occurrence_source_signs)
            or (
                not source_sign_id
                and occurrence.get("source_sign_id") not in (None, "")
            )
            or str(row.get("source_native_sign_term") or "")
            != str(occurrence.get("source_native_sign_term") or "")
            or str(row.get("evidence_role") or "")
            != str(occurrence.get("evidence_role") or "")
            or str(row.get("evidence_partition") or "")
            != str(occurrence.get("evidence_partition") or "")
            or bool(row.get("independent_evidence"))
            != bool(occurrence.get("independent_evidence"))
        ):
            raise ValueError(
                "Occurrence ownership receipt disagrees with its occurrence."
            )
        expected_disposition = (
            "EXPLICIT_NONASSOCIATION"
            if axis == "LATERALIZATION" and lateralization == "nonlat"
            else "EXPLICIT_NO_USABLE_TARGET"
            if axis == "LATERALIZATION" and lateralization == "unspecified"
            else "DIRECT_TARGET_RELATIONSHIP"
            if projectable else "NONPROJECTABLE_AXIS_EVIDENCE"
        )
        if str(row.get("relationship_disposition") or "") != expected_disposition:
            raise ValueError("Axis-evidence ownership receipt disposition differs.")
        expected_usable = expected_disposition in {
            "DIRECT_TARGET_RELATIONSHIP", "EXPLICIT_NONASSOCIATION",
        }
        if row.get("target_usable") is not expected_usable:
            raise ValueError(
                "Axis-evidence ownership receipt changes target usability."
            )
        native_status = str(row.get("source_native_axis_text_status") or "")
        native_text = row.get("source_native_axis_text")
        if (
            native_status in {
                "EXACT_SOURCE_VECTOR", "EXACT_STRUCTURED_SOURCE_TARGET",
            }
            and native_text in (None, "")
        ) or (
            native_status == "UNAVAILABLE_NOT_ATOMICALLY_STORED"
            and native_text not in (None, "")
        ) or native_status not in {
            "EXACT_SOURCE_VECTOR", "EXACT_STRUCTURED_SOURCE_TARGET",
            "UNAVAILABLE_NOT_ATOMICALLY_STORED",
        }:
            raise ValueError(
                "Axis-evidence ownership receipt changes source-native axis wording."
            )
        if projectable:
            if (
                str(row.get("mapping_status") or "") not in ACTIVE_MAPPING_STATUSES
                or str(row.get("relation_scope") or "")
                not in DIRECT_RELATION_SCOPES[subject_kind]
                or native_status == "UNAVAILABLE_NOT_ATOMICALLY_STORED"
            ):
                raise ValueError("Projectable ownership receipt is not direct approved evidence.")
        elif str(row.get("mapping_status") or "") not in {
            "EXACT_SOURCE", "OWNER_APPROVED", "OWNER_REVIEW_REQUIRED",
        }:
            raise ValueError("Nonprojectable ownership receipt has an invalid status.")

    def _validate_axis_evidence_membership(self, row):
        if set(row) != set(MEMBERSHIP_EDGE_FIELDS):
            raise ValueError("Axis-evidence membership fields differ from contract.")
        self._validate_presentation_fields(row)
        sign_id = str(row.get("public_sign_id") or "")
        axis = str(row.get("axis") or "")
        finding_ref = str(row.get("finding_ref") or "")
        statistic_id = str(row.get("statistic_id") or "")
        work_id = str(row.get("source_work_id") or "")
        context_id = str(row.get("evidence_context_id") or "")
        source_sign_id = str(row.get("source_sign_id") or "")
        occurrence_id = str(row.get("result_occurrence_id") or "")
        ownership_kind = str(row.get("ownership_kind") or "")
        disposition = str(row.get("relationship_disposition") or "")
        occurrence = self.occurrences.get(occurrence_id)
        occurrence_source_signs = {
            str(value)
            for value in (occurrence or {}).get("source_component_sign_ids") or []
        }
        if (
            sign_id not in self.signs
            or axis not in {"LOCALIZATION", "LATERALIZATION"}
            or finding_ref not in self.findings
            or not occurrence
            or str(occurrence.get("finding_ref") or "") != finding_ref
            or str(occurrence.get("public_sign_id") or "") != sign_id
            or (
                source_sign_id
                and (
                    source_sign_id not in self.source_signs
                    or source_sign_id not in occurrence_source_signs
                    or (finding_ref, source_sign_id)
                    not in self.finding_source_sign_pairs
                )
            )
            or (
                not source_sign_id
                and str(row.get("sign_relation") or "")
                != "GROUPED_SOURCE_RESULT"
            )
            or ownership_kind not in MEMBERSHIP_OWNERSHIP_KINDS
            or disposition not in MEMBERSHIP_DISPOSITIONS
            or not isinstance(row.get("target_usable"), bool)
            or not str(row.get("ownership_id") or "")
            or not str(row.get("sign_relation") or "")
            or not str(row.get("sign_mapping_status") or "")
            or not str(row.get("evidence_role") or "")
            or not str(row.get("evidence_partition") or "")
            or not isinstance(row.get("independent_evidence"), bool)
        ):
            raise ValueError("Axis-evidence membership violates typed identity ownership.")
        identity_rows = [
            ref
            for ref in self.reference_edges_from.get(
                ("OCCURRENCE_SIGN", occurrence_id), ()
            )
            if str(ref["target_node_id"]) == sign_id
        ]
        if (
            len(identity_rows) != 1
            or str(identity_rows[0].get("mapping_status") or "")
            != str(row.get("sign_mapping_status") or "")
        ):
            raise ValueError(
                "Axis-evidence membership sign mapping differs from its occurrence identity."
            )
        source_id = self.finding_source_owner[finding_ref]
        source = self.sources[source_id]
        expected_work_id = str(source.get("source_work_id") or source_id)
        context = self.evidence_contexts.get(context_id)
        if (
            work_id != expected_work_id
            or not context
            or str(context.get("context_kind") or "") != "AXIS_ASSERTION"
            or str(context.get("finding_ref") or "") != finding_ref
            or str(context.get("source_sha256") or "") != source_id
            or str(context.get("axis") or "") != axis
        ):
            raise ValueError(
                "Axis-evidence membership disagrees with its source context."
            )
        if ownership_kind == "STATISTIC_AXIS_EVIDENCE_CONTEXT":
            assignment_rows = [
                assignment
                for assignment in self.statistic_occurrence_assignments_by_statistic.get(
                    statistic_id, ()
                )
                if str(assignment.get("resolution_status") or "") == "RESOLVED"
                and str(assignment.get("result_occurrence_id") or "")
                == occurrence_id
                and str(assignment.get("public_sign_id") or "") == sign_id
                and str(assignment.get("source_sign_id") or "")
                == source_sign_id
            ]
            if (
                not statistic_id
                or statistic_id not in self.statistics
                or str(row.get("ownership_id") or "") != context_id
                or self.statistic_finding_owner.get(statistic_id) != finding_ref
                or context_id not in self.statistic_axis_context_ids.get(
                    statistic_id, ()
                )
                or len(assignment_rows) != 1
                or str(assignment_rows[0].get("source_sign_relation") or "")
                != str(row["sign_relation"])
                or str(assignment_rows[0].get("mapping_status") or "")
                != str(row["sign_mapping_status"])
                or not any(
                    str(ref["target_node_id"]) == source_sign_id
                    and str(ref.get("relation") or "")
                    == str(row["sign_relation"])
                    for ref in self.reference_edges_from.get(
                        ("STATISTIC_SOURCE_SIGN", statistic_id), ()
                    )
                )
            ):
                raise ValueError(
                    "Statistic axis membership disagrees with atomic references."
                )
            evidence_owner = self.statistics[statistic_id]
        elif ownership_kind == "SUBJECT_AXIS_EVIDENCE":
            receipt = self.axis_evidence_ownership_by_id.get(
                str(row["ownership_id"])
            )
            if statistic_id:
                raise ValueError(
                    "Subject axis membership unexpectedly names a statistic."
                )
            if (
                not receipt
                or any(
                    str(receipt.get(field) or "")
                    != str(row.get(field) or "")
                    for field in (
                        "ownership_kind", "evidence_context_id", "finding_ref",
                        "source_sign_id", "axis", "relationship_disposition",
                        "evidence_role", "evidence_partition",
                    )
                )
                or str(receipt.get("occurrence_id") or "") != occurrence_id
                or bool(receipt.get("independent_evidence"))
                != bool(row.get("independent_evidence"))
            ):
                raise ValueError(
                    "Subject axis membership disagrees with its ownership receipt."
                )
            if source_sign_id and not any(
                str(ref["target_node_id"]) == source_sign_id
                and str(ref.get("relation") or "") == str(row["sign_relation"])
                for ref in self.reference_edges_from.get(
                    ("FINDING_SOURCE_SIGN", finding_ref), ()
                )
            ):
                raise ValueError(
                    "Subject axis membership disagrees with finding-sign references."
                )
            evidence_owner = occurrence
        else:
            fallback = self.cohort_fallback_by_id.get(str(row["ownership_id"]))
            references = [
                reference
                for reference in self.cohort_fallback_occurrence_references
                if str(reference["fallback_assertion_id"])
                == str(row["ownership_id"])
                and str(reference["result_occurrence_id"]) == occurrence_id
                and str(reference["public_sign_id"]) == sign_id
                and str(reference.get("source_sign_id") or "")
                == source_sign_id
            ]
            if (
                statistic_id
                or not fallback
                or len(references) != 1
                or fallback.get("searchable") is not True
                or str(fallback.get("fallback_status") or "")
                != "ACTIVE_FALLBACK"
                or references[0].get("searchable") is not True
                or str(references[0].get("fallback_status") or "")
                != "ACTIVE_FALLBACK"
                or disposition != "COHORT_FALLBACK_RELATIONSHIP"
                or str(fallback.get("evidence_context_id") or "") != context_id
                or str(fallback.get("finding_ref") or "") != finding_ref
                or str(fallback.get("axis") or "") != axis
                or any(
                    str(references[0].get(field) or "")
                    != str(row.get(field) or "")
                    for field in (
                        "finding_ref", "source_sign_id", "evidence_role",
                        "evidence_partition",
                    )
                )
                or bool(references[0].get("independent_evidence"))
                != bool(row.get("independent_evidence"))
            ):
                raise ValueError(
                    "Cohort fallback membership disagrees with its exact occurrence reference."
                )
            if source_sign_id and not any(
                str(ref["target_node_id"]) == source_sign_id
                and str(ref.get("relation") or "") == str(row["sign_relation"])
                for ref in self.reference_edges_from.get(
                    ("FINDING_SOURCE_SIGN", finding_ref), ()
                )
            ):
                raise ValueError(
                    "Cohort fallback membership changes its source-sign relation."
                )
            evidence_owner = references[0]
        if (
            str(row.get("evidence_role") or "")
            != str(evidence_owner.get("evidence_role") or "")
            or str(row.get("evidence_partition") or "")
            != str(evidence_owner.get("evidence_partition") or "")
            or bool(row.get("independent_evidence"))
            != bool(evidence_owner.get("independent_evidence"))
        ):
            raise ValueError(
                "Axis-evidence membership changes its result evidence role."
            )
        if (
            ownership_kind == "SUBJECT_AXIS_EVIDENCE"
            and disposition == "DIRECT_TARGET_RELATIONSHIP"
            and not any(
                str(placement.get("evidence_link_id") or "")
                == str(row["ownership_id"])
                and str(placement.get("sign_id") or "") == sign_id
                and str(placement.get("source_sign_id") or "")
                == source_sign_id
                and str(placement.get("occurrence_id") or "")
                == occurrence_id
                and str(placement.get("finding_ref") or "") == finding_ref
                and str(placement.get("evidence_context_id") or "")
                == context_id
                and str(placement.get("axis") or "") == axis
                for placement in self.direct_placement_edges
            )
        ):
            raise ValueError(
                "Direct subject membership does not resolve its source evidence owner."
            )

    def _validate_context_relationship_surfaces(self):
        """Validate occurrence-local cohort fallback and cross-axis joins."""
        context_by_evidence = {
            str(row["evidence_link_id"]): row
            for row in self.context_placement_edges
        }
        if len(context_by_evidence) != len(self.context_placement_edges):
            raise ValueError("Context evidence-link identities are duplicated.")
        references_by_fallback = {}
        references_by_id = {}
        for reference in self.cohort_fallback_occurrence_references:
            fallback_id = str(reference["fallback_assertion_id"])
            fallback = self.cohort_fallback_by_id.get(fallback_id)
            occurrence_id = str(reference["result_occurrence_id"])
            occurrence = self.occurrences.get(occurrence_id)
            source_sign_id = str(reference.get("source_sign_id") or "")
            fallback_status = str(reference.get("fallback_status") or "")
            active = fallback_status == "ACTIVE_FALLBACK"
            superseding_ids = self._unique_string_list(
                reference, "superseding_placement_edge_ids"
            )
            source_signs = {
                str(value)
                for value in (occurrence or {}).get("source_component_sign_ids") or []
            }
            if (
                not fallback
                or not occurrence
                or str(reference["activation_state"]) != "ACTIVE"
                or fallback_status not in {
                    "ACTIVE_FALLBACK", "SUPERSEDED_BY_DIRECT",
                }
                or not isinstance(reference.get("searchable"), bool)
                or active != (reference["searchable"] is True)
                or active == bool(superseding_ids)
                or str(reference["finding_ref"])
                != str(occurrence.get("finding_ref") or "")
                or str(reference["public_sign_id"])
                != str(occurrence.get("public_sign_id") or "")
                or str(reference["identity_edge_id"])
                != str(occurrence.get("identity_edge_id") or "")
                or (source_sign_id and source_sign_id not in source_signs)
                or (
                    not source_sign_id
                    and occurrence.get("source_sign_id") not in (None, "")
                )
                or str(reference["source_native_sign_term"])
                != str(occurrence.get("source_native_sign_term") or "")
                or not str(reference["mapping_lineage"])
                or str(reference["evidence_role"])
                != str(occurrence.get("evidence_role") or "")
                or str(reference["evidence_partition"])
                != str(occurrence.get("evidence_partition") or "")
                or bool(reference["independent_evidence"])
                != bool(occurrence.get("independent_evidence"))
                or any(
                    placement_id not in self.direct_placement_by_id
                    or str(self.direct_placement_by_id[placement_id].get(
                        "occurrence_id"
                    ) or "") != occurrence_id
                    or str(self.direct_placement_by_id[placement_id].get(
                        "source_sign_id"
                    ) or "") != source_sign_id
                    or str(self.direct_placement_by_id[placement_id].get(
                        "axis"
                    ) or "") != str(fallback.get("axis") or "")
                    or self.direct_placement_by_id[placement_id].get(
                        "target_usable"
                    ) is not True
                    or self.direct_placement_by_id[placement_id].get(
                        "projectable"
                    ) is not True
                    for placement_id in superseding_ids
                )
            ):
                raise ValueError(
                    "A cohort fallback occurrence reference violates occurrence identity."
                )
            reference_id = str(reference["occurrence_reference_id"])
            references_by_id[reference_id] = reference
            references_by_fallback.setdefault(fallback_id, []).append(reference)

        for fallback in self.cohort_fallback_assertions:
            self._validate_presentation_fields(fallback)
            fallback_id = str(fallback["fallback_assertion_id"])
            fallback_finding = self.findings.get(str(fallback["finding_ref"]))
            context_edge = context_by_evidence.get(
                str(fallback["context_evidence_link_id"])
            )
            superseding_ids = self._unique_string_list(
                fallback, "superseding_placement_edge_ids"
            )
            fallback_status = str(fallback["fallback_status"])
            active = fallback_status == "ACTIVE_FALLBACK"
            occurrence_references = references_by_fallback.get(fallback_id, [])
            active_occurrence_references = [
                reference for reference in occurrence_references
                if str(reference["fallback_status"]) == "ACTIVE_FALLBACK"
            ]
            reference_superseding_ids = {
                placement_id
                for reference in occurrence_references
                for placement_id in reference["superseding_placement_edge_ids"]
            }
            anatomy_id = str(fallback.get("anatomy_id") or "")
            lateralization = str(fallback.get("lateralization_code") or "")
            source_target_usable = bool(anatomy_id) or (
                bool(lateralization) and lateralization != "unspecified"
            )
            native_status = str(fallback["source_native_axis_text_status"])
            native_text = fallback.get("source_native_axis_text")
            if (
                not context_edge
                or str(fallback["activation_state"]) != "ACTIVE"
                or str(fallback["relation_scope"]) != "COHORT_CONTEXT"
                or fallback["projectable"] is not False
                or fallback_status not in {
                    "ACTIVE_FALLBACK", "SUPERSEDED_BY_DIRECT",
                }
                or not isinstance(fallback["searchable"], bool)
                or active != (fallback["searchable"] is True)
                or active != bool(active_occurrence_references)
                or set(superseding_ids) != reference_superseding_ids
                or fallback.get("target_usable") is not source_target_usable
                or bool(anatomy_id) == bool(lateralization)
                or str(fallback["axis"])
                != ("LOCALIZATION" if anatomy_id else "LATERALIZATION")
                or (
                    lateralization
                    and lateralization not in LATERALIZATION_LABELS
                )
                or not str(fallback["source_native_locator"])
                or not str(fallback["mapping_lineage"])
                or (
                    native_status in {
                        "EXACT_SOURCE_VECTOR", "EXACT_STRUCTURED_SOURCE_TARGET",
                    }
                    and native_text in (None, "")
                )
                or (
                    native_status == "UNAVAILABLE_NOT_ATOMICALLY_STORED"
                    and native_text not in (None, "")
                )
                or native_status not in {
                    "EXACT_SOURCE_VECTOR", "EXACT_STRUCTURED_SOURCE_TARGET",
                    "UNAVAILABLE_NOT_ATOMICALLY_STORED",
                }
                or not fallback_finding
                or str(fallback["evidence_role"])
                != str((fallback_finding or {}).get("evidence_role") or "")
                or str(fallback["evidence_partition"])
                != str((fallback_finding or {}).get("evidence_partition") or "")
                or bool(fallback["independent_evidence"])
                != bool((fallback_finding or {}).get("independent_evidence"))
                or any(
                    str(fallback.get(field) or "")
                    != str(context_edge.get(field) or "")
                    for field in (
                        "assertion_id", "evidence_context_id", "finding_ref",
                        "axis", "anatomy_id", "lateralization_code",
                        "relation_scope", "source_native_axis_text",
                        "source_native_axis_text_status",
                        "source_native_locator",
                    )
                )
                or not occurrence_references
                or any(
                    placement_id not in self.direct_placement_by_id
                    for placement_id in superseding_ids
                )
            ):
                raise ValueError(
                    "A cohort fallback assertion violates its source/context contract."
                )
            display_values = (
                fallback.get("display_region_link_id"),
                fallback.get("display_region_id"),
                fallback.get("display_region_basis"),
            )
            if anatomy_id:
                populated = [value not in (None, "") for value in display_values]
                if any(populated) and not all(populated):
                    raise ValueError(
                        "A localization cohort fallback has a partial display-region link."
                    )
                if all(populated):
                    display_link = self.anatomy_display_region_by_id.get(
                        str(fallback["display_region_link_id"])
                    )
                    if (
                        not display_link
                        or str(display_link["anatomy_node_id"]) != anatomy_id
                    ):
                        raise ValueError(
                            "A localization cohort fallback changes its display-region link."
                        )
            elif any(value not in (None, "") for value in display_values):
                raise ValueError(
                    "A lateralization cohort fallback contains display-region data."
                )
            for reference in references_by_fallback[fallback_id]:
                self._validate_presentation_fields(reference)
                if any(
                    str(reference.get(field) or "")
                    != str(fallback.get(field) or "")
                    for field in (
                        "context_evidence_link_id", "assertion_id",
                        "finding_ref", "evidence_role", "evidence_partition",
                        "presentation_disposition", "target_usable",
                    )
                ) or bool(reference["independent_evidence"]) != bool(
                    fallback["independent_evidence"]
                ):
                    raise ValueError(
                        "A cohort occurrence reference changes its fallback assertion."
                    )
        self.cohort_fallback_occurrence_reference_by_id = references_by_id

    def _nodes_by(self, group, identity_field):
        group_rows = self.node_groups.get(group, ())
        rows = [row for row in group_rows if row.get(identity_field) not in (None, "")]
        if len(rows) != len(group_rows):
            raise ValueError(f"{group} contains a node without {identity_field}.")
        values = {
            str(row[identity_field]): row
            for row in rows
        }
        if len(values) != len(rows):
            raise ValueError(f"{group} node identities are duplicated.")
        return values

    def _contract_rows(self, group, fields, identity_field):
        if group not in self.payload:
            raise ValueError(f"Scientific graph lacks required {group} rows.")
        rows = tuple(self.payload.get(group) or ())
        identities = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(fields):
                raise ValueError(f"{group} fields differ from the graph contract.")
            identity = str(row.get(identity_field) or "")
            if not identity:
                raise ValueError(f"{group} contains an empty {identity_field}.")
            identities.append(identity)
        if len(identities) != len(set(identities)):
            raise ValueError(f"{group} identities are duplicated.")
        return rows

    @staticmethod
    def _unique_string_list(row, field):
        values = row.get(field)
        if (
            not isinstance(values, list)
            or len(values) != len({str(value) for value in values})
            or any(not str(value or "") for value in values)
        ):
            raise ValueError(f"{field} is not a unique nonempty string array.")
        return [str(value) for value in values]

    def _validate_classification_surfaces(self):
        public_schemes = tuple(
            str(value)
            for value in PROJECTION_CONTRACT["classification_public_schemes"]
        )
        source_contract = PROJECTION_CONTRACT[
            "classification_source_mapping_contract"
        ]
        source_schemes = set(source_contract["source_scheme_ids"])
        source_mappings = {}
        for row in self.classification_source_mappings:
            source_node_id = str(row["source_node_id"])
            public_node_id = str(row["public_node_id"])
            node = self.classifications.get(public_node_id)
            relation = str(row["relation"])
            if (
                str(row["source_scheme_id"]) not in source_schemes
                or not node
                or str(row["mapping_status"])
                not in {"EXACT_SOURCE", "DETERMINISTIC_EXACT_LABEL", "OWNER_APPROVED"}
                or relation not in {
                    "SOURCE_NODE", "DETERMINISTIC_EXACT_LABEL_MERGE",
                    "UNIFIED_SCOPE_ROOT", "RETAIN_SOURCE_TERM_UNDER_MAPPED_PARENT",
                    "STRUCTURAL_SCHEME_CONTAINER",
                }
                or str(row["activation_state"]) != "ACTIVE"
                or len(str(row["registry_sha256"])) != 64
                or not str(row["provenance"])
            ):
                raise ValueError(
                    "A classification source mapping violates its typed contract."
                )
            if relation == "RETAIN_SOURCE_TERM_UNDER_MAPPED_PARENT" and (
                source_node_id != public_node_id
                or str(node.get("scheme_id") or "") != "LUDERS_UNIFIED"
                or str(node.get("hierarchy_resolution_basis") or "") != relation
            ):
                raise ValueError(
                    "A retained source classification term lost its public identity."
                )
            source_mappings[source_node_id] = row
        self.classification_source_mapping_by_source = source_mappings

        terminology_by_node = {}
        source_concepts = set()
        terminology_contract = PROJECTION_CONTRACT[
            "ilae_2022_terminology_evidence_contract"
        ]
        for row in self.classification_terminology_evidence:
            source_node_id = str(row["source_node_id"])
            public_node_id = str(row["public_node_id"])
            if source_node_id in source_concepts:
                raise ValueError(
                    "An ILAE source terminology concept maps more than once."
                )
            source_concepts.add(source_node_id)
            if (
                str(row["source_scheme_id"])
                != terminology_contract["source_scheme_id"]
                or str(row["public_scheme_id"])
                != terminology_contract["public_scheme_id"]
                or public_node_id not in self.classifications
                or str(row["relation"]) not in {"EXACT", "NARROWER_THAN"}
                or str(row["mapping_status"])
                not in {
                    "DETERMINISTIC_EXACT_LABEL", "EXACT_SOURCE",
                    "OWNER_APPROVED",
                }
                or str(row["activation_state"]) != "ACTIVE"
                or not str(row["source_native_term"])
                or not str(row["source_native_statement"])
                or not isinstance(row["source_locators"], list)
                or not row["source_locators"]
                or not isinstance(row["source_attributes"], dict)
                or not isinstance(row["mapping_lineage"], dict)
            ):
                raise ValueError(
                    "A retained ILAE terminology row violates its typed contract."
                )
            terminology_by_node.setdefault(public_node_id, []).append(row)
        self.classification_terminology_by_node = {
            node_id: tuple(rows) for node_id, rows in terminology_by_node.items()
        }

        assignments_by_sign_scheme = {}
        for row in self.classification_assignments:
            sign_id = str(row["public_sign_id"])
            scheme_id = str(row["scheme_id"])
            status = str(row["resolution_status"])
            relation = str(row["relation"])
            mapping_status = str(row["mapping_status"])
            node_id = str(row.get("node_id") or "")
            candidate_ids = self._unique_string_list(row, "candidate_node_ids")
            hierarchy_path = self._unique_string_list(
                row, "hierarchy_path_node_ids"
            )
            support_ids = self._unique_string_list(
                row, "support_relationship_ids"
            )
            key = (sign_id, scheme_id)
            if (
                sign_id not in self.signs
                or scheme_id not in public_schemes
                or key in assignments_by_sign_scheme
                or str(row["activation_state"]) != "ACTIVE"
                or not str(row["assignment_id"])
                or not str(row["provenance"])
            ):
                raise ValueError(
                    "A public sign classification assignment has invalid ownership."
                )
            if status == "RESOLVED":
                node = self.classifications.get(node_id)
                if (
                    not node
                    or str(node.get("scheme_id") or "") != scheme_id
                    or relation not in {"EXACT", "NARROWER_THAN"}
                    or mapping_status not in {
                        "SOURCE_EXPLICIT", "DETERMINISTIC_EXACT_LABEL",
                        "OWNER_APPROVED",
                    }
                    or not hierarchy_path
                    or hierarchy_path[-1] != node_id
                    or not candidate_ids
                    or node_id not in candidate_ids
                    or not support_ids
                ):
                    raise ValueError(
                        "A resolved classification assignment lacks its exact node support."
                    )
                for index, path_node_id in enumerate(hierarchy_path):
                    path_node = self.classifications.get(path_node_id)
                    expected_parent = None if index == 0 else hierarchy_path[index - 1]
                    if (
                        not path_node
                        or str(path_node.get("scheme_id") or "") != scheme_id
                        or (path_node.get("parent_node_id") or None) != expected_parent
                    ):
                        raise ValueError(
                            "A classification assignment hierarchy path is invalid."
                        )
            elif status == "OWNER_REVIEW_REQUIRED":
                if (
                    node_id
                    or relation != "UNRESOLVED"
                    or mapping_status != "OWNER_REVIEW_REQUIRED"
                    or len(candidate_ids) < 2
                    or hierarchy_path
                    or not support_ids
                    or any(
                        candidate_id not in self.classifications
                        or str(self.classifications[candidate_id].get("scheme_id") or "")
                        != scheme_id
                        for candidate_id in candidate_ids
                    )
                ):
                    raise ValueError(
                        "A review classification assignment violates fail-closed state."
                    )
            elif status == "NOT_CLASSIFIED":
                if (
                    node_id
                    or relation != "UNRESOLVED"
                    or mapping_status != "NO_SUPPORTED_ASSIGNMENT"
                    or candidate_ids
                    or hierarchy_path
                    or support_ids
                ):
                    raise ValueError(
                        "A NOT_CLASSIFIED assignment invents classification support."
                    )
            else:
                raise ValueError("A classification assignment has an unknown status.")
            assignments_by_sign_scheme[key] = row
        expected_assignments = {
            (sign_id, scheme_id)
            for sign_id in self.signs
            for scheme_id in public_schemes
        }
        if set(assignments_by_sign_scheme) != expected_assignments:
            raise ValueError(
                "Classification assignments do not cover every public sign and scheme once."
            )
        self.classification_assignment_by_sign_scheme = assignments_by_sign_scheme

        expected_resolved_refs = {
            (
                str(row["public_sign_id"]), str(row["node_id"]),
                str(row["relation"]), str(row["mapping_status"]),
            )
            for row in self.classification_assignments
            if str(row["resolution_status"]) == "RESOLVED"
        }
        actual_resolved_refs = {
            (
                str(row["source_node_id"]), str(row["target_node_id"]),
                str(row["relation"]), str(row["mapping_status"]),
            )
            for row in self.reference_rows("SIGN_CLASSIFICATION")
        }
        if actual_resolved_refs != expected_resolved_refs:
            raise ValueError(
                "Resolved classification assignments and sign references differ."
            )

    def _validate_citation_links(self):
        citations_by_finding = {}
        citation_pairs = set()
        for row in self.citation_links:
            finding_ref = str(row["finding_ref"])
            citation_id = str(row["citation_id"])
            cited_work_id = str(row["cited_work_id"])
            finding = self.findings.get(finding_ref)
            pair = (finding_ref, citation_id)
            if (
                not finding
                or pair in citation_pairs
                or cited_work_id not in self.works
                or str(row["evidence_role"])
                != str(finding.get("evidence_role") or "")
                or str(row["citation_relation"])
                != (
                    "CITED_RESTATEMENT_OF"
                    if str(row["evidence_role"]) == "CITED_STUDY_RESTATEMENT"
                    else "CITES_WORK"
                )
                or not str(row["citation_as_printed"])
                or not str(row["source_locator"])
                or not str(row["source_excerpt"])
                or str(row["resolution_status"]) != "EXACT_STRUCTURED_LINK"
                or not str(row["resolution_basis"])
                or row["independent_evidence"] is not False
                or str(row["activation_state"]) != "ACTIVE"
            ):
                raise ValueError("A structured citation link violates its contract.")
            citation_pairs.add(pair)
            citations_by_finding.setdefault(finding_ref, []).append(row)
        self.citation_links_by_finding = {
            finding_ref: tuple(rows)
            for finding_ref, rows in citations_by_finding.items()
        }

        expected_refs = {
            (
                str(row["finding_ref"]), str(row["cited_work_id"]),
                str(row["citation_relation"]), str(row["citation_id"]),
            )
            for row in self.citation_links
        }
        actual_refs = set()
        for row in self.reference_rows("FINDING_CITED_WORK"):
            receipt_ids = self._unique_string_list(row, "receipt_release_ids")
            if len(receipt_ids) != 1:
                raise ValueError(
                    "A cited-work reference does not identify one citation occurrence."
                )
            actual_refs.add((
                str(row["source_node_id"]), str(row["target_node_id"]),
                str(row["relation"]), receipt_ids[0],
            ))
        if actual_refs != expected_refs:
            raise ValueError("Structured citations and cited-work references differ.")

    def _validate_statistic_occurrence_assignments(self):
        assignments_by_statistic = {}
        source_pairs = {
            (str(row["source_node_id"]), str(row["target_node_id"])): row
            for row in self.reference_rows("STATISTIC_SOURCE_SIGN")
        }
        expected_pairs = set(source_pairs)
        actual_pairs = set()
        resolved_sign_refs = {
            (
                str(row["source_node_id"]), str(row["target_node_id"]),
                str(row["relation"]), str(row["mapping_status"]),
            )
            for row in self.reference_rows("STATISTIC_SIGN")
        }
        resolved_occurrence_refs = {
            (
                str(row["source_node_id"]), str(row["target_node_id"]),
                str(row["mapping_status"]),
            )
            for row in self.reference_rows("STATISTIC_OCCURRENCE")
        }
        expected_sign_refs, expected_occurrence_refs = set(), set()
        for row in self.statistic_occurrence_assignments:
            statistic_id = str(row["statistic_id"])
            finding_ref = str(row["finding_ref"])
            source_sign_id = str(row["source_sign_id"])
            pair = (statistic_id, source_sign_id)
            statistic = self.statistics.get(statistic_id)
            source_ref = source_pairs.get(pair)
            candidates = self._unique_string_list(
                row, "candidate_result_occurrence_ids"
            )
            if (
                not statistic
                or pair in actual_pairs
                or str(statistic.get("finding_ref") or "") != finding_ref
                or not source_ref
                or str(source_ref["relation"])
                != str(row["source_sign_relation"])
                or not str(row["source_native_statistic_text"])
                or not str(row["source_native_locator"])
                or not str(row["source_native_excerpt"])
            ):
                raise ValueError(
                    "A statistic occurrence assignment violates source ownership."
                )
            actual_pairs.add(pair)
            status = str(row["resolution_status"])
            occurrence_id = str(row.get("result_occurrence_id") or "")
            public_sign_id = str(row.get("public_sign_id") or "")
            mapping_status = str(row["mapping_status"])
            if status == "RESOLVED":
                occurrence = self.occurrences.get(occurrence_id)
                if (
                    not occurrence
                    or str(occurrence.get("finding_ref") or "") != finding_ref
                    or str(occurrence.get("public_sign_id") or "") != public_sign_id
                    or candidates != [occurrence_id]
                    or mapping_status not in {
                        "EXACT_SOURCE", "OWNER_APPROVED", "OWNER_REVIEW_REQUIRED",
                    }
                ):
                    raise ValueError(
                        "A resolved statistic assignment lacks one exact occurrence."
                    )
                expected_sign_refs.add((
                    statistic_id, public_sign_id,
                    str(row["source_sign_relation"]), mapping_status,
                ))
                expected_occurrence_refs.add((
                    statistic_id, occurrence_id, mapping_status,
                ))
            elif status == "OWNER_REVIEW_REQUIRED":
                if (
                    occurrence_id or public_sign_id
                    or mapping_status != "OWNER_REVIEW_REQUIRED"
                    or str(row["resolution_basis"]).startswith(
                        "OWNER_REVIEW_REQUIRED_"
                    ) is False
                ):
                    raise ValueError(
                        "A review statistic assignment violates fail-closed state."
                    )
            elif status == "NOT_APPLICABLE":
                if (
                    occurrence_id or public_sign_id or candidates
                    or str(row["evidence_role"]) != "EDUCATIONAL_STATEMENT"
                    or str(row["evidence_partition"]) != "OTHER_CONTEXT"
                    or row["independent_evidence"] is not False
                    or mapping_status != "NOT_APPLICABLE"
                    or str(row["resolution_basis"])
                    != "NOT_APPLICABLE_EDUCATIONAL_CONTEXT"
                ):
                    raise ValueError(
                        "An educational statistic was assigned to a result occurrence."
                    )
            else:
                raise ValueError("A statistic occurrence assignment has unknown status.")
            if (
                str(row["evidence_role"])
                != str(statistic.get("evidence_role") or "")
                or str(row["evidence_partition"])
                != str(statistic.get("evidence_partition") or "")
                or bool(row["independent_evidence"])
                != bool(statistic.get("independent_evidence"))
                or not str(row["provenance"])
                or str(row["activation_state"]) != "ACTIVE"
            ):
                raise ValueError(
                    "A statistic occurrence assignment changes evidence role."
                )
            assignments_by_statistic.setdefault(statistic_id, []).append(row)
        if actual_pairs != expected_pairs:
            raise ValueError(
                "Statistic occurrence assignments do not conserve source-sign rows."
            )
        if (
            resolved_sign_refs != expected_sign_refs
            or resolved_occurrence_refs != expected_occurrence_refs
        ):
            raise ValueError(
                "Resolved statistic assignments and graph references differ."
            )
        self.statistic_occurrence_assignments_by_statistic = {
            statistic_id: tuple(rows)
            for statistic_id, rows in assignments_by_statistic.items()
        }

    def _validate_anatomy_display_region_support(self):
        links_by_anatomy_region = {
            (
                str(row["anatomy_node_id"]),
                str(row["display_region_id"]),
            )
            for row in self.anatomy_display_region_links
        }
        for row in self.anatomy_display_region_links:
            anatomy_id = str(row["anatomy_node_id"])
            region_id = str(row["display_region_id"])
            anatomy = self.anatomy[anatomy_id]
            basis = str(row["display_region_basis"])
            parent_id = str(row.get("support_parent_node_id") or "")
            relationship_ids = [
                str(value) for value in row["support_relationship_ids"]
            ]
            if basis == "DIRECT_MAJOR_REGION_IDENTITY":
                valid = (
                    not parent_id and not relationship_ids
                    and str(anatomy.get("major_region_anatomy_node_id") or "")
                    == anatomy_id
                    and str(anatomy.get("atlas_native_id") or "") == region_id
                )
            elif basis == "EXPLICIT_PARENT_REGION_RELATIONSHIP":
                parent = self.anatomy.get(parent_id) or {}
                valid = (
                    bool(parent_id) and not relationship_ids
                    and str(anatomy.get("parent_node_id") or "") == parent_id
                    and str(parent.get("major_region_anatomy_node_id") or "")
                    == parent_id
                    and str(parent.get("atlas_native_id") or "") == region_id
                )
            elif basis == "EXPLICIT_ONE_HOP_ANATOMY_RELATIONSHIP":
                relationships = [
                    self.anatomy_relationship_by_id.get(relationship_id)
                    for relationship_id in relationship_ids
                ]
                valid = (
                    not parent_id and bool(relationships)
                    and all(relationship is not None for relationship in relationships)
                    and all(
                        str(relationship["source_anatomy_node_id"])
                        == anatomy_id
                        and (
                            str(relationship["target_anatomy_node_id"]),
                            region_id,
                        ) in links_by_anatomy_region
                        for relationship in relationships
                    )
                )
            else:
                valid = not parent_id and not relationship_ids
            if not valid:
                raise ValueError(
                    "An anatomy display-region link lacks its exact declared support."
                )

    @staticmethod
    def _active(row, statuses=ACTIVE_MAPPING_STATUSES):
        return (
            str(row.get("mapping_status") or "") in statuses
            and str(row.get("activation_state") or "") == "ACTIVE"
        )

    @staticmethod
    def _validate_presentation_fields(row):
        """Require the ledger-authored evidence partition and display role."""
        if (
            not str(row.get("evidence_role") or "")
            or not str(row.get("evidence_partition") or "")
            or not isinstance(row.get("independent_evidence"), bool)
            or str(row.get("presentation_disposition") or "")
            not in PRESENTATION_DISPOSITIONS
            or not isinstance(row.get("target_usable"), bool)
        ):
            raise ValueError(
                "A relationship lacks its canonical evidence presentation fields."
            )

    def _validate_reference_edge(self, row):
        kind = str(row.get("edge_kind") or "")
        mapping_status = str(row.get("mapping_status") or "")
        statuses = PHASE_MAPPING_STATUSES if kind in PHASE_REFERENCE_KINDS else {
            *REFERENCE_MAPPING_STATUSES,
            *({"OWNER_REVIEW_REQUIRED"} if kind in OWNER_REVIEW_REFERENCE_KINDS else set()),
        }
        if not self._active(row, statuses):
            raise ValueError(
                "A serialized reference edge is not active approved graph truth."
            )
        expected = REFERENCE_ENDPOINT_KINDS.get(kind)
        actual = (
            str(row.get("source_node_kind") or ""),
            str(row.get("target_node_kind") or ""),
        )
        if expected is None or actual != expected:
            raise ValueError(f"Reference edge {kind!r} has invalid endpoint kinds.")
        if (
            mapping_status == "OWNER_REVIEW_REQUIRED"
            and kind not in OWNER_REVIEW_REFERENCE_KINDS
        ):
            raise ValueError(
                "OWNER_REVIEW_REQUIRED escaped its retained-evidence edge kinds."
            )
        if mapping_status == "SOURCE_EXPLICIT" and kind != "SIGN_CLASSIFICATION":
            raise ValueError(
                "SOURCE_EXPLICIT escaped its classification provenance edge."
            )
        source_id = str(row.get("source_node_id") or "")
        target_id = str(row.get("target_node_id") or "")
        if source_id not in self.nodes_by_kind[expected[0]]:
            raise ValueError(f"Reference edge {kind!r} has an absent source endpoint.")
        if target_id not in self.nodes_by_kind[expected[1]]:
            raise ValueError(f"Reference edge {kind!r} has an absent target endpoint.")
        context_id = str(row.get("evidence_context_id") or "")
        if context_id and context_id not in self.evidence_contexts:
            raise ValueError(f"Reference edge {kind!r} has an absent evidence context.")
        if kind in {
            "STATISTIC_EVIDENCE_CONTEXT", "STATISTIC_AXIS_EVIDENCE_CONTEXT",
        } and context_id != target_id:
            raise ValueError("Statistic evidence-context reference identity differs.")
        if kind in PHASE_REFERENCE_KINDS:
            self._validate_phase_reference(row)

    @staticmethod
    def _validate_phase_reference(row):
        provenance = str(row.get("provenance_relation") or "")
        kind = str(row.get("edge_kind") or "")
        allowed_provenance = {
            "FINDING_PHASE": {"DIRECT"},
            "STATISTIC_PHASE": {"DIRECT", "INHERIT_FINDING"},
            "OCCURRENCE_PHASE": {"DIRECT", "INHERIT_FINDING"},
            "SIGN_PHASE": {
                "AGGREGATE_FINDING_EVIDENCE",
                "NO_INCLUDED_SOURCE_PHASE_EVIDENCE",
            },
        }
        if (
            str(row.get("relation") or "") != "HAS_PHASE"
            or row.get("evidence_context_id") not in (None, "")
            or str(row.get("target_node_id") or "").startswith("PHASE:") is False
            or provenance not in allowed_provenance[kind]
        ):
            raise ValueError("A phase reference violates its typed provenance contract.")
        phase_evidence_ids = row.get("phase_evidence_ids")
        if (
            not isinstance(phase_evidence_ids, list)
            or len(phase_evidence_ids) != 1
            or not str(phase_evidence_ids[0] or "")
        ):
            raise ValueError("A phase reference must name exactly one evidence row.")
        for field in (
            "support_phase_evidence_ids", "source_native_phase_values",
            "effective_source_phase_values", "finding_refs", "source_sha256s",
            "locators", "source_excerpts",
        ):
            values = row.get(field)
            if not isinstance(values, list) or len(values) != len({
                str(value) for value in values
            }):
                raise ValueError(
                    f"A phase reference has invalid or duplicate {field}."
                )

    def _validate_reference_ownership(self):
        self.finding_source_owner = {}
        for finding_id, finding in self.findings.items():
            owners = self.reference_edges_from.get(
                ("FINDING_SOURCE", finding_id), ()
            )
            if (
                len(owners) != 1
                or str(owners[0]["target_node_id"])
                != str(finding.get("source_sha256") or "")
            ):
                raise ValueError("A finding does not have exactly one matching source owner.")
            self.finding_source_owner[finding_id] = str(owners[0]["target_node_id"])
            source_sign_rows = self.reference_edges_from.get(
                ("FINDING_SOURCE_SIGN", finding_id), ()
            )
            source_sign_ids = [
                str(row["target_node_id"]) for row in source_sign_rows
            ]
            public_sign_rows = self.reference_edges_from.get(
                ("FINDING_SIGN", finding_id), ()
            )
            public_sign_ids = [
                str(row["target_node_id"]) for row in public_sign_rows
            ]
            expected_public_signs = {
                str(row["target_node_id"])
                for occurrence_id, occurrence in self.occurrences.items()
                if str(occurrence.get("finding_ref") or "") == finding_id
                for row in self.reference_edges_from.get(
                    ("OCCURRENCE_SIGN", occurrence_id), ()
                )
            }
            if (
                len(source_sign_ids) != len(set(source_sign_ids))
                or len(public_sign_ids) != len(set(public_sign_ids))
                or set(public_sign_ids) != expected_public_signs
            ):
                raise ValueError(
                    "A finding sign expansion differs from its source-sign identities."
                )
        self.statistic_finding_owner = {}
        self.statistic_context_owner = {}
        self.statistic_axis_context_ids = {}
        for statistic_id, statistic in self.statistics.items():
            finding_rows = self.reference_edges_from.get(
                ("STATISTIC_FINDING", statistic_id), ()
            )
            if len(finding_rows) != 1:
                raise ValueError("A statistic does not have exactly one finding owner.")
            finding_id = str(finding_rows[0]["target_node_id"])
            if finding_id != str(statistic.get("finding_ref") or ""):
                raise ValueError("A statistic reference disagrees with its finding owner.")
            self.statistic_finding_owner[statistic_id] = finding_id
            context_rows = self.reference_edges_from.get(
                ("STATISTIC_EVIDENCE_CONTEXT", statistic_id), ()
            )
            if len(context_rows) != 1:
                raise ValueError("A statistic does not have exactly one evidence context.")
            context = self.evidence_contexts[
                str(context_rows[0]["target_node_id"])
            ]
            if (
                str(context.get("finding_ref") or "") != finding_id
                or str(context.get("context_kind") or "")
                != "STATISTIC_SOURCE_RECORD"
                or str(context.get("statistic_id") or "") != statistic_id
            ):
                raise ValueError("A statistic evidence context belongs to a different finding.")
            finding = self.findings[finding_id]
            if str(context.get("source_sha256") or "") != str(
                finding.get("source_sha256") or ""
            ):
                raise ValueError("A statistic evidence context belongs to a different source.")
            context_id = str(context_rows[0]["target_node_id"])
            self.statistic_context_owner[statistic_id] = context_id
            axis_context_ids = [
                str(row["target_node_id"])
                for row in self.reference_edges_from.get(
                    ("STATISTIC_AXIS_EVIDENCE_CONTEXT", statistic_id), ()
                )
            ]
            if len(axis_context_ids) != len(set(axis_context_ids)):
                raise ValueError(
                    "A statistic has duplicate axis evidence-context references."
                )
            for axis_context_id in axis_context_ids:
                axis_context = self.evidence_contexts[axis_context_id]
                if (
                    str(axis_context.get("finding_ref") or "") != finding_id
                    or str(axis_context.get("context_kind") or "")
                    != "AXIS_ASSERTION"
                    or str(axis_context.get("source_sha256") or "")
                    != str(finding.get("source_sha256") or "")
                ):
                    raise ValueError(
                        "A statistic axis evidence context belongs to a different finding or source."
                    )
            self.statistic_axis_context_ids[statistic_id] = tuple(axis_context_ids)
            source_sign_rows = self.reference_edges_from.get(
                ("STATISTIC_SOURCE_SIGN", statistic_id), ()
            )
            source_sign_ids = [
                str(row["target_node_id"]) for row in source_sign_rows
            ]
            if len(source_sign_ids) != len(set(source_sign_ids)):
                raise ValueError(
                    "A statistic has duplicate source-sign references."
                )
        self.sequence_finding_owner = {}
        for sequence_id, sequence in self.sequences.items():
            finding_rows = self.reference_edges_from.get(
                ("SEQUENCE_FINDING", sequence_id), ()
            )
            if (
                len(finding_rows) != 1
                or str(finding_rows[0]["target_node_id"])
                != str(sequence.get("finding_ref") or "")
            ):
                raise ValueError("A sequence does not have exactly one matching finding.")
            self.sequence_finding_owner[sequence_id] = str(
                finding_rows[0]["target_node_id"]
            )
        for occurrence_id, occurrence in self.occurrences.items():
            sequence_rows = self.reference_edges_to.get(
                ("SEQUENCE_OCCURRENCE", occurrence_id), ()
            )
            source_sign_rows = self.reference_edges_from.get(
                ("OCCURRENCE_SOURCE_SIGN", occurrence_id), ()
            )
            public_sign_rows = self.reference_edges_from.get(
                ("OCCURRENCE_SIGN", occurrence_id), ()
            )
            sequence_id = str(occurrence.get("sequence_id") or "")
            expected_source_signs = {
                str(value)
                for value in occurrence.get("source_component_sign_ids") or []
            }
            expected_public_sign = str(occurrence.get("public_sign_id") or "")
            if (
                (sequence_id and (
                    len(sequence_rows) != 1
                    or str(sequence_rows[0]["source_node_id"]) != sequence_id
                    or self.sequence_finding_owner.get(sequence_id)
                    != str(occurrence.get("finding_ref") or "")
                ))
                or (not sequence_id and sequence_rows)
            ):
                raise ValueError(
                    "An occurrence does not match its optional sequence owner."
                )
            actual_source_signs = {
                str(row["target_node_id"]) for row in source_sign_rows
            }
            if (
                not expected_source_signs
                or actual_source_signs != expected_source_signs
                or len(source_sign_rows) != len(expected_source_signs)
                or any(
                    (str(occurrence.get("finding_ref") or ""), source_sign_id)
                    not in self.finding_source_sign_pairs
                    for source_sign_id in expected_source_signs
                )
            ):
                raise ValueError(
                    "An occurrence does not preserve its exact source-sign components."
                )
            actual_public_signs = [
                str(row["target_node_id"]) for row in public_sign_rows
            ]
            if (
                not expected_public_sign
                or actual_public_signs != [expected_public_sign]
            ):
                raise ValueError(
                    "An occurrence does not have exactly one canonical sign identity."
                )

    def _validate_phase_ownership(self):
        evidence_owner = {}
        for row in self.reference_edges:
            if str(row.get("edge_kind") or "") not in PHASE_REFERENCE_KINDS:
                continue
            evidence_id = str(row["phase_evidence_ids"][0])
            if evidence_id in evidence_owner:
                raise ValueError("A phase evidence row is serialized more than once.")
            evidence_owner[evidence_id] = row

        subject_specs = (
            ("FINDING_PHASE", self.findings),
            ("STATISTIC_PHASE", self.statistics),
            ("OCCURRENCE_PHASE", self.occurrences),
            ("SIGN_PHASE", self.signs),
        )
        for kind, subjects in subject_specs:
            for subject_id in subjects:
                rows = self.reference_edges_from.get((kind, subject_id), ())
                phase_ids = [str(row["target_node_id"]) for row in rows]
                if not rows or len(phase_ids) != len(set(phase_ids)):
                    raise ValueError(
                        f"{kind} must supply one or more unique phases per visible subject."
                    )
                if "PHASE:NOT_REPORTED" in phase_ids and len(phase_ids) != 1:
                    raise ValueError(
                        "NOT_REPORTED must be the sole phase for a visible subject."
                    )

        finding_phase_by_evidence = {
            str(row["phase_evidence_ids"][0]): row
            for row in self.reference_edges_by_kind.get("FINDING_PHASE", ())
        }
        occurrence_phase_by_evidence = {
            str(row["phase_evidence_ids"][0]): row
            for row in self.reference_edges_by_kind.get("OCCURRENCE_PHASE", ())
        }
        for kind, expected_source_kind in PHASE_REFERENCE_KINDS.items():
            for row in self.reference_edges_by_kind.get(kind, ()):
                subject_id = str(row["source_node_id"])
                if expected_source_kind == "FINDING":
                    owner_finding = subject_id
                elif expected_source_kind == "STATISTIC":
                    owner_finding = self.statistic_finding_owner[subject_id]
                elif expected_source_kind == "SIGN_OCCURRENCE":
                    owner_finding = str(
                        self.occurrences[subject_id].get("finding_ref") or ""
                    )
                else:
                    owner_finding = None
                finding_refs = {str(value) for value in row["finding_refs"]}
                source_ids = {str(value) for value in row["source_sha256s"]}
                if owner_finding is not None and finding_refs != {owner_finding}:
                    raise ValueError(
                        "A subject phase reference disagrees with its finding owner."
                    )
                if owner_finding is not None and source_ids != {
                    self.finding_source_owner[owner_finding]
                }:
                    raise ValueError(
                        "A subject phase reference disagrees with its source owner."
                    )
                provenance = str(row["provenance_relation"])
                support_ids = {
                    str(value) for value in row["support_phase_evidence_ids"]
                }
                if expected_source_kind != "SIGN":
                    if any(not row[field] for field in (
                        "source_native_phase_values", "effective_source_phase_values",
                        "finding_refs", "source_sha256s", "locators",
                        "source_excerpts",
                    )):
                        raise ValueError(
                            "A subject phase reference lacks source provenance."
                        )
                    if provenance == "DIRECT" and support_ids:
                        raise ValueError(
                            "A direct subject phase unexpectedly names inherited support."
                        )
                    if provenance == "DIRECT" and set(map(
                        str, row["effective_source_phase_values"]
                    )) != set(map(str, row["source_native_phase_values"])):
                        raise ValueError(
                            "A direct subject phase changes its source-native phase value."
                        )
                    if provenance == "INHERIT_FINDING":
                        if len(row["support_phase_evidence_ids"]) != 1:
                            raise ValueError(
                                "An inherited subject phase must name exactly one finding support."
                            )
                        support_rows = [
                            finding_phase_by_evidence.get(evidence_id)
                            for evidence_id in support_ids
                        ]
                        if (
                            not support_rows
                            or any(item is None for item in support_rows)
                            or any(
                                str(item["source_node_id"]) != owner_finding
                                or str(item["target_node_id"])
                                != str(row["target_node_id"])
                                for item in support_rows
                            )
                        ):
                            raise ValueError(
                                "An inherited subject phase lacks same-finding, same-phase support."
                            )
                        supported_native = {
                            str(value) for item in support_rows
                            for value in item["source_native_phase_values"]
                        }
                        supported_effective = {
                            str(value) for item in support_rows
                            for value in item["effective_source_phase_values"]
                        }
                        if (
                            set(map(str, row["source_native_phase_values"]))
                            != supported_native
                            or set(map(str, row["effective_source_phase_values"]))
                            != supported_effective
                        ):
                            raise ValueError(
                                "An inherited subject phase changes its finding support values."
                            )
                    continue
                if provenance == "NO_INCLUDED_SOURCE_PHASE_EVIDENCE":
                    if (
                        str(row["target_node_id"]) != "PHASE:NOT_REPORTED"
                        or support_ids
                        or any(row[field] for field in (
                            "source_native_phase_values",
                            "effective_source_phase_values", "finding_refs",
                            "source_sha256s", "locators", "source_excerpts",
                        ))
                    ):
                        raise ValueError(
                            "A no-evidence sign phase must be explicit NOT_REPORTED."
                        )
                    continue
                support_rows = [
                    occurrence_phase_by_evidence.get(evidence_id)
                    for evidence_id in support_ids
                ]
                if (
                    not support_rows or any(item is None for item in support_rows)
                    or any(
                        str(item["target_node_id"])
                        != str(row["target_node_id"])
                        for item in support_rows
                    )
                    or any(
                        str(self.occurrences[
                            str(item["source_node_id"])
                        ].get("public_sign_id") or "") != subject_id
                        for item in support_rows
                    )
                ):
                    raise ValueError(
                        "A sign phase does not resolve to matching occurrence evidence."
                    )
                supported_native = {
                    str(value) for item in support_rows
                    for value in item["source_native_phase_values"]
                }
                supported_effective = {
                    str(value) for item in support_rows
                    for value in item["effective_source_phase_values"]
                }
                if (
                    set(map(str, row["source_native_phase_values"]))
                    != supported_native
                    or set(map(str, row["effective_source_phase_values"]))
                    != supported_effective
                ):
                    raise ValueError(
                        "A sign phase changes its supporting finding phase values."
                    )
                supported_findings = {
                    str(self.occurrences[
                        str(item["source_node_id"])
                    ]["finding_ref"])
                    for item in support_rows
                }
                if (
                    finding_refs != supported_findings
                    or not supported_findings.issubset(
                        set(self.finding_refs_for_sign(subject_id))
                    )
                    or source_ids != {
                        self.finding_source_owner[finding_ref]
                        for finding_ref in supported_findings
                    }
                ):
                    raise ValueError(
                        "A sign phase aggregation disagrees with finding/source ownership."
                    )

    def _validate_placement(self, row, *, direct):
        missing = [field for field in PLACEMENT_EDGE_FIELDS if field not in row]
        if missing:
            raise ValueError(f"Placement edge lacks required fields: {missing}")
        self._validate_presentation_fields(row)
        expected_subjects = set(DIRECT_RELATION_SCOPES) if direct else {
            "FINDING_CONTEXT"
        }
        anatomy = row.get("anatomy_id") not in (None, "")
        lateralization = row.get("lateralization_code") not in (None, "")
        expected_usable = anatomy or str(row.get("lateralization_code") or "") != (
            "unspecified"
        )
        if (
            row.get("projectable") is not direct
            or not self._active(row)
            or str(row.get("subject_kind") or "") not in expected_subjects
            or anatomy == lateralization
            or str(row.get("target_kind") or "")
            != ("ANATOMY" if anatomy else "LATERALIZATION")
            or str(row.get("axis") or "")
            != ("LOCALIZATION" if anatomy else "LATERALIZATION")
            or row.get("target_usable") is not expected_usable
            or (
                lateralization
                and str(row.get("lateralization_code") or "")
                not in LATERALIZATION_LABELS
            )
        ):
            raise ValueError("Placement edge violates the direct/context contract.")
        subject_kind = str(row.get("subject_kind") or "")
        relation_scope = str(row.get("relation_scope") or "")
        if direct and relation_scope not in DIRECT_RELATION_SCOPES[subject_kind]:
            raise ValueError(
                "Placement edge has an invalid direct relation scope for its subject."
            )
        required = (
            "placement_edge_id", "evidence_context_id", "finding_ref", "assertion_id",
            "source_id", "source_sha256", "source_version", "locator", "source_excerpt",
        )
        if any(row.get(field) in (None, "") for field in required):
            raise ValueError("Placement edge lacks source assertion provenance.")
        finding = self.findings.get(str(row.get("finding_ref") or ""))
        source_id = str(row.get("source_id") or "")
        source_sha256 = str(row.get("source_sha256") or "")
        source = self.sources.get(source_id)
        if (
            not finding or not source or source_id != source_sha256
            or source_sha256 != str(finding.get("source_sha256") or "")
            or str(row.get("source_version") or "")
            != str(source.get("source_version") or "")
        ):
            raise ValueError("Placement provenance disagrees with its source owner.")
        if direct and row.get("sign_id") in (None, ""):
            raise ValueError("Direct placement lacks an exact sign.")
        if direct and str(row.get("sign_id")) not in self.signs:
            raise ValueError("Direct placement references a non-public sign identity.")
        if direct and any(row.get(field) in (None, "") for field in (
            "source_native_sign_term", "source_native_axis_text",
            "source_native_axis_text_status",
            "source_native_locator", "mapping_lineage",
        )):
            raise ValueError("Direct placement lacks source-native display provenance.")
        if direct and str(row.get("source_native_axis_text_status") or "") not in {
            "EXACT_SOURCE_VECTOR", "EXACT_STRUCTURED_SOURCE_TARGET",
        }:
            raise ValueError(
                "Direct placement lacks exact placement-native anatomy wording."
            )
        if anatomy and str(row.get("anatomy_id")) not in self.anatomy:
            raise ValueError("Placement references an absent anatomy node.")
        display_fields = (
            row.get("display_region_link_id"), row.get("display_region_id"),
            row.get("display_region_basis"),
        )
        if anatomy:
            populated = [value not in (None, "") for value in display_fields]
            if any(populated) and not all(populated):
                raise ValueError(
                    "Localization placement has a partial display-region reference."
                )
            if all(populated):
                display_link = self.anatomy_display_region_by_id.get(
                    str(row["display_region_link_id"])
                )
                if (
                    not display_link
                    or str(display_link["anatomy_node_id"])
                    != str(row.get("anatomy_id") or "")
                    or str(display_link["display_region_id"])
                    != str(row.get("display_region_id") or "")
                    or str(display_link["display_region_basis"])
                    != str(row.get("display_region_basis") or "")
                ):
                    raise ValueError(
                        "Placement lacks its exact provenance-bound display region link."
                    )
        elif any(value not in (None, "") for value in display_fields):
            raise ValueError(
                "A lateralization placement contains anatomy display-region fields."
            )
        context = self.evidence_contexts.get(str(row.get("evidence_context_id") or ""))
        if not context or any(
            str(context.get(field) or "") != str(row.get(field) or "")
            for field in (
                "assertion_id", "finding_ref", "axis", "source_sha256",
                "locator", "source_excerpt",
            )
        ):
            raise ValueError("Placement provenance disagrees with its evidence context.")
        if str(row.get("subject_kind") or "") == "SIGN_OCCURRENCE":
            occurrence = self.occurrences.get(str(row.get("occurrence_id") or ""))
            source_sign_id = str(row.get("source_sign_id") or "")
            occurrence_source_signs = {
                str(value)
                for value in (occurrence or {}).get("source_component_sign_ids") or []
            }
            if (
                not occurrence
                or str(occurrence.get("finding_ref") or "")
                != str(row.get("finding_ref") or "")
                or occurrence.get("sequence_component_id")
                != row.get("sequence_component_id")
                or str(occurrence.get("sequence_id") or "")
                != str(row.get("sequence_id") or "")
                or occurrence.get("ordinal") != row.get("ordinal")
                or occurrence.get("simultaneous_group_id")
                != row.get("simultaneous_group_id")
                or occurrence.get("alternative_group_id")
                != row.get("alternative_group_id")
                or occurrence.get("source_role") != row.get("source_role")
                or (source_sign_id and source_sign_id not in occurrence_source_signs)
                or (
                    not source_sign_id
                    and occurrence.get("source_sign_id") not in (None, "")
                )
                or str(row.get("sign_id") or "")
                != str(occurrence.get("public_sign_id") or "")
                or str(row.get("source_native_sign_term") or "")
                != str(occurrence.get("source_native_sign_term") or "")
            ):
                raise ValueError("Occurrence placement disagrees with its occurrence identity.")
        elif str(row.get("subject_kind") or "") in {
            "FINDING_SIGN", "FINDING_CONTEXT"
        } and any(row.get(field) not in (None, "") for field in (
            "occurrence_id", "sequence_component_id", "sequence_id", "ordinal",
            "simultaneous_group_id", "alternative_group_id", "source_role",
        )):
            raise ValueError("Finding-scoped placement contains occurrence fields.")
        if not direct and str(row.get("relation_scope") or "") not in {
            "COHORT_CONTEXT", "COMPARATOR_CONTEXT"
        }:
            raise ValueError("Context placement has a direct or unknown scope.")

    def _validate_projectability_chain(self, row):
        derived = str(row.get("migration_origin") or "") == (
            "ANATOMY_RELATIONSHIP_PROJECTION"
        )
        source_evidence_link_id = str(row.get("source_evidence_link_id") or "")
        basis = str(row.get("projectability_basis") or "")
        if not derived:
            if source_evidence_link_id or not basis:
                raise ValueError(
                    "A source-stated placement has an invalid projectability basis."
                )
            return
        prefix = "EXPLICIT_ONE_HOP_ANATOMY_RELATIONSHIP:"
        if not source_evidence_link_id or not basis.startswith(prefix):
            raise ValueError("A derived placement lacks an explicit one-hop chain.")
        relationship = self.anatomy_relationship_by_id.get(basis[len(prefix):])
        if not relationship:
            raise ValueError("A derived placement names no active anatomy relationship.")
        match_fields = (
            "subject_kind", "evidence_context_id", "finding_ref", "sign_id",
            "source_sign_id", "occurrence_id", "sequence_component_id",
            "sequence_id", "ordinal", "simultaneous_group_id",
            "alternative_group_id", "source_role", "assertion_id", "axis",
            "relation_scope", "source_id", "source_sha256", "source_version",
            "locator", "source_excerpt", "projectable", "activation_state",
        )
        bases = [
            candidate
            for candidate in self.direct_placements_by_evidence.get(
                source_evidence_link_id, ()
            )
            if str(candidate.get("migration_origin") or "")
            != "ANATOMY_RELATIONSHIP_PROJECTION"
            and all(candidate.get(field) == row.get(field) for field in match_fields)
            and str(candidate.get("anatomy_id") or "")
            == str(relationship.get("source_anatomy_node_id") or "")
            and str(row.get("anatomy_id") or "")
            == str(relationship.get("target_anatomy_node_id") or "")
        ]
        if len(bases) != 1:
            raise ValueError(
                "A derived placement does not resolve to one exact source placement."
            )
        self.source_placement_for_derived[str(row["placement_edge_id"])] = bases[0]

    def _build_relationship_index(self):
        """Index shipped result relationships and their exact target references."""
        self.result_relationship_by_id = {}
        self.relationships_by_sign = {}
        self.relationships_by_sign_axis = {}
        self.relationships_by_occurrence = {}
        self.relationships_by_component = {}
        self.relationships_by_statistic = {}
        self.relationships_by_work = {}
        self.relationships_by_report = {}
        self.axis_targets_by_sign_axis = {}
        self.target_reference_by_key = {}
        self.target_references_by_sign_axis = {}
        self.occurrences_by_sign = {}
        self.context_modifier_result_by_id = {}
        for record in self.result_relationships:
            self._validate_result_relationship(record)
            relationship_id = str(record["relationship_id"])
            kind = str(record["relationship_kind"])
            sign_id = str(record.get("public_sign_id") or "")
            axis = str(record.get("axis") or "")
            occurrence_id = str(record.get("result_occurrence_id") or "")
            component_id = str(record.get("result_component_id") or "")
            work_id = str(record.get("work_id") or "")
            report_id = str(record.get("report_id") or "")
            self.result_relationship_by_id[relationship_id] = record
            if sign_id:
                self.relationships_by_sign.setdefault(sign_id, []).append(record)
                self.relationships_by_sign_axis.setdefault(
                    (sign_id, axis), []
                ).append(record)
            if occurrence_id:
                self.relationships_by_occurrence.setdefault(
                    occurrence_id, []
                ).append(record)
                if kind == "SIGN_IDENTITY":
                    self.occurrences_by_sign.setdefault(sign_id, []).append(record)
            if component_id:
                self.relationships_by_component.setdefault(
                    component_id, []
                ).append(record)
            self.relationships_by_work.setdefault(work_id, []).append(record)
            self.relationships_by_report.setdefault(report_id, []).append(record)
            for statistic_id in record["statistic_ids"]:
                self.relationships_by_statistic.setdefault(
                    str(statistic_id), []
                ).append(record)
            if kind == "AXIS_EVIDENCE" or (
                kind == "COHORT_FALLBACK"
                and str(record["relationship_status"]) == "ACTIVE_FALLBACK"
            ):
                key = (kind, relationship_id)
                reference = {
                    "relationship_kind": kind,
                    "relationship_id": relationship_id,
                    "result_relationship": record,
                }
                self.target_reference_by_key[key] = reference
                self.target_references_by_sign_axis.setdefault(
                    (sign_id, axis), []
                ).append(reference)
            elif kind == "CONTEXT_MODIFIER":
                self.context_modifier_result_by_id[relationship_id] = record
        exact_modifier_owner_fields = (
            "work_id", "report_id", "result_occurrence_id",
            "result_component_id", "finding_ref", "public_sign_id", "axis",
            "source_version", "source_attribution_status", "evidence_partition",
            "presentation_disposition",
        )
        for record in self.result_relationships:
            modifier_ids = record["context_modifier_ids"]
            if str(record["relationship_kind"]) != "AXIS_EVIDENCE" and modifier_ids:
                raise ValueError(
                    "A non-axis relationship carries target-bound context modifiers."
                )
            for modifier_id in modifier_ids:
                modifier = self.context_modifier_result_by_id.get(str(modifier_id))
                if (
                    modifier is None
                    or str(modifier.get("relationship_kind") or "")
                    != "CONTEXT_MODIFIER"
                    or str(modifier.get("relationship_role") or "")
                    not in ("PROPAGATION", "SOURCE_CONDITION")
                    or str(modifier.get("dictionary_domain") or "")
                    != "CONTEXT_MODIFIER"
                    or str(modifier.get("dictionary_item_id") or "")
                    != str(modifier.get("relationship_role") or "")
                    or modifier.get("target_usable") is not False
                    or modifier.get("projectable") is not False
                    or any(
                        str(modifier.get(field) or "")
                        != str(record.get(field) or "")
                        for field in exact_modifier_owner_fields
                    )
                ):
                    raise ValueError(
                        "A target-bound context modifier crosses its exact public owner."
                    )
        return

        self.occurrences_by_sign = {}
        self.occurrences_by_finding = {}
        for occurrence in self.occurrences.values():
            sign_id = str(occurrence.get("public_sign_id") or "")
            finding_ref = str(occurrence.get("finding_ref") or "")
            self.occurrences_by_sign.setdefault(sign_id, []).append(occurrence)
            self.occurrences_by_finding.setdefault(finding_ref, []).append(
                occurrence
            )

        self.result_relationship_by_id = {}
        self.relationships_by_sign_axis = {}
        self.relationships_by_occurrence = {}
        self.relationships_by_finding = {}
        self.relationships_by_context = {}
        self.axis_targets_by_sign_axis = {}
        for record in self.result_relationships:
            self._validate_result_relationship(record)
            relationship_id = str(record["relationship_id"])
            self.result_relationship_by_id[relationship_id] = record
            occurrence_id = str(record["result_occurrence_id"])
            sign_id = str(record["public_sign_id"])
            finding_ref = str(record["finding_ref"])
            self.relationships_by_sign_axis.setdefault(
                (sign_id, str(record.get("axis") or "")), []
            ).append(record)
            self.relationships_by_occurrence.setdefault(
                occurrence_id, []
            ).append(record)
            self.relationships_by_finding.setdefault(finding_ref, []).append(
                record
            )
            self.relationships_by_context.setdefault(
                str(record.get("evidence_context_id") or ""), []
            ).append(record)

        self.target_reference_by_key = {}
        self.target_references_by_sign_axis = {}

        def register_target(kind, target_id, result, projection, occurrence_reference=None):
            key = (str(kind), str(target_id))
            if key in self.target_reference_by_key:
                raise ValueError("Canonical target relationship identity is duplicated.")
            reference = {
                "relationship_kind": key[0],
                "relationship_id": key[1],
                "result_relationship": result,
                "target_projection": projection,
                "occurrence_reference": occurrence_reference,
            }
            self.target_reference_by_key[key] = reference
            self.target_references_by_sign_axis.setdefault((
                str(result["public_sign_id"]), str(result["axis"]),
            ), []).append(reference)

        for placement in self.direct_placement_edges:
            result = self.result_relationship_by_id.get(
                str(placement["placement_edge_id"])
            )
            if (
                not result
                or str(result["relationship_kind"]) != "AXIS_EVIDENCE"
                or str(result["result_occurrence_id"])
                != str(placement["occurrence_id"])
                or str(result["public_sign_id"]) != str(placement["sign_id"])
                or str(result["finding_ref"]) != str(placement["finding_ref"])
                or str(result["source_sha256"])
                != str(placement["source_sha256"])
                or str(result.get("source_sign_id") or "")
                != str(placement.get("source_sign_id") or "")
                or str(result["evidence_context_id"])
                != str(placement["evidence_context_id"])
                or str(result["assertion_id"]) != str(placement["assertion_id"])
                or str(result["axis"]) != str(placement["axis"])
                or str(result["source_native_sign_term"])
                != str(placement["source_native_sign_term"])
                or str(result["source_native_relationship_term"])
                != str(placement["source_native_axis_text"])
                or str(result["source_native_term_status"])
                != str(placement["source_native_axis_text_status"])
                or str(result["source_locator"])
                != str(placement["source_native_locator"])
                or str(result["source_excerpt"])
                != str(placement["source_excerpt"])
                or str(result["dictionary_domain"])
                != str(placement["target_kind"])
                or str(result["dictionary_item_id"])
                != str(
                    placement.get("anatomy_id")
                    or placement.get("lateralization_code") or ""
                )
                or str(result["relationship_role"])
                != str(placement["relation_scope"])
                or result["target_usable"] is not placement["target_usable"]
                or result["projectable"] is not (
                    placement["projectable"] is True
                    and placement["target_usable"] is True
                )
                or str(result["evidence_role"])
                != str(placement["evidence_role"])
                or str(result["evidence_partition"])
                != str(placement["evidence_partition"])
                or bool(result["independent_evidence"])
                != bool(placement["independent_evidence"])
                or str(result["presentation_disposition"])
                != str(placement["presentation_disposition"])
            ):
                raise ValueError(
                    "Direct target projection lacks its exact result relationship."
                )
            register_target(
                "AXIS_EVIDENCE", result["relationship_id"],
                result, placement,
            )

        cohort_reference_by_id = {
            str(row["occurrence_reference_id"]): row
            for row in self.cohort_fallback_occurrence_references
        }
        for relationship_id, reference in cohort_reference_by_id.items():
            result = self.result_relationship_by_id.get(relationship_id)
            assertion = self.cohort_fallback_by_id.get(
                str(reference["fallback_assertion_id"])
            )
            if (
                not result or not assertion
                or str(result["relationship_kind"]) != "COHORT_FALLBACK"
                or str(result["result_occurrence_id"])
                != str(reference["result_occurrence_id"])
                or str(result["public_sign_id"])
                != str(reference["public_sign_id"])
                or str(result["finding_ref"]) != str(reference["finding_ref"])
                or str(result.get("source_sign_id") or "")
                != str(reference.get("source_sign_id") or "")
                or str(result["evidence_context_id"])
                != str(assertion["evidence_context_id"])
                or str(result["assertion_id"])
                != str(assertion["assertion_id"])
                or str(result["axis"]) != str(assertion["axis"])
                or str(result["source_native_sign_term"])
                != str(reference["source_native_sign_term"])
                or str(result["source_native_relationship_term"])
                != str(assertion["source_native_axis_text"])
                or str(result["source_native_term_status"])
                != str(assertion["source_native_axis_text_status"])
                or str(result["source_locator"])
                != str(assertion["source_native_locator"])
                or str(result["dictionary_domain"])
                != ("ANATOMY" if assertion.get("anatomy_id") else "LATERALIZATION")
                or str(result["dictionary_item_id"])
                != str(
                    assertion.get("anatomy_id")
                    or assertion.get("lateralization_code") or ""
                )
                or str(result["relationship_role"]) != "COHORT_CONTEXT"
                or str(result["relationship_status"])
                != str(reference["fallback_status"])
                or result["target_usable"] is not assertion["target_usable"]
                or result["target_usable"] is not reference["target_usable"]
                or result["projectable"] is not False
                or str(result["evidence_role"])
                != str(reference["evidence_role"])
                or str(result["evidence_partition"])
                != str(reference["evidence_partition"])
                or bool(result["independent_evidence"])
                != bool(reference["independent_evidence"])
                or str(result["presentation_disposition"])
                != str(reference["presentation_disposition"])
            ):
                raise ValueError(
                    "Cohort target projection lacks its exact result relationship."
                )
            if reference["searchable"] is True:
                register_target(
                    "COHORT_FALLBACK", relationship_id, result, assertion,
                    reference,
                )

        self.context_modifier_result_by_id = {}
        for modifier in self.context_modifier_edges:
            modifier_id = str(modifier["modifier_edge_id"])
            result = self.result_relationship_by_id.get(modifier_id)
            if result is None:
                if str(modifier.get("subject_kind") or "") != "FINDING_CONTEXT":
                    raise ValueError(
                        "An occurrence-owned context modifier lacks its result relationship."
                    )
                continue
            if (
                str(result["relationship_kind"]) != "CONTEXT_MODIFIER"
                or str(result["finding_ref"]) != str(modifier["finding_ref"])
                or str(result["evidence_context_id"])
                != str(modifier["evidence_context_id"])
                or str(result["assertion_id"]) != str(modifier["assertion_id"])
                or str(result["axis"]) != str(modifier["axis"])
                or str(result["relationship_role"])
                != str(modifier["relation_scope"])
                or str(result["source_native_relationship_term"])
                != str(modifier["modifier_text"])
                or str(result["source_locator"]) != str(modifier["locator"])
                or str(result["source_excerpt"])
                != str(modifier["source_excerpt"])
                or result["target_usable"] is not False
                or result["projectable"] is not False
            ):
                raise ValueError(
                    "Context modifier lacks its exact result relationship."
                )
            self.context_modifier_result_by_id[modifier_id] = result

        self._index_and_validate_context_local_relationships()

        self.statistic_memberships_by_occurrence_context = {}
        for row in self.axis_evidence_membership_edges:
            statistic_id = str(row.get("statistic_id") or "")
            if not statistic_id:
                continue
            key = (
                str(row["result_occurrence_id"]),
                str(row["public_sign_id"]),
                str(row["axis"]),
                str(row["evidence_context_id"]),
            )
            self.statistic_memberships_by_occurrence_context.setdefault(
                key, []
            ).append(row)
        self._index_anatomy_evidence_traversals()

    def _index_anatomy_evidence_traversals(self):
        """Index only canonical, relationship-owned anatomy navigation paths."""
        self.anatomy_traversals_by_relationship = {}
        for row in self.anatomy_evidence_traversals:
            relationship_id = str(row.get("owner_relationship_id") or "")
            result = self.result_relationship_by_id.get(relationship_id)
            source_id = str(row.get("source_anatomy_node_id") or "")
            target_id = str(row.get("target_anatomy_node_id") or "")
            source = self.anatomy.get(source_id)
            target = self.anatomy.get(target_id)
            node_ids = [
                str(value) for value in row.get("path_anatomy_node_ids") or []
            ]
            node_labels = [
                str(value) for value in row.get("path_anatomy_node_labels") or []
            ]
            relationship_ids = [
                str(value) for value in row.get("path_relationship_ids") or []
            ]
            path_relations = [
                str(value) for value in row.get("path_relations") or []
            ]
            path_directions = [
                str(value) for value in row.get("path_directions") or []
            ]
            retrieval_scope = str(row.get("retrieval_scope") or "")
            hop_count = row.get("hop_count")
            if (
                not result
                or str(result.get("relationship_kind") or "") not in {"AXIS_EVIDENCE", "COHORT_FALLBACK"}
                or str(result.get("axis") or "") != "LOCALIZATION"
                or result.get("target_usable") is not True
                or str(result.get("dictionary_domain") or "") != "ANATOMY"
                or str(result.get("dictionary_item_id") or "") != source_id
                or not source or not target
                or row.get("organizational_only") is not True
                or row.get("discoverable") is not True
                or not isinstance(hop_count, int) or hop_count < 1
                or len(relationship_ids) != hop_count
                or len(path_relations) != hop_count
                or len(path_directions) != hop_count
                or len(node_ids) != hop_count + 1
                or len(node_labels) != hop_count + 1
                or len(node_ids) != len(set(node_ids))
                or node_ids[0] != source_id or node_ids[-1] != target_id
                or retrieval_scope not in {
                    "DIRECT", "CONTAINED", "COMPOSITE", "OVERLAP", "RELATED",
                }
                or any(
                    value not in {"FORWARD", "REVERSE"}
                    for value in path_directions
                )
                or node_labels[-1] != str(target.get("label") or "")
                or str(row.get("target_atlas_family_id") or "")
                != str(target.get("atlas_family_id") or "")
                or str(row.get("target_atlas_native_id") or "")
                != str(target.get("atlas_native_id") or "")
                or str(row.get("target_anatomy_label") or "")
                != str(target.get("label") or "")
            ):
                raise ValueError(
                    "An anatomy traversal changes or detaches its owning result relationship."
                )
            self.anatomy_traversals_by_relationship.setdefault(
                relationship_id, []
            ).append(row)

    def anatomy_targets_for_reference(self, reference):
        """Return the source target and every qualified retrieval route."""
        result = reference["result_relationship"]
        if (
            str(result.get("axis") or "") != "LOCALIZATION"
            or str(result.get("dictionary_domain") or "") != "ANATOMY"
            or result.get("target_usable") is not True
        ):
            return []
        relationship_id = str(result["relationship_id"])
        source_id = str(result["dictionary_item_id"])
        rows = [{
            "anatomy_id": source_id,
            "traversal_id": "",
            "organizational_only": False,
            "discoverable": True,
            "retrieval_scope": "DIRECT",
            "path_relationship_ids": [],
            "path_relations": [],
            "path_directions": [],
        }]
        rows.extend({
            "anatomy_id": str(row["target_anatomy_node_id"]),
            "traversal_id": str(row["traversal_id"]),
            "organizational_only": True,
            "discoverable": row["discoverable"] is True,
            "retrieval_scope": str(row.get("retrieval_scope") or ""),
            "path_relationship_ids": list(row.get("path_relationship_ids") or []),
            "path_relations": list(row.get("path_relations") or []),
            "path_directions": list(row.get("path_directions") or []),
        } for row in self.anatomy_traversals_by_relationship.get(
            relationship_id, ()
        ))
        seen = set()
        return [row for row in rows if not (
            (row["anatomy_id"], row["retrieval_scope"], row["traversal_id"])
            in seen
            or seen.add((
                row["anatomy_id"], row["retrieval_scope"], row["traversal_id"]
            ))
        )]

    def region_ids_for_target_reference(self, reference, retrieval_scopes=None):
        """Return linked regions through the caller-selected qualified routes."""
        allowed = (
            {str(value) for value in retrieval_scopes}
            if retrieval_scopes is not None else None
        )
        return _unique(
            str(link.get("display_region_id") or "")
            for target in self.anatomy_targets_for_reference(reference)
            if target["discoverable"]
            and (allowed is None or target["retrieval_scope"] in allowed)
            for link in (
                self.anatomy_display_region_by_anatomy.get(
                    target["anatomy_id"]
                ),
            )
            if link
        )

    def _index_and_validate_context_local_relationships(self):
        """Index canonical cross-axis joins without constructing relationships."""
        self.context_local_by_localization_relationship = {}
        for row in self.context_local_axis_relationships:
            localization_key = (
                str(row["localization_relationship_kind"]),
                str(row["localization_relationship_id"]),
            )
            localization_reference = self.target_reference_by_key.get(
                localization_key
            )
            localization = (
                localization_reference["result_relationship"]
                if localization_reference else None
            )
            lateralization_kind = str(
                row.get("lateralization_relationship_kind") or ""
            )
            lateralization_id = str(
                row.get("lateralization_relationship_id") or ""
            )
            lateralization_key = (
                (lateralization_kind, lateralization_id)
                if lateralization_kind or lateralization_id else None
            )
            lateralization_reference = (
                self.target_reference_by_key.get(lateralization_key)
                if lateralization_key else None
            )
            lateralization = (
                lateralization_reference["result_relationship"]
                if lateralization_reference else None
            )
            identity = (
                str(row["result_occurrence_id"]), str(row["finding_ref"]),
                str(row["source_sha256"]), str(row["public_sign_id"]),
            )
            if (
                not localization
                or localization_key[0] not in {
                    "AXIS_EVIDENCE", "COHORT_FALLBACK",
                }
                or str(localization["axis"]) != "LOCALIZATION"
                or localization["target_usable"] is not True
                or identity != (
                    str(localization["result_occurrence_id"]),
                    str(localization["finding_ref"]),
                    str(localization["source_sha256"]),
                    str(localization["public_sign_id"]),
                )
                or str(row["result_evidence_context_id"])
                != f'ECTX:RESULT:{row["result_occurrence_id"]}'
                or str(row["localization_evidence_context_id"])
                != str(localization["evidence_context_id"])
                or str(row["anatomy_id"])
                != str(localization["dictionary_item_id"])
                or str(row["localization_relation_scope"])
                != str(localization["relationship_role"])
            ):
                raise ValueError(
                    "A context-local localization row changes its result relationship."
                )
            if lateralization is None:
                if (
                    lateralization_key is not None
                    or any(row.get(field) not in (None, "") for field in (
                        "lateralization_evidence_context_id",
                        "lateralization_code", "lateralization_relation_scope",
                    ))
                    or str(row["join_status"])
                    != "NO_SAME_RESULT_OCCURRENCE_LATERALIZATION"
                ):
                    raise ValueError(
                        "A context-local row invents unrelated lateralization."
                    )
            elif (
                lateralization_key[0] not in {
                    "AXIS_EVIDENCE", "COHORT_FALLBACK",
                }
                or str(lateralization["axis"]) != "LATERALIZATION"
                or lateralization["target_usable"] is not True
                or identity != (
                    str(lateralization["result_occurrence_id"]),
                    str(lateralization["finding_ref"]),
                    str(lateralization["source_sha256"]),
                    str(lateralization["public_sign_id"]),
                )
                or str(row["lateralization_evidence_context_id"])
                != str(lateralization["evidence_context_id"])
                or str(row["lateralization_code"])
                != str(lateralization["dictionary_item_id"])
                or str(row["lateralization_relation_scope"])
                != str(lateralization["relationship_role"])
                or str(row["join_status"])
                != "SAME_RESULT_OCCURRENCE_SOURCE_CONTEXT"
            ):
                raise ValueError(
                    "A context-local row inherits cross-occurrence lateralization."
                )
            self.context_local_by_localization_relationship.setdefault(
                localization_key, []
            ).append(row)

    def _validate_result_relationship(self, row):
        """Validate identity and source ownership without recreating a relationship."""
        if set(row) != set(RESULT_RELATIONSHIP_FIELDS):
            raise ValueError("Result relationship fields differ from contract.")
        self._validate_presentation_fields(row)
        relationship_id = str(row.get("relationship_id") or "")
        kind = str(row.get("relationship_kind") or "")
        occurrence_id = str(row.get("result_occurrence_id") or "")
        component_id = str(row.get("result_component_id") or "")
        statistic_ids = row.get("statistic_ids")
        modifier_ids = row.get("context_modifier_ids")
        kind_with_optional_occurrence = (
            kind == "STATISTIC_REFERENCE"
            and str(row.get("relationship_status") or "") in {
                "UNRESOLVED", "OWNER_REVIEW_REQUIRED", "NOT_APPLICABLE",
            }
        )
        authors = row.get("work_authors")
        citations = row.get("cited_work_occurrences")
        background = row.get("evidence_partition") == "BACKGROUND_LITERATURE"
        source_native_relationship_term = str(
            row.get("source_native_relationship_term") or ""
        ).strip()
        source_native_term_status = str(
            row.get("source_native_term_status") or ""
        )
        axis = str(row.get("axis") or "")
        domain = str(row.get("dictionary_domain") or "")
        declared_unatomized_axis_term = (
            kind in {"AXIS_EVIDENCE", "COHORT_FALLBACK"}
            and not source_native_relationship_term
            and source_native_term_status == "UNAVAILABLE_NOT_ATOMICALLY_STORED"
            and axis in {"LOCALIZATION", "LATERALIZATION"}
            and domain == (
                "ANATOMY" if axis == "LOCALIZATION" else "LATERALIZATION"
            )
            and bool(str(row.get("dictionary_item_id") or "").strip())
            and bool(str(row.get("source_native_sign_term") or "").strip())
            and bool(str(row.get("source_locator") or "").strip())
            and bool(str(row.get("source_excerpt") or "").strip())
            and row.get("target_usable") is True
        )
        invalid_citations = not isinstance(citations, list) or any(
            not isinstance(citation, dict)
            or set(citation) != set(CITED_WORK_OCCURRENCE_FIELDS)
            or not str(citation.get("citation_as_printed") or "").strip()
            or (citation.get("cited_work_id") is None and not background)
            or (
                citation.get("cited_work_id") is None
                and (
                    citation.get("work_title") is not None
                    or citation.get("work_authors") is not None
                    or citation.get("work_publication_year") is not None
                    or citation.get("work_citation_text")
                    != citation.get("citation_as_printed")
                    or citation.get("bibliography_status")
                    != "SOURCE_NATIVE_CITATION_ONLY"
                )
            )
            for citation in (citations if isinstance(citations, list) else ())
        )
        if (
            not relationship_id
            or relationship_id in self.result_relationship_by_id
            or kind not in RESULT_RELATIONSHIP_KINDS
            or not str(row.get("work_id") or "")
            or not str(row.get("report_id") or "")
            or not str(row.get("finding_ref") or "")
            or not isinstance(authors, (list, type(None)))
            or invalid_citations
            or (
                not kind_with_optional_occurrence
                and not occurrence_id
            )
            or (
                not kind_with_optional_occurrence
                and not component_id
            )
            or bool(occurrence_id) != bool(component_id)
            or (
                not kind_with_optional_occurrence
                and str(row.get("public_sign_id") or "") not in self.signs
            )
            or (
                kind_with_optional_occurrence
                and row.get("public_sign_id") not in (None, "")
                and str(row.get("public_sign_id")) not in self.signs
            )
            or not isinstance(statistic_ids, list)
            or len(statistic_ids) != len({str(value) for value in statistic_ids})
            or any(str(value) not in self.statistics for value in statistic_ids)
            or not isinstance(modifier_ids, list)
            or len(modifier_ids) != len({str(value) for value in modifier_ids})
            or not source_native_term_status
            or (
                kind != "STATISTIC_REFERENCE"
                and not source_native_relationship_term
                and not declared_unatomized_axis_term
            )
            or (
                kind == "STATISTIC_REFERENCE"
                and row.get("source_native_relationship_term") not in (None, "")
            )
            or (
                source_native_term_status == "UNAVAILABLE_NOT_ATOMICALLY_STORED"
                and not declared_unatomized_axis_term
            )
            or (
                kind != "STATISTIC_REFERENCE"
                and (
                    not str(row.get("source_native_sign_term") or "").strip()
                    or not str(row.get("source_locator") or "").strip()
                    or not str(row.get("source_excerpt") or "").strip()
                )
            )
            or not str(row.get("dictionary_domain") or "")
            or not str(row.get("dictionary_item_id") or "")
            or not str(row.get("relationship_role") or "")
            or not str(row.get("relationship_status") or "")
            or not str(row.get("evidence_role") or "")
            or not str(row.get("evidence_partition") or "")
            or str(row.get("presentation_disposition") or "")
            not in PRESENTATION_DISPOSITIONS
            or not isinstance(row.get("independent_evidence"), bool)
            or not isinstance(row.get("target_usable"), bool)
            or not isinstance(row.get("projectable"), bool)
            or str(row.get("source_attribution_status") or "") not in {
                "REPORTING_WORK_IS_RESULT_SOURCE",
                "STRUCTURED_CITED_WORK_RELATIONSHIP",
                "BACKGROUND_REPORTED_BY_HOST_CITED_WORK_UNKNOWN",
            }
        ):
            raise ValueError(
                "A shipped result relationship violates its public contract."
            )
        if background:
            expected_attribution = (
                "STRUCTURED_CITED_WORK_RELATIONSHIP"
                if any(citation.get("cited_work_id") for citation in citations)
                else "BACKGROUND_REPORTED_BY_HOST_CITED_WORK_UNKNOWN"
            )
            if row.get("source_attribution_status") != expected_attribution:
                raise ValueError(
                    "A background relationship conflates host and cited-work identity."
                )
        if kind in {"AXIS_EVIDENCE", "COHORT_FALLBACK"}:
            if axis not in {"LOCALIZATION", "LATERALIZATION"} or domain != (
                "ANATOMY" if axis == "LOCALIZATION" else "LATERALIZATION"
            ):
                raise ValueError("An axis relationship changes its declared target domain.")
            if kind == "COHORT_FALLBACK" and (
                str(row["relationship_status"])
                not in {"ACTIVE_FALLBACK", "SUPERSEDED_BY_DIRECT"}
                or row["projectable"] is not False
            ):
                raise ValueError("A cohort fallback has an invalid component disposition.")
        elif kind == "PHASE" and (
            str(row.get("dictionary_domain") or "") != "PHASE"
            or str(row.get("dictionary_item_id") or "") not in self.phases
        ):
            raise ValueError("A phase relationship names no public phase.")
        elif kind == "OCCURRENCE_CLASSIFICATION" and (
            str(row.get("dictionary_domain") or "") != "CLASSIFICATION"
            or str(row.get("dictionary_item_id") or "") not in self.classifications
            or str(row.get("relationship_status") or "") != "RESOLVED"
            or row.get("projectable") is not False
        ):
            raise ValueError(
                "An occurrence classification names no resolved public classification."
            )
        elif kind == "STATISTIC_REFERENCE" and (
            str(row.get("dictionary_domain") or "") != "STATISTIC"
            or str(row.get("dictionary_item_id") or "") not in self.statistics
            or [str(value) for value in statistic_ids]
            != [str(row.get("dictionary_item_id") or "")]
        ):
            raise ValueError("A statistic relationship changes its atomic result.")

    @staticmethod
    def _query_values(values):
        if values is None:
            return None
        if isinstance(values, str):
            values = (values,)
        return {str(value) for value in values if str(value or "")}

    def _classification_context_ids(self, sign_id, relationships):
        """Return only stored sign and occurrence classification ancestry."""
        node_ids = []
        for (assigned_sign_id, _scheme_id), assignment_rows in (
            self.classification_assignment_by_sign_scheme.items()
        ):
            if assigned_sign_id != sign_id:
                continue
            for assignment in assignment_rows:
                node_ids.extend(
                    str(value)
                    for value in assignment.get("hierarchy_path_node_ids") or []
                )
                node_ids.append(str(assignment.get("node_id") or ""))
        for row in relationships:
            if str(row.get("relationship_kind") or "") != "OCCURRENCE_CLASSIFICATION":
                continue
            node_id = str(row.get("dictionary_item_id") or "")
            while node_id:
                node_ids.append(node_id)
                node_id = str(
                    (self.classifications.get(node_id) or {}).get("parent_node_id")
                    or ""
                )
        return _unique(node_ids)

    def _result_component_context(self, component_id, relationships):
        """Materialize one immutable result component without widening it."""
        relationships = list(relationships)
        sign_ids = _unique(
            str(row.get("public_sign_id") or "") for row in relationships
        )
        if len(sign_ids) != 1:
            raise ValueError(
                "A result component does not resolve to one canonical sign identity."
            )
        sign_id = sign_ids[0]
        work_ids = _unique(
            str(row.get("work_id") or "") for row in relationships
        )
        report_ids = _unique(
            str(row.get("report_id") or "") for row in relationships
        )
        if len(work_ids) != 1 or len(report_ids) != 1:
            raise ValueError(
                "A result component crosses source work or report identity."
            )
        occurrence_ids = _unique(
            str(row.get("result_occurrence_id") or "") for row in relationships
        )
        if not occurrence_ids:
            raise ValueError("A result component has no member occurrence identity.")
        target_references = [
            reference
            for row in relationships
            for reference in (
                self.target_reference(
                    str(row["relationship_kind"]), str(row["relationship_id"])
                ),
            )
            if reference is not None and self._target_reference_is_effective(reference)
        ]
        anatomy_matches = []
        for reference in target_references:
            result = reference["result_relationship"]
            if str(result.get("axis") or "") != "LOCALIZATION":
                continue
            for target in self.anatomy_targets_for_reference(reference):
                if not target["discoverable"]:
                    continue
                anatomy_id = str(target["anatomy_id"])
                display_link = self.anatomy_display_region_by_anatomy.get(
                    anatomy_id
                ) or {}
                anatomy_matches.append({
                    **target,
                    "relationship_kind": str(reference["relationship_kind"]),
                    "relationship_id": str(reference["relationship_id"]),
                    "context_modifier_ids": list(
                        result.get("context_modifier_ids") or []
                    ),
                    "evidence_partition": str(
                        result.get("evidence_partition") or ""
                    ),
                    "presentation_disposition": str(
                        result.get("presentation_disposition") or ""
                    ),
                    "source_anatomy_id": str(
                        result.get("dictionary_item_id") or ""
                    ),
                    "source_anatomy_term": str(
                        result.get("source_native_relationship_term") or ""
                    ),
                    "anatomy_label": str(
                        (self.anatomy.get(anatomy_id) or {}).get("label") or ""
                    ),
                    "display_region_id": str(
                        display_link.get("display_region_id") or ""
                    ),
                })
        statistic_ids = _unique(
            str(value)
            for row in relationships for value in row.get("statistic_ids") or []
        )
        return {
            "context_kind": "RESULT_COMPONENT",
            "context_id": str(component_id),
            "stable_identity": str(component_id),
            "result_component_id": str(component_id),
            "result_occurrence_ids": occurrence_ids,
            "finding_refs": _unique(
                str(row.get("finding_ref") or "") for row in relationships
            ),
            "work_ids": work_ids,
            "report_ids": report_ids,
            "public_sign_id": sign_id,
            "relationships": relationships,
            "target_references": target_references,
            "anatomy_matches": anatomy_matches,
            "region_ids": _unique(
                row["display_region_id"] for row in anatomy_matches
            ),
            "phase_ids": self._phase_ids_from_relationships(relationships),
            "event_group_ids": self.event_group_ids_for_occurrences(
                occurrence_ids
            ),
            "classification_node_ids": self._classification_context_ids(
                sign_id, relationships
            ),
            "lateralization_ids": _unique(
                str(row.get("dictionary_item_id") or "")
                for row in relationships
                if str(row.get("axis") or "") == "LATERALIZATION"
                and row.get("target_usable") is True
            ),
            "statistic_ids": statistic_ids,
            "metric_types": _unique(
                str(self.statistics[statistic_id].get("metric_type") or "")
                for statistic_id in statistic_ids
                if statistic_id in self.statistics
            ),
            "evidence_partitions": _unique(
                str(row.get("evidence_partition") or "")
                for row in relationships
            ),
            "presentation_dispositions": _unique(
                str(row.get("presentation_disposition") or "")
                for row in relationships
            ),
        }

    def _source_anatomy_context(self, row):
        """Expose unresolved native anatomy without making clinical membership."""
        occurrence_id = str(row.get("result_occurrence_id") or "")
        component_id = str(row.get("result_component_id") or "")
        component_rows = self.relationships_by_component.get(component_id, ())
        sign_id = str(row.get("public_sign_id") or "")
        return {
            "context_kind": "SOURCE_ANATOMY_CONTEXT",
            "context_id": str(row["evidence_link_id"]),
            "stable_identity": str(row["evidence_link_id"]),
            "result_component_id": component_id,
            "result_occurrence_ids": [occurrence_id] if occurrence_id else [],
            "finding_refs": [str(row["finding_ref"])],
            "work_ids": [str(row["work_id"])],
            "report_ids": [str(row["report_id"])],
            "public_sign_id": sign_id,
            "relationships": list(component_rows),
            "target_references": [],
            "anatomy_matches": [{
                "anatomy_id": None,
                "display_region_id": None,
                "retrieval_scope": "SOURCE_ONLY",
                "relationship_kind": "SOURCE_ANATOMY_CONTEXT",
                "relationship_id": str(row["evidence_link_id"]),
                "source_native_anatomy_term": str(
                    row.get("source_native_anatomy_term") or ""
                ),
            }],
            "region_ids": [],
            "phase_ids": (
                self._phase_ids_from_relationships(component_rows)
                if occurrence_id else []
            ),
            "event_group_ids": (
                self.event_group_ids_for_occurrences([occurrence_id])
                if occurrence_id else []
            ),
            "classification_node_ids": (
                self._classification_context_ids(sign_id, component_rows)
                if occurrence_id and sign_id else []
            ),
            "lateralization_ids": _unique(
                str(component.get("dictionary_item_id") or "")
                for component in component_rows
                if str(component.get("axis") or "") == "LATERALIZATION"
                and component.get("target_usable") is True
            ),
            "statistic_ids": [
                str(value) for value in row.get("statistic_ids") or []
            ],
            "metric_types": _unique(
                str(self.statistics[str(value)].get("metric_type") or "")
                for value in row.get("statistic_ids") or []
                if str(value) in self.statistics
            ),
            "evidence_partitions": [str(row["evidence_partition"])],
            "presentation_dispositions": [
                str(row["presentation_disposition"])
            ],
            "source_anatomy_context": row,
        }

    def query_evidence_contexts(
        self, *, sign_ids=None, result_component_ids=None,
        result_occurrence_ids=None, region_ids=None, anatomy_ids=None,
        retrieval_scopes=None, phase_ids=None, classification_node_ids=None,
        lateralization_ids=None, source_ids=None, statistic_ids=None,
        metric_types=None, evidence_partitions=None,
        presentation_dispositions=None, context_kinds=("RESULT_COMPONENT",),
        counted_unit="RESULT_COMPONENT",
    ):
        """Query all scientific facets against the same owning component."""
        filters = {
            "sign_ids": self._query_values(sign_ids),
            "result_component_ids": self._query_values(result_component_ids),
            "result_occurrence_ids": self._query_values(result_occurrence_ids),
            "region_ids": self._query_values(region_ids),
            "anatomy_ids": self._query_values(anatomy_ids),
            "retrieval_scopes": self._query_values(retrieval_scopes),
            "phase_ids": self._query_values(phase_ids),
            "classification_node_ids": self._query_values(
                classification_node_ids
            ),
            "lateralization_ids": self._query_values(lateralization_ids),
            "source_ids": self._query_values(source_ids),
            "statistic_ids": self._query_values(statistic_ids),
            "metric_types": self._query_values(metric_types),
            "evidence_partitions": self._query_values(evidence_partitions),
            "presentation_dispositions": self._query_values(
                presentation_dispositions
            ),
        }
        allowed_kinds = self._query_values(context_kinds) or set()
        unknown_kinds = allowed_kinds - {
            "RESULT_COMPONENT", "SOURCE_ANATOMY_CONTEXT",
        }
        if unknown_kinds:
            raise ValueError(f"Unknown evidence context kinds: {sorted(unknown_kinds)}")
        if counted_unit not in {
            "RESULT_COMPONENT", "FINDING", "WORK", "STATISTIC", "SIGN",
            "SOURCE_CONTEXT",
        }:
            raise ValueError("Evidence query has an unsupported counted unit.")
        rows = []
        if not hasattr(self, "_query_context_rows"):
            self._query_context_rows = {}
        if "RESULT_COMPONENT" in allowed_kinds:
            if "RESULT_COMPONENT" not in self._query_context_rows:
                self._query_context_rows["RESULT_COMPONENT"] = tuple(
                    self._result_component_context(component_id, relationships)
                    for component_id, relationships in self.relationships_by_component.items()
                )
            rows.extend(self._query_context_rows["RESULT_COMPONENT"])
        if "SOURCE_ANATOMY_CONTEXT" in allowed_kinds:
            if "SOURCE_ANATOMY_CONTEXT" not in self._query_context_rows:
                self._query_context_rows["SOURCE_ANATOMY_CONTEXT"] = tuple(
                    self._source_anatomy_context(row)
                    for row in getattr(self, "source_anatomy_contexts", ())
                )
            rows.extend(self._query_context_rows["SOURCE_ANATOMY_CONTEXT"])

        def intersects(values, expected):
            return expected is None or bool(set(values).intersection(expected))

        def matches(row):
            if filters["sign_ids"] is not None and row["public_sign_id"] not in filters["sign_ids"]:
                return False
            if (
                filters["result_component_ids"] is not None
                and row["result_component_id"] not in filters["result_component_ids"]
            ):
                return False
            if not intersects(
                row["result_occurrence_ids"], filters["result_occurrence_ids"]
            ):
                return False
            if not intersects(row["region_ids"], filters["region_ids"]):
                return False
            anatomy_matches = [
                match for match in row["anatomy_matches"]
                if filters["retrieval_scopes"] is None
                or match["retrieval_scope"] in filters["retrieval_scopes"]
            ]
            if filters["retrieval_scopes"] is not None and not anatomy_matches:
                return False
            if filters["anatomy_ids"] is not None and not any(
                match["anatomy_id"] in filters["anatomy_ids"]
                for match in anatomy_matches
            ):
                return False
            if filters["region_ids"] is not None and not any(
                match["display_region_id"] in filters["region_ids"]
                for match in anatomy_matches
            ):
                return False
            if not intersects(row["phase_ids"], filters["phase_ids"]):
                return False
            if not intersects(
                row["classification_node_ids"],
                filters["classification_node_ids"],
            ):
                return False
            if not intersects(
                row["lateralization_ids"], filters["lateralization_ids"]
            ):
                return False
            if filters["source_ids"] is not None and not (
                set(row["work_ids"] + row["report_ids"])
                .intersection(filters["source_ids"])
            ):
                return False
            if not intersects(row["statistic_ids"], filters["statistic_ids"]):
                return False
            if not intersects(row["metric_types"], filters["metric_types"]):
                return False
            if not intersects(
                row["evidence_partitions"], filters["evidence_partitions"]
            ):
                return False
            return intersects(
                row["presentation_dispositions"],
                filters["presentation_dispositions"],
            )

        rows = [row for row in rows if matches(row)]
        identity_field = {
            "RESULT_COMPONENT": "result_component_id",
            "FINDING": "finding_refs",
            "WORK": "work_ids",
            "STATISTIC": "statistic_ids",
            "SIGN": "public_sign_id",
            "SOURCE_CONTEXT": "context_id",
        }[counted_unit]
        counted_ids = _unique(
            value
            for row in rows
            for value in (
                row[identity_field]
                if isinstance(row[identity_field], list)
                else [row[identity_field]]
            )
        )
        return {
            "counted_unit": counted_unit,
            "counted_ids": counted_ids,
            "count": len(counted_ids),
            "rows": rows,
        }

    def source_native_terms_for_sign(self, sign_id):
        """Return only source-native terms carried by owned result occurrences."""
        return _unique(
            str(row.get("source_native_sign_term") or "")
            for row in self.relationships_by_sign.get(str(sign_id), ())
        )

    def result_relationship(self, relationship_id, relationship_kind=None):
        row = self.result_relationship_by_id.get(str(relationship_id))
        if (
            row is not None and relationship_kind is not None
            and str(row["relationship_kind"]) != str(relationship_kind)
        ):
            return None
        return row

    def target_reference(self, relationship_kind, relationship_id):
        return self.target_reference_by_key.get(
            (str(relationship_kind), str(relationship_id))
        )

    def context_modifiers_for_target_reference(self, reference):
        """Resolve only modifiers bound to this exact exported target edge."""
        result = reference.get("result_relationship") if reference else None
        if not result or str(result.get("relationship_kind") or "") != "AXIS_EVIDENCE":
            return []
        return [
            {
                "relationship_kind": "CONTEXT_MODIFIER",
                "relationship_id": str(modifier_id),
                "result_relationship": self.context_modifier_result_by_id[
                    str(modifier_id)
                ],
            }
            for modifier_id in result.get("context_modifier_ids") or []
        ]

    @staticmethod
    def _target_reference_is_effective(reference):
        result = reference["result_relationship"]
        return result.get("target_usable") is True

    def target_references_for_sign(
        self, sign_id, axis=None, *, usable_only=False,
        presentation_disposition=None,
    ):
        axes = (
            (str(axis).upper(),) if axis is not None
            else ("LATERALIZATION", "LOCALIZATION")
        )
        rows = [
            reference
            for value in axes
            for reference in self.target_references_by_sign_axis.get(
                (str(sign_id), value), ()
            )
            for result in (reference["result_relationship"],)
            if not usable_only or self._target_reference_is_effective(reference)
            if presentation_disposition is None
            or str(result["presentation_disposition"])
            == str(presentation_disposition)
        ]
        return sorted(rows, key=lambda row: (
            str(row["relationship_kind"]), str(row["relationship_id"]),
        ))

    def target_references_for_findings(self, finding_refs, axis=None):
        finding_refs = {str(value) for value in finding_refs}
        return sorted([
            row for row in self.target_reference_by_key.values()
            if str(row["result_relationship"]["finding_ref"]) in finding_refs
            and (axis is None or str(row["result_relationship"]["axis"])
                 == str(axis).upper())
        ], key=lambda row: (
            str(row["relationship_kind"]), str(row["relationship_id"]),
        ))

    def target_references_for_statistics(self, statistic_ids, axis=None):
        statistic_ids = {str(value) for value in statistic_ids}
        return sorted([
            row for row in self.target_reference_by_key.values()
            if statistic_ids.intersection(
                str(value)
                for value in row["result_relationship"]["statistic_ids"]
            )
            and (axis is None or str(row["result_relationship"]["axis"])
                 == str(axis).upper())
        ], key=lambda row: (
            str(row["relationship_kind"]), str(row["relationship_id"]),
        ))

    def relationships_for_sign(
        self, sign_id, axis=None, *, usable_only=False,
        presentation_disposition=None,
    ):
        axes = (
            (str(axis).upper(),) if axis is not None
            else ("LATERALIZATION", "LOCALIZATION")
        )
        rows = [
            row
            for value in axes
            for row in self.relationships_by_sign_axis.get(
                (str(sign_id), value), ()
            )
            if str(row["relationship_kind"]) in {
                "AXIS_EVIDENCE", "COHORT_FALLBACK", "CONTEXT_MODIFIER",
            }
            if not usable_only or row.get("target_usable") is True
            if presentation_disposition is None
            or str(row.get("presentation_disposition") or "")
            == str(presentation_disposition)
        ]
        return sorted(
            rows,
            key=lambda row: (
                str(row["relationship_kind"]), str(row["relationship_id"])
            ),
        )

    def relationships_for_statistics(self, statistic_ids, axis=None):
        """Resolve statistics through result-owned relationship references."""
        statistic_ids = {str(value) for value in statistic_ids}
        rows = [
            row for row in self.result_relationships
            if statistic_ids.intersection(
                str(value) for value in row["statistic_ids"]
            )
            and str(row["relationship_kind"]) in {
                "AXIS_EVIDENCE", "COHORT_FALLBACK", "CONTEXT_MODIFIER",
            }
            and (axis is None or str(row.get("axis") or "") == str(axis).upper())
        ]
        return sorted(
            rows,
            key=lambda row: (
                str(row["relationship_kind"]), str(row["relationship_id"])
            ),
        )

    def owned_result_relationships_for_statistics(self, statistic_ids):
        """Return shipped result rows without widening their scientific role."""
        statistic_ids = {str(value) for value in statistic_ids}
        return sorted(
            (
                row for row in self.result_relationships
                if statistic_ids.intersection(
                    str(value) for value in row["statistic_ids"]
                )
            ),
            key=lambda row: (
                str(row["relationship_kind"]), str(row["relationship_id"])
            ),
        )

    def relationships_for_findings(
        self, finding_refs, axis=None, *, usable_only=False,
        presentation_disposition=None,
    ):
        rows = [
            row
            for finding_ref in {str(value) for value in finding_refs}
            for row in self.relationships_by_finding.get(finding_ref, ())
            if str(row["relationship_kind"]) in {
                "AXIS_EVIDENCE", "COHORT_FALLBACK", "CONTEXT_MODIFIER",
            }
            if axis is None or str(row.get("axis") or "") == str(axis).upper()
            if not usable_only or row.get("target_usable") is True
            if presentation_disposition is None
            or str(row.get("presentation_disposition") or "")
            == str(presentation_disposition)
        ]
        return sorted(
            rows,
            key=lambda row: (
                str(row["relationship_kind"]), str(row["relationship_id"])
            ),
        )

    def owned_result_relationships_for_findings(self, finding_refs):
        """Return exact shipped result rows owned by the requested findings."""
        return sorted(
            (
                row
                for finding_ref in {str(value) for value in finding_refs}
                for row in self.relationships_by_finding.get(finding_ref, ())
            ),
            key=lambda row: (
                str(row["relationship_kind"]), str(row["relationship_id"])
            ),
        )

    def statistic_ids_for_relationship(self, relationship):
        result = relationship.get("result_relationship", relationship)
        return sorted({
            str(value) for value in result.get("statistic_ids") or []
        })

    def context_local_lateralization_codes(self, relationship):
        result = relationship.get("result_relationship", relationship)
        occurrence_id = str(result.get("result_occurrence_id") or "")
        sign_id = str(result.get("public_sign_id") or "")
        if not occurrence_id:
            return []
        return _unique(
            str(row.get("dictionary_item_id") or "")
            for row in self.relationships_by_occurrence.get(occurrence_id, ())
            if str(row.get("public_sign_id") or "") == sign_id
            and str(row.get("axis") or "") == "LATERALIZATION"
            and str(row.get("relationship_kind") or "") in {
                "AXIS_EVIDENCE", "COHORT_FALLBACK",
            }
            and row.get("target_usable") is True
        )

    def reference_rows(self, edge_kind):
        return tuple(self.reference_edges_by_kind.get(edge_kind, ()))

    def reference_rows_from(self, edge_kind, source_node_id):
        return tuple(self.reference_edges_from.get(
            (edge_kind, str(source_node_id)), ()
        ))

    def reference_rows_to(self, edge_kind, target_node_id):
        return tuple(self.reference_edges_to.get(
            (edge_kind, str(target_node_id)), ()
        ))

    def finding_refs_for_sign(self, sign_id):
        raise RuntimeError(
            "Private finding identities are not part of the public relationship API."
        )

    def source_sign_ids_for_sign(self, sign_id):
        raise RuntimeError(
            "Private source-sign identities are not part of the public relationship API."
        )

    def citation_links_for_finding(self, finding_ref):
        return tuple(self.citation_links_by_finding.get(str(finding_ref), ()))

    def statistic_occurrence_assignments_for_statistic(self, statistic_id):
        return tuple(self.statistic_occurrence_assignments_by_statistic.get(
            str(statistic_id), ()
        ))

    def sign_ids_for_findings(self, finding_refs):
        raise RuntimeError(
            "Private finding identities are not part of the public relationship API."
        )

    def sign_ids_for_statistics(self, statistic_ids):
        statistic_ids = {str(value) for value in statistic_ids}
        return _unique(
            str(row.get("public_sign_id") or "")
            for statistic_id in statistic_ids
            for row in self.relationships_by_statistic.get(statistic_id, ())
            if row.get("public_sign_id")
        )

    def evidence_context_ids_for_statistics(self, statistic_ids):
        raise RuntimeError(
            "Private evidence-context identities are not part of the public relationship API."
        )

    def finding_refs_for_statistics(self, statistic_ids):
        raise RuntimeError(
            "Private finding identities are not part of the public relationship API."
        )

    def _phase_ids_from_relationships(self, rows):
        phase_ids = _unique(
            str(row.get("dictionary_item_id") or "")
            for row in rows
            if str(row.get("relationship_kind") or "") == "PHASE"
            and str(row.get("dictionary_domain") or "") == "PHASE"
        )
        return sorted(phase_ids, key=lambda phase_id: (
            self.phases[phase_id]["ordinal"],
            str(self.phases[phase_id]["label"]).casefold(), phase_id,
        ))

    def phase_ids_for_sign(self, sign_id):
        return self._phase_ids_from_relationships(
            self.relationships_by_sign.get(str(sign_id), ())
        )

    def phase_ids_for_findings(self, finding_refs):
        raise RuntimeError(
            "Private finding identities are not part of the public relationship API."
        )

    def phase_ids_for_statistics(self, statistic_ids):
        return self._phase_ids_from_relationships(
            row
            for statistic_id in map(str, statistic_ids)
            for row in self.relationships_by_statistic.get(statistic_id, ())
        )

    def phase_ids_for_occurrences(self, occurrence_ids):
        return self._phase_ids_from_relationships(
            row
            for occurrence_id in map(str, occurrence_ids)
            for row in self.relationships_by_occurrence.get(occurrence_id, ())
        )

    def event_group_ids_for_occurrences(self, occurrence_ids):
        """Traverse phase and classification dictionaries for exact occurrences."""
        targets = set()
        for occurrence_id in map(str, occurrence_ids):
            rows = self.relationships_by_occurrence.get(occurrence_id, ())
            for row in rows:
                if row["relationship_kind"] == "PHASE":
                    targets.add(("PHASE", str(row["dictionary_item_id"])))
                if row["relationship_kind"] == "OCCURRENCE_CLASSIFICATION":
                    node_id = str(row["dictionary_item_id"])
                    while node_id:
                        targets.add(("CLASSIFICATION", node_id))
                        node_id = str(self.classifications[node_id].get("parent_node_id") or "")
                if row["relationship_kind"] == "SIGN_IDENTITY":
                    for scheme in self.projection_contract["classification_public_schemes"]:
                        for assignment in self.classification_assignments_for_sign(
                            row["public_sign_id"], scheme,
                        ):
                            if assignment.get("resolution_status") != "RESOLVED":
                                continue
                            targets.update(("CLASSIFICATION", str(node_id)) for node_id in
                                           assignment["hierarchy_path_node_ids"])
        return [
            str(group["node_id"]) for group in self.node_groups["event_groups"]
            if any((member["dictionary_domain"], member["dictionary_item_id"]) in targets
                   for member in group["members"])
        ]

    def phase_labels(self, phase_ids):
        return [str(self.phases[phase_id]["label"]) for phase_id in phase_ids]

    def _phase_source_values_from_relationships(self, rows):
        return _unique(
            str(row.get("source_native_relationship_term") or "")
            for row in rows
            if str(row.get("relationship_kind") or "") == "PHASE"
        )

    def phase_source_values_for_sign(self, sign_id):
        return self._phase_source_values_from_relationships(
            self.relationships_by_sign.get(str(sign_id), ())
        )

    def phase_source_values_for_findings(self, finding_refs):
        raise RuntimeError(
            "Private finding identities are not part of the public relationship API."
        )

    def phase_source_values_for_statistics(self, statistic_ids):
        return self._phase_source_values_from_relationships(
            row
            for statistic_id in map(str, statistic_ids)
            for row in self.relationships_by_statistic.get(statistic_id, ())
        )

    def phase_source_values_for_occurrences(self, occurrence_ids):
        return self._phase_source_values_from_relationships(
            row
            for occurrence_id in map(str, occurrence_ids)
            for row in self.relationships_by_occurrence.get(occurrence_id, ())
        )

    def statistic_ids_for_finding(self, finding_ref):
        raise RuntimeError(
            "Private finding identities are not part of the public relationship API."
        )

    def source_ids_for_findings(self, finding_refs):
        raise RuntimeError(
            "Private source identities are not part of the public relationship API."
        )

    def finding_refs_for_source(self, source_id):
        raise RuntimeError(
            "Private source identities are not part of the public relationship API."
        )

    def classification_node_ids_for_sign(self, sign_id, scheme_ids=None):
        sign_id = str(sign_id)
        scheme_ids = set(self.projection_contract["classification_public_schemes"]) if (
            scheme_ids is None
        ) else {
            str(value) for value in (
                [scheme_ids] if isinstance(scheme_ids, str) else scheme_ids
            )
        }
        return _unique(
            str(row["node_id"])
            for scheme_id in sorted(scheme_ids)
            for row in self.classification_assignments_for_sign(sign_id, scheme_id)
            if str(row["resolution_status"]) == "RESOLVED"
        )

    def classification_assignments_for_sign(self, sign_id, scheme_id):
        return self.classification_assignment_by_sign_scheme.get(
            (str(sign_id), str(scheme_id)), ()
        )

    def classification_assignment_for_sign(self, sign_id, scheme_id):
        rows = self.classification_assignments_for_sign(sign_id, scheme_id)
        return rows[0] if len(rows) == 1 else None

    def classification_terminology_terms_for_nodes(self, node_ids):
        return _unique(
            str(row["source_native_term"])
            for node_id in node_ids
            for row in self.classification_terminology_by_node.get(
                str(node_id), ()
            )
        )

    def active_classification_scheme_ids(self, family):
        """Return graph-owned sign-classification schemes for one family."""
        family = str(family or "").strip().upper().replace("-", "_")
        if not family:
            raise ValueError("Classification family is required.")
        declared = self.projection_contract["classification_public_schemes"]
        return sorted({
            scheme_id
            for scheme_id in map(str, declared)
            if scheme_id
            and (
                scheme_id.upper().replace("-", "_") == family
                or scheme_id.upper().replace("-", "_").startswith(
                    family + "_"
                )
            )
        })

    def single_active_classification_scheme_id(self, family):
        """Require the one public organizational scheme for a family."""
        scheme_ids = self.active_classification_scheme_ids(family)
        if len(scheme_ids) != 1:
            raise ValueError(
                f"Expected exactly one active {family} classification scheme; "
                f"found {scheme_ids!r}."
            )
        scheme_id = scheme_ids[0]
        return scheme_id

    def classification_node_ids_for_statistics(self, statistic_ids, scheme_ids=None):
        """Return canonical sign assignments for exact statistic occurrences."""
        sign_ids = self.sign_ids_for_statistics(statistic_ids)
        return _unique([
            node_id for sign_id in sign_ids
            for node_id in self.classification_node_ids_for_sign(
                sign_id, scheme_ids
            )
        ])

    def statistic_ids_for_placement(self, placement):
        """Return only atomic statistics linked to this exact placement context."""
        relationship = placement.get("result_relationship") or placement
        if "statistic_ids" not in relationship:
            placement_edge_id = str(placement.get("placement_edge_id") or "")
            relationship = self.result_relationship(
                placement_edge_id, "AXIS_EVIDENCE"
            )
        if not relationship:
            raise ValueError(
                "Placement does not resolve an exact shipped result relationship."
            )
        return self.statistic_ids_for_relationship(relationship)

    def axis_evidence_memberships_for_sign(self, sign_id, axis):
        """Return the ordered typed evidence memberships for one public summary."""
        return list(self.axis_evidence_memberships_by_sign_axis.get(
            (str(sign_id), str(axis).upper()), ()
        ))

    def axis_evidence_memberships_for_findings(
        self, finding_refs, *, ownership_kind=None
    ):
        """Return typed axis ownership for exact findings, never inferred targets."""
        rows = [
            row
            for finding_ref in {str(value) for value in finding_refs}
            for row in self.axis_evidence_memberships_by_finding.get(
                finding_ref, ()
            )
            if ownership_kind is None
            or str(row.get("ownership_kind") or "") == ownership_kind
        ]
        return sorted(rows, key=lambda row: str(row["membership_edge_id"]))

    def axis_evidence_memberships_for_statistics(self, statistic_ids):
        """Return typed axis ownership for exact atomic statistics."""
        rows = [
            row
            for statistic_id in {str(value) for value in statistic_ids}
            for row in self.axis_evidence_memberships_by_statistic.get(
                statistic_id, ()
            )
        ]
        return sorted(rows, key=lambda row: str(row["membership_edge_id"]))

    def _axis_membership_projection(self, sign_id, axis):
        rows = self.axis_evidence_memberships_for_sign(sign_id, axis)
        grouped = {}
        for row in rows:
            grouped.setdefault(str(row["source_work_id"]), []).append(row)
        groups = OrderedDict(
            (work_id, grouped[work_id]) for work_id in sorted(grouped)
        )
        finding_refs = sorted({str(row["finding_ref"]) for row in rows})
        return {
            "rows": rows,
            "groups": groups,
            "membership_edge_ids": sorted(
                str(row["membership_edge_id"]) for row in rows
            ),
            "finding_refs": finding_refs,
            "statistic_ids": sorted({
                str(row["statistic_id"]) for row in rows
                if row.get("statistic_id") not in (None, "")
            }),
            "work_ids": list(groups),
        }

    def validate_weighted_contribution(self, sign_id, axis, contribution):
        """Fail unless one weighted work names its exact graph-owned rows."""
        sign_id = str(sign_id)
        axis = str(axis).upper()
        work_id = str(contribution.get("work_id") or "")
        membership_rows = self.axis_evidence_memberships_by_sign_axis_work.get(
            (sign_id, axis, work_id), ()
        )
        expected_findings = sorted({
            str(row["finding_ref"]) for row in membership_rows
        })
        actual_finding_rows = [
            str(value) for value in contribution.get("row_finding_refs") or []
        ]
        if (
            not work_id or not membership_rows
            or len(actual_finding_rows) != len(set(actual_finding_rows))
            or actual_finding_rows != expected_findings
        ):
            raise ValueError("Weighted contribution finding membership differs from graph.")
        expected_statistics = sorted({
            str(row["statistic_id"]) for row in membership_rows
            if row.get("statistic_id") not in (None, "")
        })
        actual_statistic_rows = [
            str(value) for value in contribution.get("row_statistic_ids") or []
        ]
        if (
            len(actual_statistic_rows) != len(set(actual_statistic_rows))
            or actual_statistic_rows != expected_statistics
        ):
            raise ValueError("Weighted contribution statistic membership differs from graph.")
        primary_statistics = [
            str(value)
            for value in contribution.get("primary_input_statistic_ids") or []
        ]
        if (
            primary_statistics != sorted(set(primary_statistics))
            or not set(primary_statistics).issubset(expected_statistics)
        ):
            raise ValueError(
                "Weighted contribution primary inputs differ from graph statistics."
            )
        owns_weight_eligible_relationship = any(
            row.get("target_usable") is True
            and str(row["relationship_disposition"]) in {
                "DIRECT_TARGET_RELATIONSHIP",
                "COHORT_FALLBACK_RELATIONSHIP",
            }
            and row.get("independent_evidence") is True
            and str(row.get("presentation_disposition") or "")
            == "PRIMARY_RESULT_PLACEMENT"
            and str(row.get("evidence_partition") or "") in {
                "PRIMARY_EVIDENCE", "CASE_EVIDENCE",
            }
            for row in membership_rows
        )
        if not owns_weight_eligible_relationship:
            try:
                nonzero_weight = float(contribution.get("final_weight") or 0) != 0
            except (TypeError, ValueError):
                nonzero_weight = True
            if nonzero_weight:
                raise ValueError(
                    "A nonprimary or targetless contribution has nonzero weight."
                )

    def project_weighted_contributions(self, sign_id, axis, metadata_rows):
        """Attach non-relational weight metadata to exact graph-owned memberships."""
        sign_id = str(sign_id)
        axis = str(axis).upper()
        metadata_by_work = {}
        for row in metadata_rows or ():
            work_id = str(row.get("work_id") or "")
            if not work_id or work_id in metadata_by_work:
                raise ValueError("Weighted contribution metadata has duplicate work identity.")
            metadata_by_work[work_id] = row
        projection = self._axis_membership_projection(sign_id, axis)
        expected_by_work = projection["groups"]
        if set(metadata_by_work) != set(expected_by_work):
            raise ValueError(
                "Weighted contribution metadata works differ from graph evidence."
            )
        projected = []
        for work_id in expected_by_work:
            self.validate_weighted_contribution(
                sign_id, axis, metadata_by_work[work_id]
            )
            projected.append(deepcopy(metadata_by_work[work_id]))
        self.validate_weighted_contributions(sign_id, axis, projected)
        return projected

    def validate_weighted_contributions(self, sign_id, axis, contributions):
        """Require exactly one contribution for every graph-owned source work."""
        sign_id = str(sign_id)
        axis = str(axis).upper()
        expected_work_ids = set(
            self._axis_membership_projection(sign_id, axis)["work_ids"]
        )
        contributions = list(contributions or [])
        actual_work_ids = [
            str(row.get("work_id") or "") for row in contributions
        ]
        if (
            len(actual_work_ids) != len(set(actual_work_ids))
            or actual_work_ids != sorted(expected_work_ids)
        ):
            raise ValueError(
                "Weighted contribution source works differ from graph."
            )
        for contribution in contributions:
            self.validate_weighted_contribution(sign_id, axis, contribution)
        return expected_work_ids

    def project_axis_summary(self, summary):
        """Validate one canonical summary without reconstructing its payload."""
        sign_id = str(summary.get("sign_id") or "")
        axis = str(summary.get("axis") or "").upper()
        if sign_id not in self.signs or axis not in {
            "LOCALIZATION", "LATERALIZATION",
        }:
            raise ValueError("Weighted-evidence summary has an unknown sign or axis.")
        projection = self._axis_membership_projection(sign_id, axis)
        supplied_ids = summary.get("axis_evidence_membership_edge_ids")
        if (
            not isinstance(supplied_ids, list)
            or len(supplied_ids) != len({str(value) for value in supplied_ids})
            or [str(value) for value in supplied_ids]
            != projection["membership_edge_ids"]
        ):
            raise ValueError(
                "Weighted summary membership edge identities differ from graph."
            )
        contributions = self.project_weighted_contributions(
            sign_id, axis, summary.get("contributions") or []
        )
        target_contract = summary.get("target_contract") or {}
        reported_targets = target_contract.get("reported_targets")
        self._validate_and_bind_reported_targets(
            sign_id, axis, reported_targets
        )
        expected_arrays = {
            "row_finding_refs": projection["finding_refs"],
            "row_statistic_ids": projection["statistic_ids"],
            "row_work_ids": projection["work_ids"],
        }
        for field, expected in expected_arrays.items():
            if [str(value) for value in summary.get(field) or []] != expected:
                raise ValueError(
                    f"Weighted summary {field} differ from typed memberships."
                )
        expected_counts = {
            "row_finding_count": len(projection["finding_refs"]),
            "row_statistic_count": len(projection["statistic_ids"]),
            "row_work_count": len(projection["work_ids"]),
        }
        if any(summary.get(field) != value for field, value in expected_counts.items()):
            raise ValueError("Weighted summary relationship counts differ from memberships.")
        if (
            str(summary.get("preferred_label") or "")
            != str(self.signs[sign_id].get("label") or sign_id)
            or contributions != list(summary.get("contributions") or [])
        ):
            raise ValueError("Weighted summary canonical identity or contribution order differs.")
        return deepcopy(summary)

    def _validate_and_bind_reported_targets(self, sign_id, axis, targets):
        """Bind the canonical summary target payload to exact relationship IDs."""
        if not isinstance(targets, list):
            raise ValueError("Weighted summary has no canonical reported targets.")
        expected_relationships = {
            (str(row["relationship_kind"]), str(row["relationship_id"])): row
            for row in self.target_references_for_sign(
                sign_id, axis, usable_only=True,
                presentation_disposition="PRIMARY_RESULT_PLACEMENT",
            )
        }
        actual_relationships = set()
        target_identities = set()
        for target in targets:
            target_kind = str(target.get("target_kind") or "")
            target_id = str(target.get("target_id") or "")
            target_identity = (target_kind, target_id)
            if (
                target_kind not in {"ANATOMY", "LATERALIZATION"}
                or not target_id
                or target_identity in target_identities
            ):
                raise ValueError("Weighted summary target identity is invalid.")
            target_identities.add(target_identity)
            relationship_ids = {
                str(value) for value in target.get("relationship_ids") or []
            }
            relationships = {
                (str((self.result_relationship(value) or {}).get(
                    "relationship_kind"
                ) or ""), value)
                for value in relationship_ids
            }
            if (
                not relationship_ids
                or {
                    str(value)
                    for value in target.get("relationship_kinds") or []
                } != {kind for kind, _relationship_id in relationships}
                or not relationships.issubset(expected_relationships)
            ):
                raise ValueError(
                    "Weighted summary target relationship references differ."
                )
            rows = [expected_relationships[key] for key in relationships]
            expected_placement_ids = {
                str(row["target_projection"]["placement_edge_id"])
                for row in rows
                if str(row["result_relationship"]["relationship_kind"])
                == "AXIS_EVIDENCE"
            }
            expected_cohort_ids = {
                str(row["result_relationship"]["relationship_id"])
                for row in rows
                if str(row["result_relationship"]["relationship_kind"])
                == "COHORT_FALLBACK"
            }
            if any(
                str(row["result_relationship"].get("dictionary_domain") or "")
                != target_kind
                or str(
                    row["result_relationship"].get("dictionary_item_id") or ""
                ) != target_id
                for row in rows
            ) or {
                str(value) for value in target.get("placement_edge_ids") or []
            } != expected_placement_ids or {
                str(value)
                for value in target.get("cohort_fallback_edge_ids") or []
            } != expected_cohort_ids:
                raise ValueError(
                    "Weighted summary target changes a relationship target."
                )
            actual_relationships.update(relationships)
        if actual_relationships != set(expected_relationships):
            raise ValueError(
                "Weighted summary target set differs from canonical relationships."
            )
        self.axis_targets_by_sign_axis[(str(sign_id), str(axis))] = deepcopy(
            targets
        )

    def context_placements_for_sign(self, sign_id):
        return [
            {
                **reference,
                "target_label": str(
                    (self.anatomy.get(str(
                        reference["result_relationship"]["dictionary_item_id"]
                    )) or {}).get("label")
                    or reference["result_relationship"]["dictionary_item_id"]
                ),
            }
            for reference in self.target_references_for_sign(sign_id)
            if str(reference["result_relationship"]["relationship_kind"])
            == "COHORT_FALLBACK"
        ]

    def context_modifiers_for_sign(self, sign_id):
        return [
            {
                "relationship_kind": "CONTEXT_MODIFIER",
                "relationship_id": str(row["relationship_id"]),
                "result_relationship": row,
            }
            for row in self.relationships_by_sign.get(str(sign_id), ())
            if str(row.get("relationship_kind") or "") == "CONTEXT_MODIFIER"
        ]

    def context_notes_for_sign(self, sign_id, axis=None):
        notes = []
        for reference in self.context_placements_for_sign(sign_id):
            row = reference["result_relationship"]
            if axis is not None and str(row.get("axis") or "") != str(axis):
                continue
            scope = str(row.get("relationship_role") or "").replace("_", " ").title()
            notes.append(
                f'{reference["target_label"]} is {scope.lower()} in the source, not direct sign placement.'
            )
        for reference in self.context_modifiers_for_sign(sign_id):
            row = reference["result_relationship"]
            if axis is not None and str(row.get("axis") or "") not in {"", str(axis)}:
                continue
            text = str(row.get("source_native_relationship_term") or "").strip()
            if text:
                notes.append(text)
        return _unique(notes)

    def region_ids_for_sign(self, sign_id):
        return _unique(
            region_id
            for context in self.query_evidence_contexts(
                sign_ids=[sign_id],
            )["rows"]
            for region_id in context["region_ids"]
            if region_id
        )

    def region_labels_for_sign(self, sign_id):
        return _unique(
            self.display_region_labels.get(region_id)
            for region_id in self.region_ids_for_sign(sign_id)
        )

    @cache
    def browse_contexts_for_sign(self, sign_id):
        """Retain every result component at supported anatomy or source context."""
        contexts = []
        for row in self.query_evidence_contexts(sign_ids=[sign_id])["rows"]:
            relationships = row["relationships"]
            anatomy_regions = _unique(
                self.display_region_labels.get(region_id)
                for region_id in row["region_ids"]
            )
            if anatomy_regions:
                regions = anatomy_regions
            elif "REFERENCE_CONTEXT" in row["presentation_dispositions"]:
                regions = [REFERENCE_CONTEXT_REGION]
            elif any(
                relationship.get("axis") == "LOCALIZATION"
                for relationship in relationships
            ):
                regions = [OTHER_LOCALIZATION_REGION]
            else:
                regions = [UNLINKED_LOCALIZATION_REGION]
            contexts.append({
                "result_component_id": row["result_component_id"],
                "result_occurrence_ids": row["result_occurrence_ids"],
                "relationships": relationships,
                "regions": regions, "anatomy_regions": anatomy_regions,
            })
        return contexts

    def region_map_links_for_sign(
        self, sign_id, *, presentation_disposition="PRIMARY_RESULT_PLACEMENT",
    ):
        """Expose regional map facets from the component query result set."""
        links = []
        seen = set()
        for context in self.query_evidence_contexts(
            sign_ids=[sign_id],
            presentation_dispositions=[presentation_disposition],
        )["rows"]:
            for match in context["anatomy_matches"]:
                region_id = str(match["display_region_id"])
                key = (
                    str(match["relationship_id"]), str(match["anatomy_id"]),
                    str(match["retrieval_scope"]), str(match["traversal_id"]),
                    region_id,
                )
                if not region_id or key in seen:
                    continue
                seen.add(key)
                links.append({
                    "relationship_kind": str(match["relationship_kind"]),
                    "relationship_id": str(match["relationship_id"]),
                    "target_anatomy_id": str(match["anatomy_id"]),
                    "target_label": str(match["anatomy_label"]),
                    "display_region_id": region_id,
                    "display_region_label": self.display_region_labels[region_id],
                    "presentation_disposition": str(
                        match.get("presentation_disposition") or ""
                    ),
                    "retrieval_scope": str(match["retrieval_scope"]),
                    "context_modifier_ids": list(
                        match.get("context_modifier_ids") or []
                    ),
                    "traversal_id": str(match["traversal_id"]),
                    "path_relationship_ids": list(
                        match["path_relationship_ids"]
                    ),
                    "path_relations": list(match["path_relations"]),
                    "path_directions": list(match["path_directions"]),
                })
        return links

    def axis_targets_for_sign(self, sign_id, axis):
        """Group exact usable result relationships for display, without widening."""
        axis = str(axis).upper()
        groups = OrderedDict()
        for reference in self.target_references_for_sign(
            sign_id, axis, usable_only=True,
            presentation_disposition="PRIMARY_RESULT_PLACEMENT",
        ):
            row = reference["result_relationship"]
            target_kind = str(row["dictionary_domain"])
            target_id = str(row["dictionary_item_id"])
            key = (target_kind, target_id)
            if target_kind == "ANATOMY":
                label = str((self.anatomy.get(target_id) or {}).get("label") or "")
                display_region_ids = self.region_ids_for_target_reference(reference)
                area_ids = _unique(
                    str((self.anatomy.get(target["anatomy_id"]) or {}).get(
                        "atlas_native_id"
                    ) or "")
                    for target in self.anatomy_targets_for_reference(reference)
                    if self._is_brodmann_node(
                        self.anatomy.get(target["anatomy_id"]) or {}
                    )
                )
                public_key = target_id
            else:
                label = LATERALIZATION_LABELS.get(target_id, target_id)
                display_region_ids = []
                area_ids = []
                public_key = "nonassoc" if target_id == "nonlat" else target_id
            target = groups.setdefault(key, {
                "target_kind": target_kind,
                "target_id": target_id,
                "key": public_key,
                "label": label,
                "display_region_ids": [],
                "area_ids": [],
                "relationship_ids": [],
                "relationship_kinds": [],
                "placement_edge_ids": [],
                "cohort_fallback_edge_ids": [],
            })
            target["display_region_ids"] = _unique([
                *target["display_region_ids"], *display_region_ids,
            ])
            target["area_ids"] = _unique([*target["area_ids"], *area_ids])
            relationship_id = str(row["relationship_id"])
            kind = str(row["relationship_kind"])
            target["relationship_ids"] = _unique([
                *target["relationship_ids"], relationship_id,
            ])
            target["relationship_kinds"] = _unique([
                *target["relationship_kinds"], kind,
            ])
            subset = (
                "placement_edge_ids" if kind == "AXIS_EVIDENCE"
                else "cohort_fallback_edge_ids"
            )
            target[subset] = _unique([*target[subset], relationship_id])
        return list(groups.values())

    @staticmethod
    def _is_brodmann_node(node):
        return str(node.get("atlas_family_id") or node.get("atlas_id") or "").upper() == "BRODMANN"

    def brodmann_map_links_for_sign(
        self, sign_id, *, presentation_disposition="PRIMARY_RESULT_PLACEMENT",
    ):
        """Return Brodmann facets from the same component query as regions."""
        if presentation_disposition not in PRESENTATION_DISPOSITIONS:
            raise ValueError("Brodmann links require a public presentation partition.")
        links = []
        seen = set()
        for context in self.query_evidence_contexts(
            sign_ids=[sign_id],
            presentation_dispositions=[presentation_disposition],
        )["rows"]:
            for target in context["anatomy_matches"]:
                node = self.anatomy.get(target["anatomy_id"]) or {}
                if not self._is_brodmann_node(node):
                    continue
                area_id = str(node.get("atlas_native_id") or "")
                key = (
                    str(target["relationship_id"]), area_id,
                    str(target["retrieval_scope"]), str(target["traversal_id"]),
                )
                if not area_id or key in seen:
                    continue
                seen.add(key)
                display_link = self.anatomy_display_region_by_anatomy.get(
                    target["anatomy_id"]
                ) or {}
                display_region_id = str(
                    display_link.get("display_region_id") or ""
                )
                links.append({
                    "area_id": area_id,
                    "relationship_kind": str(target["relationship_kind"]),
                    "relationship_id": str(target["relationship_id"]),
                    "traversal_id": target["traversal_id"],
                    "retrieval_scope": target["retrieval_scope"],
                    "context_modifier_ids": list(
                        target.get("context_modifier_ids") or []
                    ),
                    "path_relationship_ids": target["path_relationship_ids"],
                    "path_relations": target["path_relations"],
                    "path_directions": target["path_directions"],
                    "target_anatomy_id": target["anatomy_id"],
                    "target_label": str(node.get("label") or ""),
                    "display_region_id": display_region_id,
                    "display_region_label": str(
                        self.display_region_labels.get(display_region_id) or ""
                    ),
                    "presentation_disposition": str(
                        target.get("presentation_disposition") or ""
                    ),
                })
        return links

    def brodmann_areas_for_sign(self, sign_id):
        return _unique(row["area_id"] for row in self.brodmann_map_links_for_sign(sign_id))

    def classification_projection(self):
        nodes = [
            {
                **row,
                "node_id": str(row["classification_node_id"]),
                "node_kind": row.get("node_type"),
            }
            for row in self.node_groups.get("classifications", ())
        ]
        mappings = [
            {
                "sign_id": str(row["public_sign_id"]),
                "node_id": str(row["node_id"]),
                "relation": row.get("relation"),
            }
            for row in self.classification_assignments
            if str(row.get("resolution_status") or "") == "RESOLVED"
        ]
        return {"nodes": nodes, "sign_mappings": mappings}

    def assert_matches_database(self, database_path):
        """Compare the payload with the ledger's serialized public projection."""
        database_path = Path(database_path).resolve(strict=True)
        connection = sqlite3.connect(
            f"file:{database_path.as_posix()}?mode=ro&immutable=1", uri=True
        )
        try:
            rows = connection.execute(
                "SELECT section_name,group_name,row_ordinal,row_json "
                "FROM public_scientific_relationship_graph_rows "
                "ORDER BY section_name,group_name,row_ordinal"
            ).fetchall()
        finally:
            connection.close()
        serialized = {}
        expected_ordinal = {}
        for section, group, ordinal, row_json in rows:
            key = (str(section), str(group))
            ordinal = int(ordinal)
            if ordinal != expected_ordinal.get(key, 0):
                raise ValueError(f"Database projection order is discontinuous for {key!r}.")
            expected_ordinal[key] = ordinal + 1
            serialized.setdefault(key, []).append(json.loads(row_json))
        expected = {
            **{
                ("NODE", name): list(rows)
                for name, rows in self.node_groups.items()
            },
            ("RESULT_RELATIONSHIP", "result_relationships"):
                list(self.result_relationships),
            ("CLASSIFICATION_ASSIGNMENT", "classification_assignments"):
                list(self.classification_assignments),
            ("ANATOMY_TRAVERSAL", "anatomy_evidence_traversals"):
                list(self.anatomy_evidence_traversals),
            ("RESULT_RELATIONSHIP", "source_anatomy_contexts"):
                list(self.source_anatomy_contexts),
            ("WEIGHTED_AXIS_SUMMARY", "weighted_axis_summaries"):
                list(self.weighted_axis_summaries),
        }
        if serialized != expected:
            missing = sorted(set(expected) - set(serialized))
            extra = sorted(set(serialized) - set(expected))
            changed = sorted(
                key for key in set(expected) & set(serialized)
                if expected[key] != serialized[key]
            )
            raise ValueError(
                "Public graph differs from the database-owned serialized projection: "
                f"missing={missing} extra={extra} changed={changed}."
            )
        return sum(len(rows) for rows in expected.values())
