"""Seed a temporary database and smoke-test an actual Flask factory subprocess."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="mixtape-http-") as temporary:
        environment = os.environ.copy()
        environment["FLASK_SKIP_DOTENV"] = "1"
        environment["DATABASE_URL"] = "sqlite:///" + (Path(temporary) / "smoke.db").as_posix()
        hidden = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        seed = subprocess.run([sys.executable, "seed_data.py"], cwd=root,
                              env=environment, capture_output=True, text=True, check=True, **hidden)
        print(seed.stdout.strip())
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        command = [sys.executable, "-m", "flask", "--app", "app:create_app", "run",
                   "--host", "127.0.0.1", "--port", str(port), "--no-reload"]
        with (Path(temporary) / "server.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=root, env=environment,
                                       stdout=log, stderr=log, **hidden)
            try:
                for attempt in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Flask factory process exited before readiness")
                    try:
                        with urlopen(f"http://127.0.0.1:{port}/songs/search?q=Anthem", timeout=1) as response:
                            data = json.load(response)
                            status = response.status
                        break
                    except (URLError, TimeoutError):
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Flask server did not become ready")
                assert status == 200 and data["count"] == 1
                assert data["results"][0]["title"] == "Crown Heights Anthem"
                print("Factory startup: PASS (python -m flask --app app:create_app run)")
                print("GET /songs/search?q=Anthem: HTTP 200; count=1; title=Crown Heights Anthem")
            finally:
                if os.name == "nt" and process.poll() is None:
                    # Windows venv redirectors can have a child interpreter.
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   capture_output=True, check=True, **hidden)
                else:
                    process.terminate()
                process.wait(timeout=10)
    print("Temporary database removed; server stopped; private .env not loaded.")


if __name__ == "__main__":
    main()
