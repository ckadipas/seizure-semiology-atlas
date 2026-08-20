.PHONY: build validate serve check-sync help

help:
	@echo "targets:"
	@echo "  make validate   - validate the generated/redacted canonical atlas bundle"
	@echo "  make build      - validate the bundle and render HTML into docs/"
	@echo "  make check-sync - verify committed HTML matches the committed bundle"
	@echo "  make serve      - build, then serve docs/ at http://localhost:8000"

validate:
	python3 tools/validate_atlas_bundle.py

build: validate
	python3 generator/gen_study.py

check-sync: build
	git diff --exit-code docs/seizure_semiology_localization.html docs/index.html

serve: build
	cd docs && python3 -m http.server 8000
