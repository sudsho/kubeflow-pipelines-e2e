PY := python
PIP := pip

.PHONY: setup lint test compile

setup:
	$(PIP) install -r requirements.txt

lint:
	$(PY) -m compileall -q pipelines src

test:
	pytest -q

compile:
	$(PY) pipelines/compile.py
