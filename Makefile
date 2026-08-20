.PHONY: all build validate serve intake clean check-sync review help

help:
	@echo "targets:"
	@echo "  make validate   - schema + integrity checks on dataset and Brodmann map (CI gate)"
	@echo "  make build      - validate/index the owner-reviewed V30 ledger and render HTML -> docs/"
	@echo "  make review     - rerun the deterministic V30 ledger integrity check"
	@echo "  make check-sync - verify committed generated JSON matches its sources"
	@echo "  make serve      - build then serve docs/ at http://localhost:8000"
	@echo "  make intake PDF=path/to/paper.pdf - screen & queue a new paper for integration"
	@echo "  make clean      - remove generated HTML"

validate:
	python3 tools/validate_data.py

build: validate
	python3 tools/build_v30_evidence_index.py
	python3 tools/adversarial_review.py --strict
	python3 generator/gen_study.py
	python3 tools/test_v30_evidence_contract.py
	@echo "Built docs/seizure_semiology_localization.html"

review:
	python3 tools/build_v30_evidence_index.py
	python3 tools/adversarial_review.py --strict

check-sync:
	python3 tools/build_v30_evidence_index.py
	python3 tools/adversarial_review.py --strict
	git diff --exit-code enrichment/enrichment.json enrichment/evidence_index.json enrichment/meta_analysis.json enrichment/review_flags.json \
	  || (echo "ERROR: generated data is out of sync with its sources. Run 'make build' and commit." && exit 1)

serve: build
	cd docs && python3 -m http.server 8000

intake:
	@test -n "$(PDF)" || (echo "usage: make intake PDF=path/to/paper.pdf" && exit 1)
	python3 tools/intake_paper.py "$(PDF)"

clean:
	rm -f docs/*.html
