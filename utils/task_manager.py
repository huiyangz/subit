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

    def start_new_task(self, task_id: str) -> None:
        """开始新任务，清理之前的任务"""
        self._reset()
        self.current_task_id = task_id

    def save_transcript(self, segment_id: int, text: str) -> None:
        """保存分片转录结果"""
        self.transcripts[segment_id] = text

    def get_transcript(self, segment_id: Optional[int] = None) -> Dict[str, str] | str | None:
        """获取指定分片或所有转写结果"""
        if segment_id is None:
            return self.transcripts
        return self.transcripts.get(segment_id, None)

    def is_processing_complete(self) -> bool:
        return self.processing_complete

    def mark_processing_complete(self) -> None:
        self.processing_complete = True

    def clear(self) -> None:
        """清理所有任务数据"""
        self._reset()