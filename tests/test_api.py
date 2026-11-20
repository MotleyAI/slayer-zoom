import json

from fastapi.testclient import TestClient

from slayer_zoom.api import create_app
from slayer_zoom.traces import QUESTION


def _events(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_health() -> None:
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}


def test_ladder_schema_names_the_levels() -> None:
    schema = TestClient(create_app()).get("/schema/ladder").json()
    assert schema["title"] == "Ladder"
    assert "levels" in schema["properties"]


def test_answer_streams_every_level_from_the_trace() -> None:
    response = TestClient(create_app()).post("/answer", json={"question": "what is our revenue year to date"})
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _events(response.text)
    kinds = [kind for kind, _ in events]
    assert kinds == ["ladder", "level", "level", "level", "level", "level", "done"]
    levels = [data for kind, data in events if kind == "level"]
    assert [level["index"] for level in levels] == [0, 1, 2, 3, 4]
    assert levels[0]["panels"][0]["data"]["rows"][0]["orders.revenue"] > 0


def test_other_questions_get_a_pointer_to_the_demo_question() -> None:
    events = _events(TestClient(create_app()).post("/answer", json={"question": "How many stores?"}).text)
    assert events[0][0] == "error"
    assert QUESTION in events[0][1]["message"]
