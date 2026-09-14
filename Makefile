.PHONY: build validate serve check-sync check-deployment help

help:
	@echo "targets:"
	@echo "  make validate   - validate the committed normalized release"
	@echo "  make build      - validate the website and data for local use or deployment"
	@echo "  make check-sync - validate the release and confirm website files are unchanged"
	@echo "  make serve      - build, then serve docs/ at http://localhost:8000"

validate:
	python3 tools/test_public_governance.py
	python3 tools/validate_normalized_atlas_release.py

build: validate

check-sync: build
	git diff --exit-code -- docs

check-deployment: check-sync

serve: build
	cd docs && python3 -m http.server 8000
