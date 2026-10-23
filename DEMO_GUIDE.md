# Mixtape recording guide

Mixtape is a social music JSON API: friends share songs, rate them, build playlists,
and follow listening activity. This project repaired all five reported bugs and
documented the causes with original failing evidence, regression tests, and five
separate fix commits. There is no frontend to navigate; the terminal demo is the
fastest way to show the assignment clearly during the Projects 3/4/5 batch session.

## Prepare once in Windows PowerShell

```powershell
Set-Location 'D:\Productivity\School\Howard University\Courses\Fall 2026\CSCI 485\Project 5'
# Already installed in this workspace; these commands also set up a fresh clone.
if (-not (Test-Path .venv\Scripts\python.exe)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
git branch --show-current
```

The branch should be `bugfix/mixtape`. Calling the venv's interpreter directly
avoids PowerShell activation-policy changes. No API key is needed. Do not display
`.env` while recording.

## The shortest recording sequence

These commands need no running server and never touch a disk database. Every
invocation builds a fresh in-memory fixture; rerunning is the reset operation.

```powershell
# 1. Saved original observations, without checking out or undoing fixes.
$before = Get-Content artifacts\baseline.json -Raw | ConvertFrom-Json
$before.issue_1 | Format-List
$before.issue_3 | Format-List

# 2. Run real routes, services, and SQLAlchemy against isolated demo fixtures.
.\.venv\Scripts\python.exe scripts\demo_mixtape.py --check

# 3. Show the complete regression result and graded history.
.\.venv\Scripts\python.exe -m pytest tests/ -q
git branch --show-current
git --no-pager log --oneline
```

The saved **before** streak is Saturday 12 -> Sunday **1**, expected 13.
The saved **before** search is **3 results with 1 unique song ID**. Those are
observations captured before production edits, not simulated broken responses.
The baseline's playlist POST error is also preserved; see `artifacts/baseline.md`
for why an explicit eighth fixture entry was needed to demonstrate retrieval then.

Actual verified output from the corrected demo (`artifacts/demo_output.txt`):

```text
Mixtape: isolated database, clock fixed at Sunday 2024-06-16 09:00 UTC
1. Streak: Saturday 12 -> Sunday 13 (expected 13)
2. Feed: yesterday only = 0; after today's listen = 1 (expected 0, 1)
3. Search: Anthem results = 1 (expected 1)
4. Rating: saved 5/5; owner notifications = 1 (expected 1)
5. Playlist: 7/7 before; 8/8 after POST (expected 7, 8)
All five corrected behaviors verified.
```

The full suite reports **35 passed** (runtime varies). The demo freezes only the
clock, uses a real Flask test client and database, and persists real model changes.
For a machine-readable after-state, run:

```powershell
.\.venv\Scripts\python.exe scripts\demo_mixtape.py --json
```

## Start a live server and safely reset demo seed data

Use a dedicated demo database. `seed_data.py` drops and rebuilds the selected
database, so always set the demo URL explicitly before seeding. These commands
reset only `instance/mixtape-demo.db`, not the default `instance/mixtape.db`.
The starter seed script and its data are unchanged.

```powershell
$env:FLASK_SKIP_DOTENV = '1'
$env:DATABASE_URL = 'sqlite:///mixtape-demo.db'
.\.venv\Scripts\python.exe seed_data.py
.\.venv\Scripts\python.exe -m flask --app app:create_app run --host 127.0.0.1 --port 5000 --no-reload
```

Actual seed output is 5 users, 13 songs, 3 playlists, and 10 tags. Keep this terminal
running. In a second PowerShell terminal, check the real HTTP endpoint:

```powershell
$response = Invoke-RestMethod 'http://127.0.0.1:5000/songs/search?q=Anthem'
$response.count
$response.results | Select-Object title, artist
```

Expected: count **1**, title **Crown Heights Anthem**, artist **Borough Kings**.
The API has no `/` homepage; use `/songs/search?q=Anthem`. Stop the server with
Ctrl+C. Never start it with `python app.py`; use the factory command above.

For an automated real-HTTP check with a temporary database and automatic cleanup:

```powershell
.\.venv\Scripts\python.exe scripts\verify_http.py
```

This launches the same Flask factory on an available localhost port, verifies
HTTP 200 and one Anthem result, stops its own server process tree, and removes its
temporary database. Its successful output is in `artifacts/startup_verification.txt`.
The Codex sandbox needed normal Windows process permissions for cleanup; the
helper was successfully verified outside that sandbox restriction.

## Brief architecture and source tour

Open `submission.md` at **Codebase Map**, then point out:

1. `app.py:create_app()` configures SQLite and registers four blueprints.
2. `models.py` defines seven entities and three association tables.
3. `routes/` parses HTTP input and formats JSON; `services/` implements behavior.
4. Playlist creation travels from `POST /playlists/` to `routes/playlists.py:create`,
   `playlist_service.create_playlist`, `db.session.add/commit`, and `Playlist.to_dict`.

Quick source highlights without opening multiple editors:

```powershell
Select-String -Path services\streak_service.py -Pattern 'days_since_last == 1' | ForEach-Object { $_.Line }
Select-String -Path services\feed_service.py -Pattern 'day_start|day_end' | ForEach-Object { $_.Line }
Select-String -Path services\search_service.py -Pattern '\.unique' | ForEach-Object { $_.Line }
Select-String -Path services\notification_service.py -Pattern 'song_rated|commit=False|position=' | ForEach-Object { $_.Line }
Select-String -Path services\playlist_service.py -Pattern 'for song in songs' | ForEach-Object { $_.Line }
```

## Individual regression demonstrations

| Behavior | PowerShell command after `.\.venv\Scripts\python.exe -m pytest` |
| --- | --- |
| Sunday, Monday, same day, gaps, year boundary | `tests/test_streaks.py tests/regressions/test_streak_api.py -q` |
| Yesterday vs today; UTC midnight; latest friend activity | `tests/regressions/test_feed_api.py -q` |
| Zero/one/three tags; distinct songs; title and artist matching | `tests/test_search.py tests/regressions/test_search_api.py -q` |
| Saved ratings; owner alerts; edits/retries; self-ratings; read state | `tests/regressions/test_notifications_api.py -q` |
| Empty/single/seven entries; new last song; ordering; repeated add | `tests/test_playlists.py tests/regressions/test_playlist_api.py -q` |

Notifications are created once per new user/song rating. Editing the score does
not issue another alert. The current-day feed follows the app's UTC convention,
not the recording computer's local timezone.

## Suggested two-to-three-minute one-take narration

**0:00–0:25 — Introduction and orientation.**
“Mixtape is a social music API where friends share songs, rate them, and build
playlists. For Project 5 I used Codex to investigate and repair all five reported
bugs. The architecture map was committed before bug investigation. Routes handle
HTTP, services handle behavior, and SQLAlchemy models persist the data.”

**0:25–0:50 — Before evidence.**
“These saved results came from the original implementation. A Saturday streak of
12 became 1 on Sunday. Searching Anthem returned three entries for one song.
The baseline commit also records yesterday's feed activity, missing rating alerts,
and a playlist returning six of seven songs.”

**0:50–1:35 — Live corrected demo.**
“This script uses real endpoints and an isolated database with a fixed clock.
Sunday now increments the streak to 13 because the weekday exclusion was removed.
The feed uses UTC midnight boundaries. Search deduplicates song identities after
the tag join. New ratings create an owner notification in the same transaction.
Playlist retrieval no longer slices off the final row, and adding a song now
supplies its required position and contributor. All five checks pass.”

**1:35–2:10 — Tests and reasoning.**
“The full suite has 35 passing tests, including the original tests. New cases
cover midnight boundaries, multiple tags, repeated ratings, owner notifications,
and empty or populated playlists. The original endpoint regressions had eleven
failures before the fixes. Each root cause analysis records the reproduction,
navigation path, exact cause, fix, and side-effect checks.”

**2:10–2:40 — History and disclosure.**
“This is the bugfix/mixtape branch. The history shows the orientation checkpoint,
the failing baseline, and five separate fix commits. The AI usage section explains
Codex's role and the checks that verified its diagnoses. The branch URL, write-up,
and Git-history screenshot are prepared for submission after publishing.”

Adapt “after publishing” if you record after pushing. Do not claim a push,
personal review, or Course Portal submission before doing it.

## Recording and handoff checklist

- Before the batch: run the demo and suite once; enlarge the terminal font.
- Keep `submission.md` and this guide open; keep `.env` closed.
- Record in this order: architecture map -> two baseline objects -> one demo
  command -> full pytest -> branch and Git history. No manual database edits.
- Capture the actual `git log --oneline` output with the branch visible if a new
  screenshot is desired. `artifacts/git_log.txt` preserves the saved command output.
- Review the recording for legibility and save it with the Project 5 title.
- Only after approving publication, run `git push -u origin bugfix/mixtape`.
- Submit the branch URL and required evidence through the Course Portal.

Intended future submission URL (local branch has not been pushed):
https://github.com/blayne-montaque/ai201-p5-mixtape-starter/tree/bugfix/mixtape
