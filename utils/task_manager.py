import os
import shutil
from typing import Dict, Optional, List


class TaskManager:
    """单例任务管理器，确保同时只处理一个任务"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._reset()
        return cls._instance

    def _reset(self):
        self.current_task_id: Optional[str] = None
        self.transcripts: Dict[int, str] = {}
        self.audio_segments: List[str] = []
        self.processing_complete: bool = False
        self.is_processing: bool = False
        self.video_path: Optional[str] = None
        self.audio_path: Optional[str] = None
        self.segments_dir: Optional[str] = None

    def start_new_task(self, task_id: str, video_path: str = None, audio_path: str = None, segments_dir: str = None) -> None:
        """开始新任务，清理之前的任务"""
        self._reset()
        self.current_task_id = task_id
        self.video_path = video_path
        self.audio_path = audio_path
        self.segments_dir = segments_dir

    def save_transcript(self, segment_id: int, text: str) -> None:
        """保存分片转录结果"""
        self.transcripts[segment_id] = text

    def get_transcript(self, segment_id: Optional[int] = None) -> Dict[str, str] | str | None:
        """获取指定分片或所有转写结果"""
        if segment_id is None:
            # 转换为字符串键以适应 JSON 序列化
            str_transcripts = {}
            for seg_id, text in self.transcripts.items():
                str_transcripts[str(seg_id)] = text
            return str_transcripts
        return self.transcripts.get(segment_id, None)

    def is_processing_complete(self) -> bool:
        return self.processing_complete

    def mark_processing_complete(self) -> None:
        self.processing_complete = True

    def clear(self) -> None:
        """清理所有任务数据和临时文件"""
        print("开始清理任务管理器中的数据")

        # 重置状态（不删除文件，文件在路由中已处理）
        self._reset()

        print("任务管理器已重置")