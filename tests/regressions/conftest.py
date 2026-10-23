from datetime import datetime, timezone

import pytest

from app import create_app, db
from models import Playlist, Song, User


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        owner = User(id="owner", username="owner", email="owner@example.test")
        friend = User(id="friend", username="friend", email="friend@example.test")
        other = User(id="other", username="other", email="other@example.test")
        owner.friends.append(friend)
        friend.friends.append(owner)
        db.session.add_all([owner, friend, other])
        db.session.flush()
        db.session.add_all([
            Song(id="song", title="Crown Heights Anthem", artist="Borough Kings",
                 shared_by="owner"),
            Song(id="second", title="Midnight Drive", artist="The Wanderers",
                 shared_by="owner"),
            Playlist(id="playlist", name="Friday Energy", created_by="friend"),
        ])
        db.session.commit()
        yield app.test_client()
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def freeze_clock(monkeypatch):
    def freeze(module, instant):
        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)

        monkeypatch.setattr(module, "datetime", FrozenDateTime)

    return freeze
