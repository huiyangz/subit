"""ASR Model Wrapper using MLX and ModelScope

Uses mlx-audio-plus for fast inference on Apple Silicon.
Models are downloaded from ModelScope with local caching.
"""

import threading
from pathlib import Path
from typing import Optional, Dict
import numpy as np

from modelscope import snapshot_download
import config


class ASRModel:
    """ASR Model singleton wrapper."""

    _instance: Optional["ASRModel"] = None
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

            self.model_path: Optional[Path] = None
            self.pipeline = None
            self._initialized = True

    def load_model(self) -> None:
        """Load the ASR model from ModelScope or use cached version."""
        with self._lock:
            if self.pipeline is not None:
                return

            # Download model from ModelScope (uses cache if available)
            self.model_path = Path(
                snapshot_download(
                    config.MODEL_ID,
                    cache_dir=str(config.MODEL_CACHE_DIR),
                    revision="master",
                )
            )

            # Import mlx-audio-plus for inference
            try:
                from mlx_audio_plus import ASRPipeline

                self.pipeline = ASRPipeline(
                    str(self.model_path),
                    batch_size=1,
                )
            except ImportError:
                raise ImportError(
                    "mlx-audio-plus is not installed. "
                    "Please install it using: uv pip install mlx-audio-plus"
                )

    def transcribe(
        self, audio_data: np.ndarray, sample_rate: int = config.SAMPLE_RATE
    ) -> str:
        """Transcribe audio data to text.

        Args:
            audio_data: Audio data as numpy array (float32 or int16)
            sample_rate: Sample rate of the audio data

        Returns:
            Transcribed text string
        """
        if self.pipeline is None:
            self.load_model()

        # Ensure audio is float32 and normalize
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Resample if needed
        if sample_rate != config.SAMPLE_RATE:
            import librosa

            audio_data = librosa.resample(
                audio_data,
                orig_sr=sample_rate,
                target_sr=config.SAMPLE_RATE,
            )

        # Run inference
        result = self.pipeline.generate(audio_data)

        # Extract text from result
        if isinstance(result, dict):
            return result.get("text", "")
        elif isinstance(result, str):
            return result
        elif isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], dict):
                return result[0].get("text", "")
            return str(result[0])
        else:
            return str(result)

    def cleanup(self) -> None:
        """Clean up model resources."""
        with self._lock:
            self.pipeline = None
            self.model_path = None


def get_asr_model() -> ASRModel:
    """Get the singleton ASR model instance."""
    return ASRModel()


def cleanup_asr_model() -> None:
    """Cleanup the ASR model instance."""
    model = get_asr_model()
    model.cleanup()
