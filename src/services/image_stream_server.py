"""TCP image stream receiver for low-overhead Raspberry Pi uploads.

Frame protocol (big-endian):
- 4 bytes magic: b'GZTK'
- 2 bytes version: uint16 (currently 1)
- 2 bytes header_len: uint16
- 4 bytes image_len: uint32
- header_len bytes UTF-8 JSON header
- image_len bytes JPEG payload

Header fields:
- stream_type: "subtask" or "session"
- user_id: string
- subtask_id: int (required for subtask stream)
- session_key: string (required for session stream)
- timestamp_ms: int (optional)
"""

from __future__ import annotations

import json
import logging
import socket
import struct
import threading
import time
from pathlib import Path
from typing import Any, Dict

from src.config import config

logger = logging.getLogger(__name__)

MAGIC = b"GZTK"
PROTOCOL_VERSION = 1
FRAME_HEADER = struct.Struct(">4sHHI")
MAX_HEADER_BYTES = 4096


class ImageStreamServer:
    """Concurrent TCP server that stores uploaded JPEG frames to disk."""

    def __init__(self) -> None:
        self._host = config.IMAGE_STREAM_HOST
        self._port = config.IMAGE_STREAM_PORT
        self._base_dir = Path(config.IMAGE_STREAM_BASE_DIR)
        self._max_image_bytes = config.IMAGE_STREAM_MAX_FRAME_BYTES

        self._sock: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._running = False

        self._lock = threading.Lock()
        self._active_clients = 0
        self._total_clients = 0
        self._frames_saved = 0
        self._frames_dropped = 0
        self._bytes_saved = 0
        self._last_error = ""

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True

        self._base_dir.mkdir(parents=True, exist_ok=True)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self._host, self._port))
        sock.listen(config.IMAGE_STREAM_BACKLOG)
        sock.settimeout(1.0)
        self._sock = sock

        self._accept_thread = threading.Thread(target=self._accept_loop, name="image-stream-accept", daemon=True)
        self._accept_thread.start()

        logger.info("Image stream server listening on %s:%d", self._host, self._port)

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False

        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

        if self._accept_thread is not None:
            self._accept_thread.join(timeout=2.0)
            self._accept_thread = None

        logger.info("Image stream server stopped")

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "host": self._host,
                "port": self._port,
                "running": self._running,
                "active_clients": self._active_clients,
                "total_clients": self._total_clients,
                "frames_saved": self._frames_saved,
                "frames_dropped": self._frames_dropped,
                "bytes_saved": self._bytes_saved,
                "base_dir": str(self._base_dir),
                "last_error": self._last_error,
            }

    def _accept_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break

            if self._sock is None:
                break

            try:
                conn, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            with self._lock:
                self._active_clients += 1
                self._total_clients += 1

            worker = threading.Thread(
                target=self._client_loop,
                args=(conn, addr),
                name=f"image-stream-client-{addr[0]}:{addr[1]}",
                daemon=True,
            )
            worker.start()

    def _client_loop(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        conn.settimeout(2.0)
        try:
            while True:
                frame_header = self._recv_exact(conn, FRAME_HEADER.size)
                if frame_header is None:
                    break

                magic, version, header_len, image_len = FRAME_HEADER.unpack(frame_header)

                if magic != MAGIC or version != PROTOCOL_VERSION:
                    self._mark_drop(f"invalid protocol from {addr}")
                    break
                if header_len == 0 or header_len > MAX_HEADER_BYTES:
                    self._mark_drop(f"invalid header length from {addr}")
                    break
                if image_len == 0 or image_len > self._max_image_bytes:
                    self._mark_drop(f"invalid image size from {addr}")
                    break

                header_bytes = self._recv_exact(conn, header_len)
                payload = self._recv_exact(conn, image_len)
                if header_bytes is None or payload is None:
                    break

                try:
                    header = json.loads(header_bytes.decode("utf-8"))
                except Exception:
                    self._mark_drop(f"invalid json header from {addr}")
                    continue

                try:
                    target_dir = self._resolve_target_dir(header)
                    target_dir.mkdir(parents=True, exist_ok=True)
                    file_path = target_dir / self._build_filename(header)
                    with file_path.open("wb") as f:
                        f.write(payload)

                    with self._lock:
                        self._frames_saved += 1
                        self._bytes_saved += len(payload)
                except Exception as exc:
                    self._mark_drop(f"save failed from {addr}: {exc}")
        finally:
            try:
                conn.close()
            except OSError:
                pass
            with self._lock:
                self._active_clients = max(0, self._active_clients - 1)

    def _recv_exact(self, conn: socket.socket, size: int) -> bytes | None:
        data = bytearray()
        while len(data) < size:
            try:
                chunk = conn.recv(size - len(data))
            except socket.timeout:
                continue
            except OSError:
                return None

            if not chunk:
                return None
            data.extend(chunk)
        return bytes(data)

    def _resolve_target_dir(self, header: Dict[str, Any]) -> Path:
        stream_type = str(header.get("stream_type", "")).strip().lower()

        if stream_type == "subtask":
            subtask_id = int(header["subtask_id"])
            if subtask_id <= 0:
                raise ValueError("subtask_id must be positive")
            return self._base_dir / "subtasks" / str(subtask_id)

        if stream_type == "session":
            session_key = self._sanitize_component(str(header.get("session_key", "")))
            if not session_key:
                user_id = self._sanitize_component(str(header.get("user_id", "unknown")))
                session_key = f"{user_id}_{int(time.time())}"
            return self._base_dir / "sessions" / session_key

        raise ValueError("stream_type must be subtask or session")

    def _build_filename(self, header: Dict[str, Any]) -> str:
        ts = header.get("timestamp_ms")
        if ts is None:
            ts = int(time.time() * 1000)
        ts_int = int(ts)

        seq = header.get("seq", 0)
        seq_int = int(seq)
        return f"{ts_int}_{seq_int}.jpg"

    def _sanitize_component(self, value: str) -> str:
        clean = []
        for ch in value:
            if ch.isalnum() or ch in ("-", "_"):
                clean.append(ch)
        return "".join(clean)[:80]

    def _mark_drop(self, message: str) -> None:
        logger.warning("image-stream drop: %s", message)
        with self._lock:
            self._frames_dropped += 1
            self._last_error = message


image_stream_server = ImageStreamServer()
