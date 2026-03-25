"""RTSP frame ingest worker that decodes frames with OpenCV and persists JPEGs."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict

import cv2

from src.config import config

logger = logging.getLogger(__name__)


class RtspStreamServer:
    """Background RTSP decoder for fallback frame ingestion."""

    def __init__(self) -> None:
        self._url = config.RTSP_SOURCE_URL
        self._base_dir = Path(config.RTSP_BASE_DIR)
        self._stream_type = str(config.RTSP_STREAM_TYPE).strip().lower()
        self._session_key = self._sanitize_component(str(config.RTSP_SESSION_KEY)) or "rtsp_fallback"
        self._subtask_id = int(config.RTSP_SUBTASK_ID)
        self._max_fps = max(0.1, float(config.RTSP_MAX_FPS))
        self._jpeg_quality = max(30, min(95, int(config.RTSP_JPEG_QUALITY)))
        self._reconnect_seconds = max(0.2, float(config.RTSP_RECONNECT_SECONDS))

        self._running = False
        self._worker: threading.Thread | None = None

        self._lock = threading.Lock()
        self._frames_decoded = 0
        self._frames_saved = 0
        self._decode_failures = 0
        self._reconnect_count = 0
        self._bytes_saved = 0
        self._last_error = ""

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True

        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._worker = threading.Thread(target=self._worker_loop, name="rtsp-stream-worker", daemon=True)
        self._worker.start()
        logger.info("rtsp-stream started source=%s", self._url)

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False

        if self._worker is not None:
            self._worker.join(timeout=2.0)
            self._worker = None

        logger.info("rtsp-stream stopped")

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "enabled": config.RTSP_FALLBACK_ENABLED,
                "running": self._running,
                "source_url": self._url,
                "stream_type": self._stream_type,
                "session_key": self._session_key,
                "subtask_id": self._subtask_id,
                "frames_decoded": self._frames_decoded,
                "frames_saved": self._frames_saved,
                "decode_failures": self._decode_failures,
                "reconnect_count": self._reconnect_count,
                "bytes_saved": self._bytes_saved,
                "last_error": self._last_error,
            }

    def _worker_loop(self) -> None:
        next_allowed_frame = 0.0
        frame_interval = 1.0 / self._max_fps
        seq = 0

        while self._is_running():
            cap = cv2.VideoCapture(self._url)
            if not cap.isOpened():
                self._mark_failure("rtsp open failed")
                self._bump_reconnect()
                time.sleep(self._reconnect_seconds)
                continue

            self._bump_reconnect()
            logger.info("rtsp-stream connected source=%s", self._url)

            try:
                while self._is_running():
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        self._mark_failure("rtsp decode failed")
                        break

                    now = time.monotonic()
                    if now < next_allowed_frame:
                        continue
                    next_allowed_frame = now + frame_interval

                    self._bump_decoded()

                    encoded, jpeg = cv2.imencode(
                        ".jpg",
                        frame,
                        [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality],
                    )
                    if not encoded:
                        self._mark_failure("jpeg encode failed")
                        continue

                    payload = jpeg.tobytes()
                    try:
                        target_dir = self._resolve_target_dir()
                        target_dir.mkdir(parents=True, exist_ok=True)
                        ts = int(time.time() * 1000)
                        file_path = target_dir / f"{ts}_{seq}.jpg"
                        file_path.write_bytes(payload)
                        seq += 1
                        self._bump_saved(len(payload))
                    except Exception as exc:
                        self._mark_failure(f"save failed: {exc}")
            finally:
                cap.release()

            time.sleep(self._reconnect_seconds)

    def _resolve_target_dir(self) -> Path:
        if self._stream_type == "subtask":
            if self._subtask_id <= 0:
                raise ValueError("RTSP_SUBTASK_ID must be > 0 for subtask stream")
            return self._base_dir / "subtasks" / str(self._subtask_id)

        return self._base_dir / "sessions" / self._session_key

    def _sanitize_component(self, value: str) -> str:
        clean = []
        for ch in value:
            if ch.isalnum() or ch in ("-", "_"):
                clean.append(ch)
        return "".join(clean)[:80]

    def _is_running(self) -> bool:
        with self._lock:
            return self._running

    def _bump_decoded(self) -> None:
        with self._lock:
            self._frames_decoded += 1

    def _bump_saved(self, byte_count: int) -> None:
        with self._lock:
            self._frames_saved += 1
            self._bytes_saved += max(0, int(byte_count))
            self._last_error = ""

    def _bump_reconnect(self) -> None:
        with self._lock:
            self._reconnect_count += 1

    def _mark_failure(self, message: str) -> None:
        logger.warning("rtsp-stream warning: %s", message)
        with self._lock:
            self._decode_failures += 1
            self._last_error = message


rtsp_stream_server = RtspStreamServer()
