#!/usr/bin/env python3
"""
check_provenance.py — the page-provenance gate for intake findings.

Every finding in enrichment/intake_findings.json must carry a source PAGE
reference and map to a real sign, so nothing is integrated without a citable
page. Runs in CI on every PR.

Exit non-zero (failing the build) if any entry is malformed or unprovenanced.
Passes trivially when there are no intake findings.
"""
import json
import os
import re
import sys

PAGE_RE = re.compile(r"^(pp?\.?\s?)?\d+(\s?[-–,]\s?\d+)*$", re.IGNORECASE)


def _find_root(start):
    d = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.exists(os.path.join(d, ".atlas-root")):
            return d
        p = os.path.dirname(d)
        if p == d:
            return os.path.dirname(os.path.abspath(start))
        d = p


def main():
    root = _find_root(__file__)
    path = os.path.join(root, "enrichment", "intake_findings.json")
    if not os.path.exists(path):
        print("no intake_findings.json — nothing to check")
        return

    data = json.load(open(path))
    signs = json.load(open(os.path.join(root, "data", "semiology_data.json")))
    # A finding may attach to an existing curated sign OR to a new sign proposed in
    # this same intake (a paper introducing a sign not yet in the atlas).
    names = [s["sign"].lower() for s in signs]
    names += [ns.get("sign", "").lower() for ns in data.get("new_signs", []) if ns.get("sign")]
    errors = []

    # Proposed new signs must be complete enough to render and stay attributable.
    for i, ns in enumerate(data.get("new_signs", [])):
        for req in ("region", "sub", "sign", "phase", "lat", "latcode", "loc", "evid", "notes", "cite"):
            if not ns.get(req):
                errors.append(f"new_signs[{i}]: missing or empty '{req}'")

    for i, f in enumerate(data.get("findings", [])):
        where = f"findings[{i}]"
        for req in ("sign_stem", "paper", "finding", "pg"):
            if not f.get(req):
                errors.append(f"{where}: missing or empty '{req}'")
        pg = str(f.get("pg", "")).strip()
        if pg and not PAGE_RE.match(pg):
            errors.append(f"{where}: page reference '{pg}' is not a recognizable page or range")
        stem = (f.get("sign_stem") or "").lower()
        if stem and not any(stem in n for n in names):
            errors.append(f"{where}: sign_stem '{f.get('sign_stem')}' matches no existing sign name")

    for i, p in enumerate(data.get("papers", [])):
        for req in ("cite", "journal", "title"):
            if not p.get(req):
                errors.append(f"papers[{i}]: missing or empty '{req}'")

    if errors:
        print("::error::intake provenance check failed:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    n = len(data.get("findings", []))
    print(f"provenance OK — {n} intake finding(s), all page-cited")


if __name__ == "__main__":
    main()
