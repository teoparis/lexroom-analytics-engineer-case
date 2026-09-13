DBT := .venv/bin/dbt
PYTHON := .venv/bin/python

.PHONY: setup seed build test docs profile validate check-receipts audit dashboard clean

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

seed:
	$(DBT) seed --profiles-dir .

build:
	$(DBT) build --profiles-dir .

test:
	$(DBT) test --profiles-dir .

docs:
	$(DBT) docs generate --profiles-dir .

profile:
	$(PYTHON) scripts/profile_data.py

validate:
	$(PYTHON) scripts/validate_metrics.py

check-receipts:
	git diff --exit-code -- docs/data_profile.json docs/metric_validation.json

audit: profile build validate docs check-receipts

dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py

clean:
	$(DBT) clean --profiles-dir .
