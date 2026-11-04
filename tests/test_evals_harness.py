"""The eval harness's own logic: cassette replay, grading, and the CI threshold."""
import json

import pytest

from src import evals


def test_cassette_replays_recorded_responses_in_order(tmp_path):
    path = tmp_path / "cassette.json"
    recorder = evals.Cassette(path, "record")
    answers = iter(["first", "second"])
    for _ in range(2):
        recorder.through("messages", {"q": 1}, lambda: next(answers), dump=str, load=str)
    recorder.save()

    replay = evals.Cassette(path, "replay")
    assert [replay.through("messages", {"q": 1}, None, dump=str, load=str) for _ in range(2)] == ["first", "second"]


def test_cassette_miss_is_an_error_not_a_guess(tmp_path):
    path = tmp_path / "cassette.json"
    path.write_text(json.dumps({}))
    replay = evals.Cassette(path, "replay")
    with pytest.raises(evals.CassetteMiss):
        replay.through("messages", {"prompt": "changed"}, None, dump=str, load=str)
    assert len(replay.misses) == 1


def test_code_grader_needs_every_expected_string():
    assert evals.code_grade("Orders NW-10024 and NW-10043", ["NW-10024", "nw-10043"])
    assert not evals.code_grade("Order NW-10043", ["NW-10024", "NW-10043"])


def test_threshold_sets_exit_code(monkeypatch):
    rows = [{"id": f"c{i}", "category": "kb", "grader": "code", "input": "", "expected": [], "passed": i < 3,
             "latency_ms": 100 * i, "reply": "", "route": "KB", "verify_attempts": 1, "escalated": False, "tools": []}
            for i in range(4)]

    async def fake_run_cases(cases):
        return rows

    monkeypatch.setattr(evals, "run_cases", fake_run_cases)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert evals.main(["--threshold", "0.75"]) == 0
    assert evals.main(["--threshold", "0.8"]) == 1
