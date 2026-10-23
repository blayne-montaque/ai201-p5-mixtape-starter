from datetime import datetime, timezone

import pytest

from app import db
from models import ListeningEvent, User
from services import streak_service


@pytest.mark.parametrize("previous,current,expected", [
    ("2024-06-15T23:59:59", "2024-06-16T00:00:00", 13),
    ("2024-06-16T23:59:59", "2024-06-17T00:00:00", 13),
    ("2024-06-16T01:00:00", "2024-06-16T09:00:00", 12),
    ("2024-06-14T09:00:00", "2024-06-16T09:00:00", 1),
    ("2024-12-31T23:59:59", "2025-01-01T00:00:00", 13),
])
def test_calendar_streak_persists_through_listen_endpoint(
        client, freeze_clock, previous, current, expected):
    user = db.session.get(User, "friend")
    user.last_listened_at = datetime.fromisoformat(previous)
    user.listening_streak = 12
    db.session.commit()
    now = datetime.fromisoformat(current).replace(tzinfo=timezone.utc)
    freeze_clock(streak_service, now)

    response = client.post("/songs/song/listen", json={"user_id": "friend"})
    assert response.status_code == 201
    db.session.remove()  # Read back persisted state, not just the identity map.
    assert client.get("/users/friend/streak").get_json() == {
        "user_id": "friend", "streak": expected,
    }
    event = db.session.get(ListeningEvent, response.get_json()["id"])
    assert event.user_id == "friend" and event.song_id == "song"
    assert event.listened_at == now.replace(tzinfo=None)
