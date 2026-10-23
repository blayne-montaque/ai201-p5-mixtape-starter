# AI Usage

Codex read the project README before application source, inspected the models,
application factory, routes, starter tests, seed script, and service interfaces,
and traced playlist creation end to end. The service survey used function
signatures and docstrings; `create_playlist()` was read in full to verify the
architectural call chain below. This initial document is an orientation checkpoint
written before reproductions or investigation of the reported service behavior.
No human code review is claimed. No LLM API calls or private credentials were used.

# Codebase Map

Mixtape is a Flask JSON API for sharing songs, rating them, building collaborative
playlists, following friends' listening activity, and tracking listening streaks.
Its layers are HTTP blueprints, domain services, and SQLAlchemy persistence.

## Application and persistence

- `app.py` defines the shared `db = SQLAlchemy()` extension and
  `create_app(config=None)`. The factory configures the database, accepts config
  overrides, initializes the extension, registers four blueprints, and creates
  tables inside an application context. The default database is SQLite at
  `instance/mixtape.db`; `DATABASE_URL` can select another database.
- `models.py` imports the shared extension. UUID strings identify records.
  `User` stores profile and streak state; `Song` stores song metadata and its
  sharer; `Tag` labels songs; `ListeningEvent` links a user, song, and timestamp;
  `Rating` stores a score with a unique user/song pair; `Playlist` stores creator
  and collaboration metadata; `Notification` stores recipient, type, body, and
  read status. Entity `to_dict()` methods build JSON-compatible dictionaries.
- `friendships` links users to friends (the seed inserts both directions).
  `song_tags` links songs and tags. `playlist_entries` links playlists and songs
  with position, contributor, and addition time. User relationships expose songs,
  ratings, listening events, notifications, playlists, and friends. Song
  relationships expose ratings, listening events, and tags.
- Timestamp defaults use UTC. SQLAlchemy `DateTime` columns store timestamps;
  API serializers use ISO strings. SQLite persistence and explicit application
  contexts also support isolated in-memory test databases.

## HTTP and service responsibilities

| Routes | Services and responsibilities |
| --- | --- |
| `routes/songs.py`: `search`, `get_song_detail`, `rate`, `listen` | `search_service.search_songs()` and `get_song()` retrieve song data; `notification_service.rate_song()` saves scores; `streak_service.record_listening_event()` records listens and calls `update_listening_streak()`. |
| `routes/playlists.py`: `create`, `get_detail`, `get_songs`, `add_song` | `playlist_service.create_playlist()`, `get_playlist()`, and `get_playlist_songs()` manage playlist metadata and retrieval; `notification_service.add_to_playlist()` handles addition and related notification work. `get_user_playlists()` provides creator-based retrieval. |
| `routes/users.py`: `get_user`, `streak`, `notifications`, `read_notification` | Profile lookup uses `db.session.get(User, ...)`; `streak_service.get_streak()` supplies streak data; `notification_service.get_notifications()` and `mark_as_read()` handle notification retrieval and read state. |
| `routes/feed.py`: `listening_now`, `activity` | `feed_service.get_friends_listening_now()` supplies listening activity; `get_activity_feed()` supplies recent friend events with a result limit. |

Routes extract request parameters and JSON fields, invoke services, serialize
results with `jsonify`, and translate service `ValueError`s into HTTP error
responses. `notification_service.create_notification()` is a shared notification
creation interface. Services use the shared database session and model relations.

## End-to-end feature: create a playlist

1. A client sends `POST /playlists/` with JSON containing `name`, `created_by`,
   and optionally `is_collaborative`.
2. The factory's `/playlists` blueprint registration dispatches the request to
   `routes/playlists.py:create()`. It validates required fields and invokes
   `services/playlist_service.py:create_playlist()`.
3. The service looks up the creator with `db.session.get(User, created_by_user_id)`.
   It constructs a `Playlist`, calls `db.session.add()` and `db.session.commit()`,
   and returns the persisted model. SQLAlchemy writes its fields to SQLite.
4. The route calls `Playlist.to_dict()` and returns JSON with HTTP 201. A missing
   creator raises `ValueError`, which the route returns as an HTTP 400 error.

## Setup and verification assets

`requirements.txt` declares Flask, Flask-SQLAlchemy, SQLAlchemy, python-dotenv,
and pytest. `.gitignore` excludes virtual environments, `.env`, SQLite databases,
the instance directory, bytecode, and editor files. `seed_data.py:seed()` rebuilds
the selected database and inserts users, friendships, tags, songs, events,
playlists, and notifications. Its executable data creates 5 users, 13 songs,
3 playlists, and 10 tags. `tests/test_streaks.py`, `tests/test_search.py`, and
`tests/test_playlists.py` use pytest fixtures and in-memory SQLite to exercise
service behavior. The factory is launched with
`python -m flask --app app:create_app run`.
