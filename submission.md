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

# Root Cause Analyses

**Issue #1 — My listening streak keeps resetting**

**How you reproduced it:** The isolated demo starts a friend at streak 12 with
a Saturday 2024-06-15 23:00 UTC last listen. At Sunday 09:00, it posts to
`/songs/anthem/listen` and reads `/users/friend/streak`: the original response
was 1 instead of 13 (`artifacts/baseline.json`). The added endpoint regression
also failed at the exact Saturday 23:59:59 -> Sunday 00:00 boundary. The starter
`test_streak_increments_on_sunday` returned 1 instead of 2.

**How you found the root cause:** Traced `routes/users.py:streak()` to
`streak_service.get_streak()`, which reads stored `User.listening_streak`, then
traced the mutation from `routes/songs.py:listen()` through
`record_listening_event()` to `update_listening_streak()`. Controlled dates made
`days_since_last` equal 1 while Sunday made `today.weekday()` equal 6. The
saved failing tests confirmed that this extra weekday guard selected the reset.

**The root cause:** `elif days_since_last == 1 and today.weekday() != 6` explicitly
excluded Sunday from consecutive-day increments. Sunday's valid next-day listen
fell into the reset-to-1 branch. The endpoint faithfully returned that persisted
incorrect value; the fault was in updating the model, not serializing the profile.

**Your fix:** Removed the weekday exclusion in
`services/streak_service.py:update_listening_streak()`. A one-calendar-day gap now
increments on every weekday, using the existing UTC convention and date arithmetic.

**Your side-effect check:** Ran `tests/test_streaks.py` and
`tests/regressions/test_streak_api.py`: **10 passed** (`artifacts/issue_1_tests.txt`).
`test_calendar_streak_persists_through_listen_endpoint` covers Saturday/Sunday,
Sunday/Monday, repeated Sunday listening, a skipped day ending Sunday, and the
year boundary. It removes the session and reads stored streak/event state through
the real endpoint. Existing first-listen, ordinary consecutive-day, same-day, and
skipped-day tests also pass.

**Issue #2 — Friends Listening Now shows people from yesterday**

**How you reproduced it:** With the service clock fixed at Sunday 2024-06-16
09:00 UTC and a friend's sole event at Saturday 23:00 UTC,
`GET /feed/owner/listening-now` returned count 1, expected 0. After a Sunday
listen it correctly still returned 1. `artifacts/baseline.json` records both
observations; `test_listening_now_excludes_previous_evening` failed on the
original response. A separate boundary fixture also exposed a next-day event
being included because the original filter had no upper bound.

**How you found the root cause:** Followed `routes/feed.py:listening_now()` to
`services/feed_service.py:get_friends_listening_now()`, its friendship lookup,
and the `ListeningEvent.listened_at` SQL filter. It subtracted
`RECENT_THRESHOLD = timedelta(hours=24)` from `datetime.now(timezone.utc)`.
At Sunday 09:00 that cutoff is Saturday 09:00, which admits Saturday 23:00.
The model defaults and listen writer use UTC; SQLite returns these stored
timestamps without timezone metadata. No per-user timezone setting exists.

**The root cause:** The implementation selected a rolling 24-hour window, while
the user contract selects the current calendar day. Yesterday evening remained
eligible until the same hour today. Filtering and serialization were functioning;
the window's definition was wrong.

**Your fix:** `get_friends_listening_now()` now computes UTC midnight and the
following midnight, selecting `listened_at >= day_start` and
`listened_at < day_end`. This includes today's midnight and excludes both
yesterday and tomorrow. Existing latest-event-per-friend selection and descending
timestamp order remain in place. General activity history retains its wider scope.

**Your side-effect check:** Both tests in `tests/regressions/test_feed_api.py`
passed (`artifacts/issue_2_tests.txt`). Besides the evening-to-morning regression,
`test_feed_midnight_bounds_latest_friend_and_order` checks just before midnight,
exact midnight, next midnight, the latest song for a friend with multiple listens,
descending friend order, exclusion of self/nonfriends, empty friendships, and
HTTP 404 for a missing user. The previous-day event remains visible through
`/feed/owner/activity`.

**Issue #3 — The same song keeps showing up twice in search**

**How you reproduced it:** Created Crown Heights Anthem with three `song_tags`
associations (rap, hip-hop, boom bap) and requested `GET /songs/search?q=Anthem`.
The original returned three dictionaries with the same song ID, while songs with
zero or one tag appeared once (`artifacts/baseline.json`). The actual seeded Flask
server also returned HTTP 200 with three Anthem entries. The starter multi-tag
test and the added three-tag endpoint case both failed before changes.

**How you found the root cause:** Traced `routes/songs.py:search()` to
`services/search_service.py:search_songs()` and the `Song`/`song_tags` relationship
in `models.py`. `select(Song).outerjoin(song_tags, ...)` produces one SQL row per
association. `db.session.execute(...).scalars().all()` in the starter's SQLAlchemy
2-style query keeps those repeated entity references. Varying tag counts in the
same test isolated the cause; the symptom did not require a separate search path.

**The root cause:** A many-to-many join multiplied the selected song rows, and
the scalar result was serialized without entity deduplication. A title/artist
match is true for each joined tag row, so a three-tag song yielded three identical
results. Zero-tag songs survive the outer join as one row.

**Your fix:** Added `.unique()` after `.scalars()` in `search_songs()` before
materialization. SQLAlchemy now emits each song identity once while keeping its
loaded tags. The title/artist predicates, outer join, and encounter order are
preserved. The starter defines no explicit search sorting clause, so no new
sort contract was introduced.

**Your side-effect check:** All **9 tests passed** across `tests/test_search.py`
and `tests/regressions/test_search_api.py` (`artifacts/issue_3_tests.txt`).
`test_search_unique_with_complete_tags` covers zero/one/three tags, case-insensitive
artist and title queries, and complete tag serialization. The distinct-song test
ensures two records with identical titles/artists remain two results rather than
being collapsed by display text. Missing-query HTTP 400 and empty-match response
schema also pass.

**Issue #4 — I got notified when a friend added my song to a playlist but not when they rated it**

**How you reproduced it:** Posted `{"user_id":"friend","score":5}` to
`/songs/song/rate` in an isolated fixture. HTTP 201 and a fresh-session `Rating`
lookup confirmed the score persisted, but `/users/owner/notifications` had count
0 instead of 1. The demo independently records the same behavior for `anthem`
in `artifacts/baseline.json`. The reference playlist notification path was
exercised with a populated association (avoiding the separately documented
original new-entry insertion failure); it produced `song_added_to_playlist`.

**How you found the root cause:** Followed `routes/songs.py:rate()` into
`notification_service.rate_song()` and compared it with
`routes/playlists.py:add_song()` -> `add_to_playlist()` -> `create_notification()`.
The latter explicitly creates a `Notification` addressed to `Song.shared_by`.
The former validates and upserts `Rating`, then commits and returns without
calling any notification helper. `get_notifications()` only reads existing rows;
there is no automatic model event linking Rating persistence to notification creation.

**The root cause:** The rating workflow omitted an entire notification-producing
step. Saving a `Rating` does not itself create a `Notification`. This architectural
data-flow omission explains why valid ratings persisted while no notification
ever existed to retrieve, unlike the explicit playlist interaction flow.

**Your fix:** New ratings in `services/notification_service.py:rate_song()` now
call the shared `create_notification()` helper with type `song_rated`, the song
sharer as recipient, and the actor/song/score in the body. The helper accepts a
keyword-only `commit=False` option so the rating and notification commit together;
its default retains existing standalone behavior. Self-ratings do not notify.
The chosen repeat policy is one notification per newly created user/song rating:
retries and score edits update the existing rating without additional alerts.
Other users' first ratings each produce their own alert, matching the existing
playlist flow's non-owner interaction policy without adding new friendship rules.

**Your side-effect check:** All **5 notification tests passed**
(`artifacts/issue_4_tests.txt`). `test_saved_rating_notifies_song_owner` verifies
persisted data, recipient, body, type, unread state, and no rater notification.
The rerating test checks stable rating ID, changed score, one stored rating,
and notifications from different users. Self/invalid-score/missing-entity cases
do not create alerts. The playlist comparison test preserves playlist alerts
and verifies mark-read/unread filtering; the commit-failure test rolls back both
Rating and Notification. Issue 5 will additionally exercise the reference flow
through an actual new playlist entry once its insertion obstacle is repaired.
