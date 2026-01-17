"""State Manager for Subit ASR Service

Manages global state to ensure only one transcription task runs at a time.
Uses singleton pattern to maintain state across the application.
"""

import threading
from pathlib import Path
from typing import Dict, List, Optional
import uuid
import shutil
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StateManager:
    """Singleton state manager for transcription service."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self.current_video: Optional[Path] = None
            self.video_id: Optional[str] = None
            self.is_processing: bool = False
            self.processing_id: Optional[str] = None
            self.transcriptions: List[Dict] = []
            self.audio_duration: float = 0.0
            self.total_chunks: int = 0
            self._state_lock = threading.Lock()
            self._cancelled = False
            self._current_thread: Optional[threading.Thread] = None
            self._initialized = True

    def can_start_new_task(self) -> bool:
        """Check if a new task can be started."""
        return not self.is_processing

    def is_cancelled(self) -> bool:
        """Check if current task has been cancelled."""
        with self._state_lock:
            return self._cancelled

    def cancel_task(self) -> None:
        """Cancel current task."""
        with self._state_lock:
            self._cancelled = True
            logger.info("Task cancellation requested")

    def reset_cancel_flag(self) -> None:
        """Reset cancellation flag."""
        with self._state_lock:
            self._cancelled = False

    def set_current_thread(self, thread: threading.Thread) -> None:
        """Set current processing thread."""
        with self._state_lock:
            self._current_thread = thread

    def get_current_thread(self) -> Optional[threading.Thread]:
        """Get current processing thread."""
        with self._state_lock:
            return self._current_thread

    def _cleanup_file_safely(self, file_path: Path) -> None:
        """Safely delete a file with retries."""
        if not file_path or not file_path.exists():
            return

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Deleted file: {file_path}")
                    return
            except PermissionError:
                # File might still be in use, wait and retry
                if attempt < max_retries - 1:
                    time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Error deleting {file_path}: {e}")
                break

    def _cleanup_temp_directory(self) -> None:
        """Clean up temp directory."""
        try:
            import config
            if config.TEMP_DIR.exists():
                for file in config.TEMP_DIR.iterdir():
                    if file.is_file():
                        self._cleanup_file_safely(file)
        except Exception as e:
            logger.debug(f"Error cleaning temp directory: {e}")

    def _cleanup_uploads_directory(self, except_video: Optional[Path] = None) -> None:
        """Clean up all video files except the specified one."""
        try:
            import config
            if config.UPLOAD_FOLDER.exists():
                for file in config.UPLOAD_FOLDER.iterdir():
                    if file.is_file() and file != except_video:
                        self._cleanup_file_safely(file)
        except Exception as e:
            logger.debug(f"Error cleaning uploads directory: {e}")

    def reset_state(self, cleanup_files: bool = True, except_video: Optional[Path] = None) -> None:
        """Reset all state and optionally cleanup files.

        Args:
            cleanup_files: Whether to clean up files
            except_video: A video file path to keep (e.g., the new video being uploaded)
        """
        with self._state_lock:
            # Store current video path before resetting
            old_video = self.current_video

            # Clean up old video file (but not the except_video)
            if cleanup_files and old_video and old_video.exists() and old_video != except_video:
                self._cleanup_file_safely(old_video)

            # Clean up extracted audio if exists
            if cleanup_files and old_video:
                audio_path = old_video.parent / f"{old_video.stem}_audio.wav"
                if audio_path.exists():
                    self._cleanup_file_safely(audio_path)

            # Clean up temp directory
            if cleanup_files:
                self._cleanup_temp_directory()

            # Clean up other uploaded videos except the except_video
            if cleanup_files:
                self._cleanup_uploads_directory(except_video=except_video)

            # Reset all state variables
            self.current_video = except_video if except_video else None
            self.video_id = None
            self.is_processing = False
            self.processing_id = None
            self.transcriptions = []
            self.audio_duration = 0.0
            self.total_chunks = 0
            self._cancelled = False
            self._current_thread = None

            logger.info("State reset completed")

    def start_task(self, video_path: Path, video_id: str) -> Optional[str]:
        """Start a new transcription task.

        Returns:
            Task ID if successful, None if a task is already running.
        """
        with self._state_lock:
            if self.is_processing:
                return None

            self.is_processing = True
            self.current_video = video_path
            self.video_id = video_id
            self.processing_id = str(uuid.uuid4())
            self.transcriptions = []
            self.audio_duration = 0.0
            self.total_chunks = 0
            self._cancelled = False
            return self.processing_id

    def get_progress(self) -> Dict:
        """Get current transcription progress."""
        with self._state_lock:
            completed = len(self.transcriptions)
            if self.total_chunks > 0:
                progress = int((completed / self.total_chunks) * 100)
            else:
                progress = 0

            return {
                "is_processing": self.is_processing,
                "progress": progress,
                "completed_chunks": completed,
                "total_chunks": self.total_chunks,
                "audio_duration": self.audio_duration,
            }

    def get_transcriptions(self) -> List[Dict]:
        """Get all completed transcriptions."""
        with self._state_lock:
            return list(self.transcriptions)

    def add_transcription(
        self, index: int, text: str, start_time: float, end_time: float
    ) -> None:
        """Add a transcription result."""
        with self._state_lock:
            self.transcriptions.append(
                {
                    "index": index,
                    "text": text,
                    "start_time": start_time,
                    "end_time": end_time,
                }
            )

    def set_audio_duration(self, duration: float) -> None:
        """Set total audio duration."""
        with self._state_lock:
            self.audio_duration = duration

    def set_total_chunks(self, count: int) -> None:
        """Set total number of chunks to process."""
        with self._state_lock:
            self.total_chunks = count

    def complete_task(self) -> None:
        """Mark current task as completed."""
        with self._state_lock:
            self.is_processing = False

    def get_video_info(self) -> Optional[Dict]:
        """Get current video information."""
        with self._state_lock:
            if self.current_video is None:
                return None
            return {
                "video_id": self.video_id,
                "filename": self.current_video.name,
                "duration": self.audio_duration,
            }

    def is_same_video(self, video_id: str) -> bool:
        """Check if given video_id matches current video."""
        with self._state_lock:
            return self.video_id == video_id


# Global instance
_state_manager = None


def get_state_manager() -> StateManager:
    """Get singleton state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
