import pytest

from app import db
from models import Notification, Rating


def rate(client, user="friend", score=5):
    return client.post("/songs/song/rate", json={"user_id": user, "score": score})


def test_saved_rating_notifies_song_owner(client):
    response = rate(client)
    assert response.status_code == 201
    db.session.remove()
    rating = db.session.get(Rating, response.get_json()["id"])
    assert (rating.user_id, rating.song_id, rating.score) == ("friend", "song", 5)
    data = client.get("/users/owner/notifications").get_json()
    assert data["count"] == 1
    notification = data["notifications"][0]
    assert notification["type"] == "song_rated"
    assert notification["user_id"] == "owner" and notification["read"] is False
    assert "friend" in notification["body"] and "Crown Heights Anthem" in notification["body"]
    assert "5" in notification["body"]
    assert client.get("/users/friend/notifications").get_json()["count"] == 0


def test_rerating_updates_one_row_without_duplicate_notifications(client):
    first = rate(client).get_json()
    assert rate(client).get_json()["id"] == first["id"]
    changed = rate(client, score=3).get_json()
    assert changed["id"] == first["id"] and changed["score"] == 3
    assert db.session.query(Rating).count() == 1
    assert db.session.query(Notification).count() == 1
    assert rate(client, user="other").status_code == 201
    assert db.session.query(Notification).filter_by(user_id="owner").count() == 2


def test_own_rating_and_invalid_input_do_not_notify(client):
    assert rate(client, user="owner").status_code == 201
    for score in [0, 6]:
        assert rate(client, score=score).status_code == 400
    assert rate(client, user="missing").status_code == 400
    assert client.post("/songs/missing/rate", json={"user_id": "friend", "score": 5}).status_code == 400
    assert db.session.query(Notification).count() == 0
    assert db.session.query(Rating).count() == 1


def test_existing_playlist_notification_preserved_and_readable(client):
    # Exercise a real new-entry POST now that its required fields are supplied.
    response = client.post("/playlists/playlist/songs", json={"song_id": "second", "added_by": "friend"})
    assert response.status_code == 201
    assert rate(client).status_code == 201
    data = client.get("/users/owner/notifications").get_json()
    assert {n["type"] for n in data["notifications"]} == {"song_added_to_playlist", "song_rated"}
    notification_id = next(n["id"] for n in data["notifications"] if n["type"] == "song_rated")
    assert client.post(f"/users/notifications/{notification_id}/read").status_code == 200
    unread = client.get("/users/owner/notifications?unread_only=true").get_json()
    assert unread["count"] == 1 and unread["notifications"][0]["type"] == "song_added_to_playlist"


def test_notification_and_rating_roll_back_together(client, monkeypatch):
    def reject_commit():
        raise RuntimeError("simulated commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(db.session, "commit", reject_commit)
        with pytest.raises(RuntimeError, match="simulated commit failure"):
            rate(client)
    db.session.rollback()
    assert db.session.query(Rating).count() == 0
    assert db.session.query(Notification).count() == 0
