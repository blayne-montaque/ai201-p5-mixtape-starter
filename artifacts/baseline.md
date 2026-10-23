# Original behavior checkpoint

Captured on 2026-10-23 after orientation commit `6d78b8f`, before any production
source changes. Original application revision: `aaead6a` (fork's main).
The full course brief supplied in chat was read; all five original report titles
and required RCA fields will be used. The separate detailed grading page was not
provided; coverage is assessed against the brief's 25 required + 3 stretch points.

Commands (repository root, Windows PowerShell):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_streaks.py tests/test_search.py tests/test_playlists.py -q
.\.venv\Scripts\python.exe -m pytest tests/regressions -q --tb=short
.\.venv\Scripts\python.exe scripts/demo_mixtape.py --json
```

Results: starter tests **4 failed, 9 passed**; added endpoint regressions
**11 failed, 10 passed**. Full observed failures are in `starter_tests.txt` and
`baseline_regressions.txt`; concise endpoint observations are in `baseline.json`.
The demo uses only an in-memory SQLite database and freezes service clocks at
Sunday 2024-06-16 09:00 UTC. Its source records every fixture and request.

| Issue | Fixture and exact path | Observed | Expected |
| --- | --- | --- | --- |
| 1 | Saturday 23:00 UTC, streak 12; `POST /songs/anthem/listen`, then `GET /users/friend/streak` on Sunday | Streak 1 | 13 |
| 2 | Friend's event Saturday 23:00; `GET /feed/owner/listening-now` Sunday 09:00; then repeat after today's listen | Counts 1 then 1 | 0 then 1 |
| 3 | Crown Heights Anthem linked to rap, hip-hop, boom bap; `GET /songs/search?q=Anthem` | 3 results, 1 unique song ID | 1 result |
| 4 | Friend rates owner's song 5; `POST /songs/anthem/rate`, session removed, Rating read back, `GET /users/owner/notifications` | HTTP 201, persisted score 5, 0 rating notifications | 1 owner notification |
| 5 | Seven positioned entries; `GET /playlists/playlist/songs`; add eighth; repeat GET | 6/7 then 7/8; last visible changes Track 6 to Track 7 | 7/7 then 8/8 |

Execution paths investigated after orientation:

- `routes/songs.py:listen` -> `streak_service.record_listening_event` ->
  `update_listening_streak` -> `User`; `routes/users.py:streak` -> `get_streak`.
- `routes/feed.py:listening_now` -> `feed_service.get_friends_listening_now` ->
  friendships and `ListeningEvent` timestamp filtering.
- `routes/songs.py:search` -> `search_service.search_songs` -> `Song`/`song_tags` join.
- `routes/songs.py:rate` -> `notification_service.rate_song` -> `Rating`;
  compared `add_to_playlist` -> `create_notification` -> `Notification` and
  `routes/users.py:notifications` -> `get_notifications`.
- `routes/playlists.py:get_songs` -> `playlist_service.get_playlist_songs` ->
  `playlist_entries` ordered join; `add_song` -> `notification_service.add_to_playlist`.

## Additional observed obstacle within Issue 5

The original POST for a new playlist item raises
`NOT NULL constraint failed: playlist_entries.position`. Its relationship append
inserts only playlist ID, song ID, and timestamp, omitting required `position` and
`added_by`. The baseline demo catches this real error, rolls back, inserts the
eighth association explicitly as fixture setup, then checks retrieval again.
This distinguishes the reported omitted-last-item behavior from the additional
POST obstruction. Both empty and seven-entry POST regressions preserve the error.
Issue 5 will repair the insertion as well as retrieval to make the user's entire
reported sequence executable. No schema constraints will be weakened.

## Environment and startup

Python 3.10 with a new local `.venv`; requirements installed successfully.
Sandbox network/Git-metadata restrictions required approved elevated clone,
dependency-install, and Git-write commands. No dependency compatibility change
was necessary. Seeded only `sqlite:///mixtape-demo.db` (ignored instance folder):
5 users, 13 songs, 3 playlists, 10 tags. The starter seed header's 25-song claim
does not match its executable data; source seed data was preserved.

Launched using `FLASK_SKIP_DOTENV=1`, the explicit demo database URL, and
`python -m flask --app app:create_app run --host 127.0.0.1 --port 5000 --no-reload`.
An actual HTTP request to `/songs/search?q=Anthem` returned **200** with three
identical Crown Heights Anthem results. The API has no root-page route; verification
uses a real API endpoint. No `.env` content or LLM credentials were loaded.
