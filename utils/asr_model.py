"""ASR Model Wrapper using MLX and ModelScope

Uses mlx-audio-plus for fast inference on Apple Silicon.
Models are downloaded from ModelScope with local caching.
"""

import threading
from pathlib import Path
from typing import Optional
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
            self.model = None
            self._initialized = True

    def load_model(self) -> None:
        """Load ASR model using Model.from_pretrained."""
        with self._lock:
            if self.model is not None:
                return

            try:
                from mlx_audio.stt.models.funasr import Model

                # Download model from ModelScope (uses cache if available)
                self.model_path = Path(
                    snapshot_download(
                        config.MODEL_ID,
                        cache_dir=str(config.MODEL_CACHE_DIR),
                        revision="master",
                    )
                )

                # Load model from local path
                self.model = Model.from_pretrained(str(self.model_path))
            except ImportError as e:
                raise ImportError(
                    f"mlx_audio is not installed. "
                    f"Please install it using: uv pip install mlx-audio-plus"
                    f"\nOriginal error: {e}"
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
        if self.model is None:
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
        result = self.model.generate(audio_data)

        # Extract text from result
        # STTOutput object has a 'text' attribute
        if hasattr(result, "text"):
            return result.text
        elif isinstance(result, dict):
            return result.get("text", "")
        elif isinstance(result, str):
            return result
        elif isinstance(result, list) and len(result) > 0:
            if hasattr(result[0], "text"):
                return result[0].text
            elif isinstance(result[0], dict):
                return result[0].get("text", "")
            return str(result[0])
        else:
            return str(result)

    def cleanup(self) -> None:
        """Clean up model resources."""
        with self._lock:
            self.model = None
            self.model_path = None


def get_asr_model() -> ASRModel:
    """Get the singleton ASR model instance."""
    return ASRModel()


def cleanup_asr_model() -> None:
    """Cleanup the ASR model instance."""
    model = get_asr_model()
    model.cleanup()
