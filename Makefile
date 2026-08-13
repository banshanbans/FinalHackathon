PYTHON := /opt/homebrew/bin/python3.12
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
NPM_CACHE := $(CURDIR)/.cache/npm

.PHONY: setup setup-backend setup-web setup-presentation dev dev-api start-api dev-web dev-presentation test test-sim test-api test-e2e test-e2e-presentation capture-v3 lint validate-data precompute precompute-v32 precompute-v32-luna verify-cache verify-cache-v32 verify-cache-v32-luna demo smoke spike-agentsociety clean

setup: setup-backend setup-web setup-presentation

setup-backend:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e '.[dev]'
	-chflags nohidden $(VENV)/lib/python*/site-packages/*.pth

setup-web:
	npm --prefix apps/web install --cache $(NPM_CACHE)

setup-presentation:
	npm --prefix apps/presentation install --cache $(NPM_CACHE)

dev:
	@echo "Run 'make dev-api' with 'make dev-web' or 'make dev-presentation' in separate terminals."

dev-api:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" POLICYSCOPE_RUN_MODE=fake $(VENV)/bin/uvicorn policyscope_api.main:app --app-dir apps/api/src --reload --port 8000

start-api:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" POLICYSCOPE_RUN_MODE=live $(VENV)/bin/uvicorn policyscope_api.main:app --app-dir apps/api/src --host 0.0.0.0 --port 8000

dev-web:
	npm --prefix apps/web run dev

dev-presentation:
	npm --prefix apps/presentation run dev -- --host 127.0.0.1 --port 4180

test:
	$(PY) -m pytest
	npm --prefix apps/web run test

test-sim:
	$(PY) -m pytest simulation/tests

test-api:
	$(PY) -m pytest apps/api/tests

test-e2e:
	npm --prefix apps/web run test:e2e

test-e2e-presentation:
	npm --prefix apps/web run test:e2e:presentation

capture-v3:
	npm --prefix apps/web run test:e2e:capture

lint:
	$(VENV)/bin/ruff check simulation apps/api scripts
	$(VENV)/bin/ruff format --check simulation apps/api scripts
	npm --prefix apps/web run lint
	npm --prefix apps/web run build
	npm --prefix apps/presentation run build

validate-data:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/validate_data.py
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/validate_standard_map.py
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/validate_presentation_map.py

precompute:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/precompute_demo.py

precompute-v32:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/precompute_v32_demo.py

precompute-v32-luna:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" POLICYSCOPE_RUN_MODE=live $(PY) scripts/precompute_v32_demo.py --luna

verify-cache:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/verify_v31_cache.py

verify-cache-v32:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/verify_v32_cache.py

verify-cache-v32-luna:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/verify_v32_cache.py --luna

demo:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" POLICYSCOPE_RUN_MODE=cache $(PY) scripts/smoke_demo.py

smoke:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/smoke_demo.py --assert-complete

spike-agentsociety:
	AGENTSOCIETY_LLM_API_KEY=spike-only $(PY) scripts/spike_agentsociety2.py

clean:
	@echo "Remove generated caches manually if needed; this target is intentionally non-destructive."
