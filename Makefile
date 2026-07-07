.PHONY: all build validate serve intake clean check-sync help

help:
	@echo "targets:"
	@echo "  make validate   - schema + integrity checks on the dataset (CI gate)"
	@echo "  make build      - validate, rebuild enrichment.json, render the HTML -> docs/"
	@echo "  make check-sync - verify committed enrichment.json matches build_enrichment.py"
	@echo "  make serve      - build then serve docs/ at http://localhost:8000"
	@echo "  make intake PDF=path/to/paper.pdf - screen & queue a new paper for integration"
	@echo "  make clean      - remove generated HTML"

validate:
	python3 tools/validate_data.py

build: validate
	python3 enrichment/build_enrichment.py
	python3 generator/gen_study.py
	@echo "Built docs/seizure_semiology_localization.html"

check-sync:
	python3 enrichment/build_enrichment.py
	git diff --exit-code enrichment/enrichment.json \
	  || (echo "ERROR: enrichment.json is out of sync with build_enrichment.py. Run 'make build' and commit." && exit 1)

serve: build
	cd docs && python3 -m http.server 8000

intake:
	@test -n "$(PDF)" || (echo "usage: make intake PDF=path/to/paper.pdf" && exit 1)
	python3 tools/intake_paper.py "$(PDF)"

clean:
	rm -f docs/*.html
