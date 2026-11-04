PY ?= python

.PHONY: install test lint evals evals-record

install:
	$(PY) -m pip install -r requirements-dev.txt

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests scripts
