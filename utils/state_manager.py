"""State Manager for Subit ASR Service

Manages global state to ensure only one transcription task runs at a time.
Uses singleton pattern to maintain state across the application.
"""

import threading
from pathlib import Path
from typing import Dict, List, Optional
import uuid
import shutil


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
            self._initialized = True

    def can_start_new_task(self) -> bool:
        """Check if a new task can be started."""
        return not self.is_processing

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
            return self.processing_id

    def reset_state(self, cleanup_files: bool = True) -> None:
        """Reset all state and optionally cleanup files."""
        with self._state_lock:
            if cleanup_files and self.current_video and self.current_video.exists():
                try:
                    self.current_video.unlink()
                except Exception:
                    pass

            # Also clean up extracted audio if exists
            if cleanup_files and self.current_video:
                audio_path = self.current_video.parent / f"{self.current_video.stem}_audio.wav"
                if audio_path.exists():
                    try:
                        audio_path.unlink()
                    except Exception:
                        pass

            self.current_video = None
            self.video_id = None
            self.is_processing = False
            self.processing_id = None
            self.transcriptions = []
            self.audio_duration = 0.0
            self.total_chunks = 0

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
        """Set the total audio duration."""
        with self._state_lock:
            self.audio_duration = duration

    def set_total_chunks(self, count: int) -> None:
        """Set the total number of chunks to process."""
        with self._state_lock:
            self.total_chunks = count

    def complete_task(self) -> None:
        """Mark the current task as completed."""
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
        """Check if the given video_id matches the current video."""
        with self._state_lock:
            return self.video_id == video_id


# Global instance
_state_manager = None


def get_state_manager() -> StateManager:
    """Get the singleton state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
