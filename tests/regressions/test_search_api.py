import pytest

from app import db
from models import Song, Tag


@pytest.mark.parametrize("tag_count", [0, 1, 3])
def test_search_unique_with_complete_tags(client, tag_count):
    song = db.session.get(Song, "song")
    song.tags = [Tag(name=f"tag-{index}") for index in range(tag_count)]
    db.session.commit()
    for query in ["Anthem", "bOrOuGh"]:
        response = client.get("/songs/search", query_string={"q": query})
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
        assert data["results"][0]["id"] == "song"
        assert set(data["results"][0]["tags"]) == {f"tag-{i}" for i in range(tag_count)}


def test_search_preserves_distinct_song_ids_and_errors(client):
    db.session.add(Song(id="same-title", title="Crown Heights Anthem",
                        artist="Borough Kings", shared_by="friend"))
    db.session.commit()
    data = client.get("/songs/search?q=Anthem").get_json()
    assert data["count"] == 2
    assert {song["id"] for song in data["results"]} == {"song", "same-title"}
    assert client.get("/songs/search?q=not-found").get_json() == {"results": [], "count": 0}
    assert client.get("/songs/search").status_code == 400
