import os
import shutil
from modelscope import snapshot_download
from dotenv import load_dotenv
from mlx_audio.stt.models.funasr import Model


class ModelManager:
    def __init__(self):
        load_dotenv()
        self.model_dir = os.getenv('MODEL_DIR', 'models')
        os.makedirs(self.model_dir, exist_ok=True)
        self.model = None
        self.model_name = 'mlx-community/Fun-ASR-MLT-Nano-2512-8bit'

    def download_and_load_model(self) -> None:
        """使用 ModelScope 下载模型并加载到内存"""
        if not self.model:
            print(f"开始下载模型: {self.model_name}")

            # 使用 ModelScope 下载模型
            model_dir = snapshot_download(
                self.model_name,
                cache_dir=self.model_dir
            )
            print(f"模型已下载到: {model_dir}")

            # 加载 MLX 模型
            print("开始加载模型...")
            self.model = Model.from_pretrained(model_dir)
            print("模型加载完成")

    def transcribe_audio(self, audio_path: str) -> str:
        """对单个音频文件进行转录"""
        if not self.model:
            raise ValueError("Model not loaded. Call download_and_load_model() first.")

        try:
            # 执行转写
            result = self.model.generate(audio_path)
            return result['text'] if isinstance(result, dict) else result
        except Exception as e:
            print(f"转写错误: {e}")
            return ""