"""Deterministic endpoint demonstration; creates only an in-memory database."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app, db
from models import ListeningEvent, Playlist, Rating, Song, Tag, User, playlist_entries
from services import feed_service, streak_service
from sqlalchemy.exc import IntegrityError


class DemoClock(datetime):
    @classmethod
    def now(cls, tz=None):
        instant = datetime(2024, 6, 16, 9, tzinfo=timezone.utc)
        return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)


def demonstrate():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context(), patch.object(streak_service, "datetime", DemoClock), patch.object(feed_service, "datetime", DemoClock):
        owner = User(id="owner", username="owner", email="owner@example.test")
        friend = User(id="friend", username="friend", email="friend@example.test",
                      listening_streak=12, last_listened_at=datetime(2024, 6, 15, 23))
        owner.friends.append(friend)
        db.session.add_all([owner, friend])
        db.session.flush()
        db.session.add(Song(id="anthem", title="Crown Heights Anthem", artist="Borough Kings",
                            shared_by="owner", tags=[Tag(name=n) for n in ["rap", "hip-hop", "boom bap"]]))
        db.session.add(Playlist(id="playlist", name="Friday Energy", created_by="friend"))
        for index in range(1, 9):
            db.session.add(Song(id=f"track-{index}", title=f"Track {index}", artist="Various", shared_by="owner"))
        db.session.flush()
        for index in range(1, 8):
            db.session.execute(playlist_entries.insert().values(
                playlist_id="playlist", song_id=f"track-{index}", position=index, added_by="friend"))
        db.session.add(ListeningEvent(user_id="friend", song_id="anthem", listened_at=datetime(2024, 6, 15, 23)))
        db.session.commit()
        client = app.test_client()
        report = {}

        # Read yesterday's feed before recording today's listen.
        yesterday = client.get("/feed/owner/listening-now").get_json()["count"]
        client.post("/songs/anthem/listen", json={"user_id": "friend"})
        report["issue_1"] = {"saturday_streak": 12,
                             "sunday_streak": client.get("/users/friend/streak").get_json()["streak"],
                             "expected": 13}
        report["issue_2"] = {"yesterday_only_count": yesterday,
                             "after_today_listen_count": client.get("/feed/owner/listening-now").get_json()["count"],
                             "expected": [0, 1]}
        search = client.get("/songs/search?q=Anthem").get_json()
        report["issue_3"] = {"matching_results": search["count"],
                             "unique_song_ids": len({s["id"] for s in search["results"]}), "expected": 1}
        rating_response = client.post("/songs/anthem/rate", json={"user_id": "friend", "score": 5})
        db.session.remove()
        rating = db.session.get(Rating, rating_response.get_json()["id"])
        notifications = client.get("/users/owner/notifications").get_json()
        report["issue_4"] = {"rating_http_status": rating_response.status_code,
                             "persisted_score": rating.score,
                             "rating_notifications": sum(n["type"] == "song_rated" for n in notifications["notifications"]),
                             "expected": 1}
        before = client.get("/playlists/playlist/songs").get_json()
        try:
            add_status = client.post("/playlists/playlist/songs", json={"song_id": "track-8", "added_by": "friend"}).status_code
            add_error = None
        except IntegrityError as error:
            add_status = None
            add_error = str(error.orig)
            db.session.rollback()
            # On the original code, isolate retrieval after reproducing POST's failure.
            db.session.execute(playlist_entries.insert().values(
                playlist_id="playlist", song_id="track-8", position=8, added_by="friend"))
            db.session.commit()
        after = client.get("/playlists/playlist/songs").get_json()
        report["issue_5"] = {"stored_before": 7, "returned_before": before["count"],
                             "post_status": add_status, "post_error": add_error,
                             "returned_after": after["count"],
                             "last_visible_before": before["songs"][-1]["title"],
                             "last_visible_after": after["songs"][-1]["title"],
                             "expected_counts": [7, 8]}
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable observed results")
    parser.add_argument("--check", action="store_true", help="Fail if any corrected behavior is missing")
    args = parser.parse_args()
    result = demonstrate()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Mixtape: isolated database, clock fixed at Sunday 2024-06-16 09:00 UTC")
        print(f"1. Streak: Saturday 12 -> Sunday {result['issue_1']['sunday_streak']} (expected 13)")
        print(f"2. Feed: yesterday only = {result['issue_2']['yesterday_only_count']}; after today's listen = {result['issue_2']['after_today_listen_count']} (expected 0, 1)")
        print(f"3. Search: Anthem results = {result['issue_3']['matching_results']} (expected 1)")
        print(f"4. Rating: saved {result['issue_4']['persisted_score']}/5; owner notifications = {result['issue_4']['rating_notifications']} (expected 1)")
        print(f"5. Playlist: {result['issue_5']['returned_before']}/7 before; {result['issue_5']['returned_after']}/8 after POST (expected 7, 8)")
        if result['issue_5']['post_error']:
            print(f"   Original POST error: {result['issue_5']['post_error']}; retrieval checked after explicit fixture insertion.")
    if args.check:
        assert result["issue_1"]["sunday_streak"] == 13
        assert [result["issue_2"]["yesterday_only_count"], result["issue_2"]["after_today_listen_count"]] == [0, 1]
        assert result["issue_3"]["matching_results"] == 1
        assert result["issue_4"]["rating_notifications"] == 1
        assert result["issue_5"]["post_status"] == 201
        assert [result["issue_5"]["returned_before"], result["issue_5"]["returned_after"]] == [7, 8]
        print("All five corrected behaviors verified.")


if __name__ == "__main__":
    main()
