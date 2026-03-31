"""RTSP frame ingest worker that decodes frames with OpenCV and persists JPEGs."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict
import shutil
import os

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
        
        # Cleanup configuration
        self._max_age_hours = getattr(config, 'RTSP_MAX_FRAME_AGE_HOURS', 24)  # Default 24 hours
        self._max_storage_mb = getattr(config, 'RTSP_MAX_STORAGE_MB', 1024)  # Default 1GB
        self._cleanup_interval_seconds = getattr(config, 'RTSP_CLEANUP_INTERVAL_SECONDS', 3600)  # Default 1 hour

        self._running = False
        self._worker: threading.Thread | None = None
        self._cleanup_worker: threading.Thread | None = None

        self._lock = threading.Lock()
        self._frames_decoded = 0
        self._frames_saved = 0
        self._decode_failures = 0
        self._reconnect_count = 0
        self._bytes_saved = 0
        self._last_error = ""
        self._last_cleanup_time = 0
        self._frames_cleaned = 0

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True

        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._worker = threading.Thread(target=self._worker_loop, name="rtsp-stream-worker", daemon=True)
        self._cleanup_worker = threading.Thread(target=self._cleanup_loop, name="rtsp-cleanup-worker", daemon=True)
        self._worker.start()
        self._cleanup_worker.start()
        logger.info("rtsp-stream started source=%s", self._url)

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False

        if self._worker is not None:
            self._worker.join(timeout=2.0)
            self._worker = None
            
        if self._cleanup_worker is not None:
            self._cleanup_worker.join(timeout=2.0)
            self._cleanup_worker = None

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
                "frames_cleaned": self._frames_cleaned,
                "decode_failures": self._decode_failures,
                "reconnect_count": self._reconnect_count,
                "bytes_saved": self._bytes_saved,
                "last_error": self._last_error,
                "cleanup_config": {
                    "max_age_hours": self._max_age_hours,
                    "max_storage_mb": self._max_storage_mb,
                    "cleanup_interval_seconds": self._cleanup_interval_seconds
                }
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

    def _cleanup_loop(self) -> None:
        """Background cleanup loop that removes old frames based on age and storage limits."""
        logger.info("rtsp-cleanup worker started")
        
        while self._is_running():
            try:
                # Sleep for the configured interval
                for _ in range(self._cleanup_interval_seconds):
                    if not self._is_running():
                        break
                    time.sleep(1)
                
                if not self._is_running():
                    break
                
                # Perform cleanup
                cleaned_count = self._cleanup_old_frames()
                
                if cleaned_count > 0:
                    logger.info(f"rtsp-cleanup removed {cleaned_count} old frame files")
                    
            except Exception as e:
                logger.error(f"rtsp-cleanup error: {e}")
                time.sleep(60)  # Wait 1 minute on error before retrying
        
        logger.info("rtsp-cleanup worker stopped")

    def _cleanup_old_frames(self) -> int:
        """Clean up old frame files based on age and storage limits.
        
        Returns:
            Number of files cleaned up
        """
        try:
            if not self._base_dir.exists():
                return 0
            
            current_time = time.time()
            max_age_seconds = self._max_age_hours * 3600
            max_storage_bytes = self._max_storage_mb * 1024 * 1024
            
            total_cleaned = 0
            
            # Clean up both session and subtask directories
            for target_dir in [self._base_dir / "sessions", self._base_dir / "subtasks"]:
                if not target_dir.exists():
                    continue
                
                # Walk through all subdirectories
                for session_dir in target_dir.iterdir():
                    if not session_dir.is_dir():
                        continue
                    
                    files_to_delete = []
                    total_size = 0
                    
                    # Collect all frame files with their info
                    for file_path in session_dir.iterdir():
                        if not file_path.is_file() or file_path.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
                            continue
                        
                        file_age = current_time - file_path.stat().st_mtime
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        
                        # Mark for deletion if too old
                        if file_age > max_age_seconds:
                            files_to_delete.append((file_path, "age"))
                    
                    # If storage limit exceeded, mark oldest files for deletion
                    if total_size > max_storage_bytes:
                        all_files = []
                        for file_path in session_dir.iterdir():
                            if not file_path.is_file() or file_path.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
                                continue
                            if file_path in [f[0] for f in files_to_delete]:
                                continue
                            all_files.append((file_path, file_path.stat().st_mtime))
                        
                        # Sort by modification time (oldest first)
                        all_files.sort(key=lambda x: x[1])
                        
                        # Delete oldest files until under storage limit
                        remaining_size = total_size
                        for file_path, mtime in all_files:
                            if remaining_size <= max_storage_bytes * 0.8:  # Leave 20% buffer
                                break
                            files_to_delete.append((file_path, "storage"))
                            remaining_size -= file_path.stat().st_size
                    
                    # Delete marked files
                    for file_path, reason in files_to_delete:
                        try:
                            file_path.unlink()
                            total_cleaned += 1
                        except OSError as e:
                            logger.error(f"Failed to delete {file_path}: {e}")
                    
                    # Remove empty directories
                    try:
                        if not any(session_dir.iterdir()):
                            session_dir.rmdir()
                            logger.debug(f"Removed empty directory: {session_dir}")
                    except OSError:
                        # Directory not empty, that's fine
                        pass
            
            # Update cleanup counter
            with self._lock:
                self._frames_cleaned += total_cleaned
                self._last_cleanup_time = current_time
            
            return total_cleaned
            
        except Exception as e:
            logger.error(f"Error during frame cleanup: {e}")
            return 0

    def trigger_cleanup(self) -> int:
        """Manually trigger cleanup of old frames.
        
        Returns:
            Number of files cleaned up
        """
        return self._cleanup_old_frames()
    
    def get_cleanup_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics.
        
        Returns:
            Dictionary with cleanup statistics
        """
        with self._lock:
            return {
                "frames_cleaned": self._frames_cleaned,
                "last_cleanup_time": self._last_cleanup_time,
                "cleanup_interval_seconds": self._cleanup_interval_seconds,
                "max_age_hours": self._max_age_hours,
                "max_storage_mb": self._max_storage_mb
            }

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
