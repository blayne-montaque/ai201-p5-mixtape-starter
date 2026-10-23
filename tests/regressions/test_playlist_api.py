import pytest
from sqlalchemy import select

from app import db
from models import Song, playlist_entries


def seed_entries(count):
    for index in range(count):
        song_id = f"track-{index + 1}"
        db.session.add(Song(id=song_id, title=f"Track {index + 1}", artist="Various", shared_by="owner"))
        db.session.flush()
        db.session.execute(playlist_entries.insert().values(
            playlist_id="playlist", song_id=song_id,
            position=index * 2 + 1, added_by="friend"))
    db.session.commit()


@pytest.mark.parametrize("count", [0, 1, 7])
def test_playlist_includes_all_positions(client, count):
    seed_entries(count)
    response = client.get("/playlists/playlist/songs")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == count
    assert [song["id"] for song in data["songs"]] == [f"track-{i + 1}" for i in range(count)]
    assert client.get("/playlists/missing/songs").status_code == 404


@pytest.mark.parametrize("count", [0, 7])
def test_added_song_is_persisted_last_once_and_notifies(client, count):
    seed_entries(count)
    for _ in range(2):
        response = client.post("/playlists/playlist/songs", json={"song_id": "song", "added_by": "friend"})
        assert response.status_code == 201
    db.session.remove()
    data = client.get("/playlists/playlist/songs").get_json()
    assert data["count"] == count + 1
    assert [s["id"] for s in data["songs"]] == [f"track-{i + 1}" for i in range(count)] + ["song"]
    entry = db.session.execute(select(playlist_entries).where(playlist_entries.c.song_id == "song")).one()
    assert entry.position == (count * 2 if count else 1)
    assert entry.added_by == "friend" and entry.added_at is not None
    notifications = client.get("/users/owner/notifications").get_json()
    assert notifications["count"] == 1
    assert notifications["notifications"][0]["type"] == "song_added_to_playlist"
