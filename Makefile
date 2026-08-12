PYTHON := /opt/homebrew/bin/python3.12
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
NPM_CACHE := $(CURDIR)/.cache/npm

.PHONY: setup setup-backend setup-web dev dev-api dev-web test test-sim test-api test-e2e capture-v3 lint validate-data precompute demo smoke spike-agentsociety clean

setup: setup-backend setup-web

setup-backend:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e '.[dev]'
	-chflags nohidden $(VENV)/lib/python*/site-packages/*.pth

setup-web:
	npm --prefix apps/web install --cache $(NPM_CACHE)

dev:
	@echo "Run 'make dev-api' and 'make dev-web' in separate terminals."

dev-api:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(VENV)/bin/uvicorn policyscope_api.main:app --app-dir apps/api/src --reload --port 8000

dev-web:
	npm --prefix apps/web run dev

test:
	$(PY) -m pytest
	npm --prefix apps/web run test

test-sim:
	$(PY) -m pytest simulation/tests

test-api:
	$(PY) -m pytest apps/api/tests

test-e2e:
	npm --prefix apps/web run test:e2e

capture-v3:
	npm --prefix apps/web run test:e2e:capture

lint:
	$(VENV)/bin/ruff check simulation apps/api scripts
	$(VENV)/bin/ruff format --check simulation apps/api scripts
	npm --prefix apps/web run lint
	npm --prefix apps/web run build

validate-data:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/validate_data.py
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/validate_standard_map.py

precompute:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/precompute_demo.py

demo:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" POLICYSCOPE_RUN_MODE=cache $(PY) scripts/smoke_demo.py

smoke:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/smoke_demo.py --assert-complete

spike-agentsociety:
	AGENTSOCIETY_LLM_API_KEY=spike-only $(PY) scripts/spike_agentsociety2.py

clean:
	@echo "Remove generated caches manually if needed; this target is intentionally non-destructive."
