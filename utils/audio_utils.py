import subprocess
import wave
import math
import os
from pathlib import Path


class AudioUtils:
    @staticmethod
    def extract_audio(video_path: str, audio_path: str) -> None:
        """从视频中提取音频为 PCM 格式"""
        command = [
            'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ac', '1',
            '-ar', '16000', audio_path, '-y'
        ]
        subprocess.run(command, check=True, capture_output=True)

    @staticmethod
    def split_audio(audio_path: str, output_dir: str, segment_duration: int = 10) -> list[str]:
        """按指定时长拆分音频文件"""
        os.makedirs(output_dir, exist_ok=True)

        with wave.open(audio_path, 'rb') as wf:
            sample_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            total_frames = wf.getnframes()

            segment_frames = int(sample_rate * segment_duration)
            num_segments = math.ceil(total_frames / segment_frames)

            segments = []
            for i in range(num_segments):
                start_frame = i * segment_frames
                wf.setpos(start_frame)
                frames = wf.readframes(segment_frames)

                segment_path = os.path.join(output_dir, f'segment_{i}.wav')
                with wave.open(segment_path, 'wb') as segment_wf:
                    segment_wf.setparams((num_channels, sample_width, sample_rate, 0, 'NONE', 'not compressed'))
                    segment_wf.writeframes(frames)
                segments.append(segment_path)

        return segments