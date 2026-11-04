PY ?= python
EVAL_THRESHOLD ?= 0.8

.PHONY: install test lint evals evals-live evals-record

install:
	$(PY) -m pip install -r requirements-dev.txt

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests scripts

# Offline: replays recorded model/embedding responses from evals/cassette.json. This is what CI runs.
evals:
	@test -f evals/cassette.json || { echo "no evals/cassette.json yet: run make evals-record with real API keys first"; exit 1; }
	$(PY) -m src.evals --mode replay --threshold $(EVAL_THRESHOLD) --report evals/report.json

# Live: real Anthropic + Voyage calls. evals-record also rewrites the cassette.
evals-live:
	$(PY) -m src.evals --mode live --report evals/report.json

evals-record:
	$(PY) -m src.evals --mode record --report evals/report.json --badge evals/badge.json
