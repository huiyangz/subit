"""Audio Processor for extracting and splitting audio from video"""

from pathlib import Path
from typing import List, Tuple
import numpy as np
import subprocess
import soundfile as sf
import logging

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_audio_duration(video_path: Path) -> float:
    """Get the duration of audio in a video file using ffprobe.

    Args:
        video_path: Path to the video file

    Returns:
        Duration in seconds
    """
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Failed to get audio duration: {e}")
    return 0.0


def extract_audio(video_path: Path, sample_rate: int = config.SAMPLE_RATE) -> Tuple[np.ndarray, int]:
    """Extract audio from video file.

    Args:
        video_path: Path to the video file
        sample_rate: Target sample rate

    Returns:
        Tuple of (audio_data as numpy array, sample_rate)
    """
    # First try using librosa which can handle many formats
    try:
        import librosa

        audio_data, sr = librosa.load(
            str(video_path), sr=sample_rate, mono=True
        )
        return audio_data, sample_rate
    except Exception as e:
        logger.warning(f"librosa extraction failed: {e}, trying ffmpeg...")

    # Fallback to using ffmpeg + soundfile
    temp_audio = config.TEMP_DIR / f"{video_path.stem}_extracted.wav"

    try:
        # Extract audio using ffmpeg
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-i",
            str(video_path),
            "-vn",  # No video
            "-acodec",
            "pcm_s16le",  # 16-bit PCM
            "-ar",
            str(sample_rate),
            "-ac",
            "1",  # Mono
            str(temp_audio),
        ]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg extraction failed: {result.stderr.decode()}")

        # Load the extracted audio
        audio_data, sr = sf.read(str(temp_audio))
        audio_data = audio_data.astype(np.float32)

        # Clean up temp file
        if temp_audio.exists():
            temp_audio.unlink()

        return audio_data, sr

    except Exception as e:
        # Clean up temp file if it exists
        if temp_audio.exists():
            temp_audio.unlink()
        raise RuntimeError(f"Failed to extract audio: {e}")


def split_audio(
    audio_data: np.ndarray,
    sample_rate: int,
    chunk_duration: int = config.CHUNK_DURATION,
) -> List[Tuple[np.ndarray, float, float]]:
    """Split audio into chunks.

    Args:
        audio_data: Audio data as numpy array
        sample_rate: Sample rate of the audio
        chunk_duration: Duration of each chunk in seconds

    Returns:
        List of tuples (chunk_data, start_time, end_time)
    """
    chunk_samples = chunk_duration * sample_rate
    total_samples = len(audio_data)
    chunks = []

    for i in range(0, total_samples, chunk_samples):
        chunk_end = min(i + chunk_samples, total_samples)
        chunk = audio_data[i:chunk_end]

        start_time = i / sample_rate
        end_time = chunk_end / sample_rate

        chunks.append((chunk, start_time, end_time))

    return chunks


def process_video_audio(
    video_path: Path,
    sample_rate: int = config.SAMPLE_RATE,
    chunk_duration: int = config.CHUNK_DURATION,
) -> Tuple[List[Tuple[np.ndarray, float, float]], float]:
    """Extract audio from video and split into chunks.

    Args:
        video_path: Path to the video file
        sample_rate: Target sample rate
        chunk_duration: Duration of each chunk in seconds

    Returns:
        Tuple of (list of chunks, total duration)
    """
    duration = get_audio_duration(video_path)
    audio_data, sr = extract_audio(video_path, sample_rate)
    chunks = split_audio(audio_data, sr, chunk_duration)

    return chunks, duration
