PY := python
PIP := pip
IMG := demand-forecast:local

.PHONY: setup lint test compile submit docker docker-run clean

setup:
	$(PIP) install -r requirements.txt

lint:
	$(PY) -m compileall -q pipelines src

test:
	pytest -q

compile:
	mkdir -p dist
	$(PY) pipelines/compile.py --out dist/demand_forecast.json

submit: compile
	$(PY) pipelines/submit.py --project $$GCP_PROJECT --package dist/demand_forecast.json

docker:
	docker build -t $(IMG) .

docker-run: docker
	docker run --rm -p 8080:8080 -v $$(pwd)/local-models:/models:ro $(IMG)

clean:
	rm -rf dist mlruns __pycache__ .pytest_cache
