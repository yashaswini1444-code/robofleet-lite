"""Real-network regression test for Uvicorn's WebSocket protocol support."""

import asyncio
import json
import socket
import subprocess
import sys
import time
import urllib.request

import websockets


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _wait_until_ready(url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(f"Uvicorn exited early.\nstdout:\n{stdout}\nstderr:\n{stderr}")
        try:
            with urllib.request.urlopen(url, timeout=0.25) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("Uvicorn did not become ready within 10 seconds")


def test_real_uvicorn_websocket_upgrade_and_initial_snapshot():
    """Exercise the actual TCP upgrade path, which TestClient bypasses."""
    port = _free_port()
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_until_ready(f"http://127.0.0.1:{port}/health", process)

        async def receive_snapshot():
            async with websockets.connect(f"ws://127.0.0.1:{port}/ws/simulation", open_timeout=5) as websocket:
                return json.loads(await asyncio.wait_for(websocket.recv(), timeout=5))

        snapshot = asyncio.run(receive_snapshot())
        assert len(snapshot["robots"]) == 3
        assert snapshot["tick"] == 0
        assert snapshot["running"] is False
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
