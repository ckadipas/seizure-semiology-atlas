.PHONY: all build validate serve intake clean check-sync review help

help:
	@echo "targets:"
	@echo "  make validate   - schema + integrity checks on the dataset (CI gate)"
	@echo "  make build      - validate, rebuild enrichment + meta-analysis + review, render HTML -> docs/"
	@echo "  make review     - rerun the weighted meta-analysis + adversarial review only"
	@echo "  make check-sync - verify committed generated JSON matches its sources"
	@echo "  make serve      - build then serve docs/ at http://localhost:8000"
	@echo "  make intake PDF=path/to/paper.pdf - screen & queue a new paper for integration"
	@echo "  make clean      - remove generated HTML"

validate:
	python3 tools/validate_data.py

build: validate
	python3 enrichment/build_enrichment.py
	python3 tools/meta_analysis.py
	python3 tools/adversarial_review.py
	python3 generator/gen_study.py
	@echo "Built docs/seizure_semiology_localization.html"

review:
	python3 enrichment/build_enrichment.py
	python3 tools/meta_analysis.py
	python3 tools/adversarial_review.py

check-sync:
	python3 enrichment/build_enrichment.py
	python3 tools/meta_analysis.py
	python3 tools/adversarial_review.py
	git diff --exit-code enrichment/enrichment.json enrichment/meta_analysis.json enrichment/review_flags.json \
	  || (echo "ERROR: generated data is out of sync with its sources. Run 'make build' and commit." && exit 1)

serve: build
	cd docs && python3 -m http.server 8000

intake:
	@test -n "$(PDF)" || (echo "usage: make intake PDF=path/to/paper.pdf" && exit 1)
	python3 tools/intake_paper.py "$(PDF)"

clean:
	rm -f docs/*.html
