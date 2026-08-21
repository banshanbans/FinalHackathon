PYTHON ?= python3.12
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
NPM_CACHE := $(CURDIR)/.cache/npm
COMPOSE_ENV ?= $(CURDIR)/.env.example

.PHONY: setup setup-backend setup-web setup-presentation setup-roadshow dev dev-api start-api dev-web dev-presentation test test-sim test-api test-e2e test-e2e-presentation capture-v3 capture-readme lint validate-data build repository-check check docker-config docker-build precompute precompute-v32 precompute-v32-luna precompute-m34 precompute-m34-luna showcase-m35 verify-cache verify-cache-v32 verify-cache-v32-luna verify-cache-m34 verify-cache-m34-luna demo smoke spike-agentsociety clean

setup: setup-backend setup-web setup-presentation setup-roadshow

setup-backend:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e '.[dev]'
	-chflags nohidden $(VENV)/lib/python*/site-packages/*.pth

setup-web:
	npm --prefix apps/web ci --cache $(NPM_CACHE)

setup-presentation:
	npm --prefix apps/presentation ci --cache $(NPM_CACHE)

setup-roadshow:
	npm --prefix apps/roadshow ci --cache $(NPM_CACHE)

dev:
	@echo "Run 'make dev-api' with 'make dev-presentation' in separate terminals."

dev-api:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" POLICYSCOPE_RUN_MODE=fake $(PY) -m uvicorn policyscope_api.main:app --app-dir apps/api/src --reload --port 8000

start-api:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" POLICYSCOPE_RUN_MODE=cache POLICYSCOPE_CACHE_MISS_MODE=live $(PY) -m uvicorn policyscope_api.main:app --app-dir apps/api/src --host 0.0.0.0 --port 8000

dev-web:
	npm --prefix apps/web run dev

dev-presentation:
	npm --prefix apps/presentation run dev -- --host 127.0.0.1 --port 4180

test:
	$(PY) -m pytest
	npm --prefix apps/web run test
	npm --prefix apps/presentation run test:geometry
	npm --prefix apps/roadshow run test
	npm --prefix apps/roadshow run test:sites

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

capture-readme:
	npm --prefix apps/web run test:e2e:capture-readme

lint:
	$(VENV)/bin/ruff check simulation apps/api scripts
	$(VENV)/bin/ruff format --check simulation apps/api scripts
	npm --prefix apps/web run lint
	npm --prefix apps/presentation run typecheck
	npm --prefix apps/roadshow run typecheck
	npm --prefix apps/roadshow run check:boundaries

validate-data:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/validate_data.py
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/validate_standard_map.py
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/validate_presentation_map.py

build:
	npm --prefix apps/web run build
	npm --prefix apps/presentation run build
	npm --prefix apps/roadshow run build

repository-check:
	$(PY) scripts/check_repository.py

check: repository-check lint validate-data test build

docker-config:
	POLICYSCOPE_ENV_FILE="$(COMPOSE_ENV)" docker compose -f deploy/m35/compose.production.yml config --quiet

docker-build: docker-config
	docker build -f deploy/m35/Dockerfile.api -t 13110-api:local .
	docker build -f deploy/m35/Dockerfile.web -t 13110-presentation:local .

precompute:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/precompute_demo.py

precompute-v32:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/precompute_v32_demo.py

precompute-v32-luna:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" POLICYSCOPE_RUN_MODE=live $(PY) scripts/precompute_v32_demo.py --luna

precompute-m34:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/precompute_m34_demo.py

precompute-m34-luna:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" POLICYSCOPE_RUN_MODE=live $(PY) scripts/precompute_m34_demo.py --luna

showcase-m35:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/build_m35_showcase.py

verify-cache:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/verify_v31_cache.py

verify-cache-v32:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/verify_v32_cache.py

verify-cache-v32-luna:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/verify_v32_cache.py --luna

verify-cache-m34:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/verify_m34_cache.py

verify-cache-m34-luna:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/verify_m34_cache.py --luna

demo:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" POLICYSCOPE_RUN_MODE=cache $(PY) scripts/smoke_demo.py

smoke:
	PYTHONPATH="$(CURDIR):$(CURDIR)/apps/api/src" $(PY) scripts/smoke_demo.py --assert-complete

spike-agentsociety:
	AGENTSOCIETY_LLM_API_KEY=spike-only $(PY) scripts/spike_agentsociety2.py

clean:
	@echo "Remove generated caches manually if needed; this target is intentionally non-destructive."
