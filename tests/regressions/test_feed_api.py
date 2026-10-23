from datetime import datetime, timezone

from app import db
from models import ListeningEvent, User
from services import feed_service


def test_listening_now_excludes_previous_evening(client, freeze_clock):
    freeze_clock(feed_service, datetime(2024, 6, 16, 9, tzinfo=timezone.utc))
    db.session.add(ListeningEvent(user_id="friend", song_id="song",
                                 listened_at=datetime(2024, 6, 15, 23)))
    db.session.commit()
    response = client.get("/feed/owner/listening-now")
    assert response.status_code == 200
    assert response.get_json() == {"feed": [], "count": 0}
    assert client.get("/feed/owner/activity").get_json()["count"] == 1


def test_feed_midnight_bounds_latest_friend_and_order(client, freeze_clock):
    freeze_clock(feed_service, datetime(2024, 6, 16, 9, tzinfo=timezone.utc))
    midnight_friend = User(id="midnight", username="midnight", email="midnight@example.test")
    tomorrow_friend = User(id="tomorrow", username="tomorrow", email="tomorrow@example.test")
    owner = db.session.get(User, "owner")
    owner.friends.extend([midnight_friend, tomorrow_friend])
    db.session.add_all([midnight_friend, tomorrow_friend])
    db.session.flush()
    for user_id, song_id, time in [
        ("friend", "song", "2024-06-15T23:59:59.999999"),
        ("friend", "song", "2024-06-16T00:00:00"),
        ("friend", "second", "2024-06-16T08:00:00"),
        ("midnight", "song", "2024-06-16T00:00:00"),
        ("tomorrow", "song", "2024-06-17T00:00:00"),
        ("other", "song", "2024-06-16T08:30:00"),
        ("owner", "song", "2024-06-16T08:45:00"),
    ]:
        db.session.add(ListeningEvent(user_id=user_id, song_id=song_id,
                                     listened_at=datetime.fromisoformat(time)))
    db.session.commit()
    data = client.get("/feed/owner/listening-now").get_json()
    assert data["count"] == 2
    assert [entry["friend"]["id"] for entry in data["feed"]] == ["friend", "midnight"]
    assert data["feed"][0]["song"]["id"] == "second"
    assert data["feed"][1]["listened_at"] == "2024-06-16T00:00:00"
    assert client.get("/feed/other/listening-now").get_json() == {"feed": [], "count": 0}
    assert client.get("/feed/missing/listening-now").status_code == 404
