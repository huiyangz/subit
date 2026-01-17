"""Audio Processor for extracting and splitting audio from video"""

from pathlib import Path
from typing import Iterator, Tuple, Optional, Callable
import numpy as np
import subprocess
import logging

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioStreamCancelled(Exception):
    """Raised when audio streaming is cancelled."""
    pass


def get_audio_duration(video_path: Path) -> float:
    """Get duration of audio in a video file using ffprobe.

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


def stream_audio_chunks(
    video_path: Path,
    sample_rate: int = config.SAMPLE_RATE,
    chunk_duration: int = config.CHUNK_DURATION,
    cancelled_check: Optional[Callable[[], bool]] = None,
) -> Iterator[Tuple[np.ndarray, float, float]]:
    """Stream audio from video and yield chunks using ffmpeg.

    This uses ffmpeg to extract audio in chunks, avoiding loading the entire
    audio into memory at once.

    Args:
        video_path: Path to the video file
        sample_rate: Target sample rate
        chunk_duration: Duration of each chunk in seconds
        cancelled_check: Optional callback to check if operation iscancelled

    Yields:
        Tuples of (chunk_data, start_time, end_time)

    Raises:
        AudioStreamCancelled: If the streaming is cancelled
    """
    chunk_samples = chunk_duration * sample_rate
    bytes_per_sample = 4  # float32
    chunk_bytes = chunk_samples * bytes_per_sample

    cmd = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-vn",  # No video
        "-sn",  # No subtitles
        "-dn",  # No
        "-acodec",
        "pcm_f32le",  # 32-bit float PCM little-endian
        "-ar",
        str(sample_rate),
        "-ac",
        "1",  # Mono
        "-f",
        "f32le",  # Raw float32 output
        "-",  # Output to stdout
    ]

    process = None

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        chunk_index = 0
        buffer = bytearray()

        while True:
            # Check if cancelled
            if cancelled_check and cancelled_check():
                logger.info("Audio streaming cancelled")
                raise AudioStreamCancelled("Audio streaming was cancelled")

            # Read chunk bytes with timeout to allow cancellation checks
            try:
                import select

                # Use select to check if there's data available
                readable, _, _ = select.select([process.stdout], [], [], 0.1)

                if not readable:
                    # No data available, loop again to check cancellation
                    # Also check if process has ended
                    if process.poll() is not None:
                        # Process ended, process remaining buffer
                        if buffer:
                            samples = len(buffer) // bytes_per_sample
                            audio_data = np.frombuffer(buffer, dtype=np.float32)
                            start_time = chunk_index * chunk_duration
                            end_time = start_time + (samples / sample_rate)
                            yield (audio_data, start_time, end_time)
                        break
                    continue

                data = process.stdout.read(chunk_bytes)

            except (ImportError, AttributeError):
                # select not available (Windows), fall back to read
                data = process.stdout.read(chunk_bytes)

            if not data:
                # No more data, process remaining buffer
                if buffer:
                    samples = len(buffer) // bytes_per_sample
                    audio_data = np.frombuffer(buffer, dtype=np.float32)
                    start_time = chunk_index * chunk_duration
                    end_time = start_time + (samples / sample_rate)
                    yield (audio_data, start_time, end_time)
                break

            # Add to buffer
            buffer.extend(data)

            # While we have enough data for a full chunk, yield it
            while len(buffer) >= chunk_bytes:
                chunk_data = buffer[:chunk_bytes]
                del buffer[:chunk_bytes]

                audio_data = np.frombuffer(chunk_data, dtype=np.float32)
                start_time = chunk_index * chunk_duration
                end_time = start_time + chunk_duration
                yield (audio_data, start_time, end_time)
                chunk_index += 1

    except AudioStreamCancelled:
        raise
    except BrokenPipeError:
        # Can happen when file is deleted while reading
        if cancelled_check and cancelled_check():
            logger.info("Audio streaming cancelled due to file deletion")
            raise AudioStreamCancelled("Audio streaming was cancelled")
        else:
            logger.error(f"Broken pipe error while streaming audio from {video_path}")
            raise
    except Exception as e:
        logger.error(f"Failed to stream audio: {e}")
        raise
    finally:
        # Clean up process if it exists
        if process is not None:
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=1.0)
            except Exception as e:
                logger.debug(f"Error cleaning up ffmpeg process: {e}")


def process_video_audio(
    video_path: Path,
    sample_rate: int = config.SAMPLE_RATE,
    chunk_duration: int = config.CHUNK_DURATION,
) -> Tuple[list, float]:
    """Get duration and chunk count for a video file.

    This is a lightweight function that only calculates metadata,
    without actually loading audio data.

    Args:
        video_path: Path to the video file
        sample_rate: Target sample rate
        chunk_duration: Duration of each chunk in seconds

    Returns:
        Tuple of (total_chunks, total_duration)
    """
    duration = get_audio_duration(video_path)
    total_chunks = int(duration / chunk_duration) + 1
    return total_chunks, duration
