# Project 5 repository audit

Technical audit: 2026-10-23; publication and screenshot verified 2026-10-26
(America/New_York). Target: all **25 required + 3 stretch**
points described in the user's brief. This is evidence of feature coverage, not
a claim that a course grade has been awarded. The separate detailed grading page
was not supplied; the full project brief and starter README were read.

## Rubric and deliverables

| Requirement | Evidence / status |
| --- | --- |
| Correct fork and branch | `origin` is `https://github.com/blayne-montaque/ai201-p5-mixtape-starter.git`; active branch `bugfix/mixtape`. |
| Original history preserved; main untouched | `aaead6a` remains local main and an ancestor of HEAD; all four original commits remain. |
| Orientation before investigation | `6d78b8f` creates root `submission.md`; its architectural map is byte-for-byte equivalent after newline normalization in the final document. |
| Architectural map includes real data flow | Describes factory, seven models, three association tables, routes/services/persistence, and POST playlist creation through commit and JSON response. No defect discussion in the map. |
| Reproduce before fixes | `036ae65` captures every original failure, tests, and demo; `baseline.md`, `baseline.json`, `baseline_regressions.txt`, `starter_tests.txt`. No production edits precede it. |
| Three required bugs with full RCAs | Issues 1–3 fixed, individually committed, and documented in `submission.md`. |
| Fourth-bug stretch | Issue 4 fixed and documented; commit `14b5b3d`. |
| Fifth-bug stretch | Issue 5 fixed and documented; commit `8ee7a6b`. |
| Regression-test stretch | 22 added endpoint cases in `tests/regressions/`; baseline version had 11 failures and 10 passes. One additional side-effect case was added with Issue 5. |
| Exactly five RCA fields per issue | Automated counts verify five original bold titles and all five required fields for each. See `security_and_structure_checks.txt`. |
| AI usage first | Final document begins `# AI Usage`; honestly states Codex's navigation, implementation, baseline evidence, revised playlist assumption, and executable verification. No human-review claim. |
| Separate conventional fix commits | Five commits listed below, each including its RCA and actual targeted test result. |
| Full suite | **35 passed**: 13 unchanged starter tests + 22 added regression cases; `final_tests.txt`. |
| App startup through factory | Actual local Flask process, temporary seeded DB, HTTP 200 and one Anthem result; `startup_verification.txt`, `scripts/verify_http.py`. |
| Optional recording reference | [DEMO_GUIDE.md](../DEMO_GUIDE.md) and `scripts/demo_mixtape.py` provide verified before/after examples, all five endpoints, narration, and safe reset instructions. The guide is not a required deliverable. |
| Real Git log screenshot | **Complete.** [git-history.png](git-history.png) is tracked in commit `bb9d14e` and published. Visual inspection confirms the branch and five separate fix commits. `git_log.txt` preserves the earlier command-output snapshot. |
| Published submission branch | **Complete.** [bugfix/mixtape](https://github.com/blayne-montaque/ai201-p5-mixtape-starter/tree/bugfix/mixtape) was verified against GitHub: remote and local HEAD matched `bb9d14e` before this documentation cleanup. Course Portal submission has not been confirmed. |

## Five independently committed fixes

| Commit | Issue | Targeted verification at its commit |
| --- | --- | --- |
| `6f6d0b8` | Sunday streak exclusion removed | `issue_1_tests.txt`: 10 passed |
| `e356c61` | Current UTC-day feed bounds | `issue_2_tests.txt`: 2 passed |
| `33f1766` | Identity deduplication of joined search rows | `issue_3_tests.txt`: 9 passed |
| `14b5b3d` | Rating -> owner notification in one transaction | `issue_4_tests.txt`: 5 passed |
| `8ee7a6b` | Full ordered playlist plus valid association inserts | `issue_5_tests.txt`: 14 passed |

The shared failing tests were committed first to establish the baseline. Issue 5
also finalizes tests for the real new-entry POST, rather than relying on fixture
insertion for the working notification comparison. No starter assertion was
weakened or deleted. The required regression distinction exists for every issue.

## Corrected observed outcomes

`demo_output.txt` contains the successful live demo output:
streak 12 -> 13; yesterday-only feed 0 then today's feed 1; Anthem result count 1;
persisted score 5 with one owner notification; playlist 7/7 then 8/8 after HTTP 201.
Fixtures are in-memory, deterministic, and use synthetic `example.test` identities.

Related checks cover Sunday/Monday, skipped and repeated days, midnight bounds,
nonfriends/self, latest event ordering, full tag sets, separate song identities,
rating edits/retries/different raters, self-ratings, invalid inputs, notification
read state, transaction rollback, empty/single/seven-entry playlists, gapped
positions, repeat adds, contributor/timestamp persistence, and JSON responses.

## Security and scope

- `.env` was preserved in place, ignored and untracked. Its final SHA-256 matches
  the initial observation. Only the match result is retained in the evidence.
- A pattern scan inspected deliverable text and Git patch history for Groq/OpenAI/
  GitHub/AWS token formats, private-key headers, and long credential assignments.
  No matches were found. The starter's public development `SECRET_KEY` fallback
  remains as provided; it is not the private API key.
- `.env` contents were not displayed, loaded by Flask, committed, or sent anywhere.
  No Groq/LLM API calls were used. `FLASK_SKIP_DOTENV=1` is set for live verification.
- No databases, venv files, caches, or credentials are in the tracked deliverables.
  `security_and_structure_checks.txt` records the actual checks.
- Starter seed data, schema, requirements, and existing tests were preserved.
  New persistent seeding used only the explicitly selected ignored demo database;
  the smoke check used a temporary database that was removed.
- The completed branch and screenshot are published. No PR, merge, Course Portal
  submission, or recording is claimed for this work.

## Environment, limits, and manual handoff

`environment.txt` records actual tested versions. No production dependency
compatibility fix was necessary. The new HTTP helper initially encountered Windows
venv child-process/file-lock cleanup and sandbox process permissions; process-tree
shutdown plus an approved normal-permission run resolved it. The final smoke check
finished successfully and stopped its server. No unresolved test failures remain.

The baseline's additional playlist POST failure was reproduced and repaired as
part of Issue 5. Current-day semantics are UTC because the app has no per-user
timezone model. One notification is emitted per newly created rating; later
edits/retries do not notify again. Concurrent playlist additions and broader
authentication/API-hardening work are outside this assignment; no database redesign
or unrelated UI was introduced.

Remaining submission step: submit the published branch URL, root
[submission.md](../submission.md), and genuine [Git-history screenshot](git-history.png)
through the Course Portal. The optional demo guide is available for a recording
session; it is not a required submission artifact. No further screenshot capture
or initial branch publication is needed. Final working-tree cleanliness is checked
after committing and pushing this documentation cleanup.
