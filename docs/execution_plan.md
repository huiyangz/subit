# 视频转写服务执行计划

## 一、项目概述

本项目将创建一个基于 Flask 和 MLX 的视频音频转录服务，实现前端视频播放与后端实时语音转写功能。主要特点：

1. **前端**：视频播放器 + 上传按钮 + 播放/暂停控制 + 字幕显示
2. **后端**：Flask 服务，使用 ModelScope 下载 MLX 模型，支持音频分片处理
3. **技术栈**：Python, Flask, MLX, FFmpeg, ModelScope, mlx-audio-plus

## 二、目录结构

```
subit/
├── app.py                # Flask 应用主文件
├── requirements.txt      # Python 依赖列表
├── .env.example         # 环境变量模板
├── static/              # 静态资源
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── uploads/         # 上传视频存储目录
├── templates/           # HTML 模板
│   └── index.html
├── models/              # 模型文件目录
├── docs/               # 文档目录
│   └── execution_plan.md
├── tests/              # 测试文件目录
│   ├── test_api.py
│   └── test_integration.py
└── utils/               # 工具类
    ├── audio_utils.py   # 音频处理工具
    ├── model_utils.py   # 模型加载工具
    └── task_manager.py  # 任务管理工具
```

## 三、详细执行步骤

### 步骤 1: 环境与配置

1. **创建环境变量配置**:
   - 创建 `.env.example` 文件，包含以下配置项：
     ```env
     # Flask 配置
     FLASK_APP=app.py
     FLASK_ENV=development
     SECRET_KEY=your-secret-key-here

     # 目录配置
     UPLOAD_FOLDER=static/uploads
     MAX_CONTENT_LENGTH=524288000  # 500MB
     MODEL_DIR=models

     # 转写配置
     AUDIO_SEGMENT_DURATION=10  # 音频分片时长（秒）
     MAX_CONCURRENT_TRANSCRIPTS=1  # 最大并发转录任务数

     # MLX 配置
     MLX_DEVICE=metal  # Apple Silicon 优先使用 Metal 加速
     ```

2. **创建 `requirements.txt` 文件**:
   ```txt
   flask==2.3.3
   python-dotenv==1.0.0
   ffmpeg-python==0.2.0
   mlx-audio-plus==0.1.8
   requests>=2.31.0
   pydantic>=2.5.0
   modelscope>=1.14.0
   ```
   - 国内代理安装建议：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt`

3. **创建 `.gitignore` 文件**:
   ```gitignore
   __pycache__/
   *.pyc
   *.pyo
   *.pyd
   *.DS_Store
   venv/
   .env
   static/uploads/
   models/
   *.log
   *.tmp
   ```

### 步骤 2: 工具类开发

#### 2.1 模型下载与加载 (`utils/model_utils.py`)

```python
import os
import shutil
from modelscope import snapshot_download
from dotenv import load_dotenv
from mlx_audio_plus import ASRModel


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
            self.model = ASRModel.from_pretrained(model_dir)
            print("模型加载完成")

    def transcribe_audio(self, audio_path: str) -> str:
        """对单个音频文件进行转录"""
        if not self.model:
            raise ValueError("Model not loaded. Call download_and_load_model() first.")

        try:
            # 执行转写
            result = self.model.transcribe(audio_path)
            return result['text'] if isinstance(result, dict) else result
        except Exception as e:
            print(f"转写错误: {e}")
            return ""
```

#### 2.2 音频处理工具 (`utils/audio_utils.py`)

```python
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
```

#### 2.3 任务管理器 (`utils/task_manager.py`)

```python
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
```

### 步骤 3: Flask 后端服务 (`app.py`)

```python
import os
import uuid
from flask import Flask, render_template, request, jsonify, abort
from flask_cors import CORS
from dotenv import load_dotenv
from utils.audio_utils import AudioUtils
from utils.model_utils import ModelManager
from utils.task_manager import TaskManager
import threading

# 加载配置
load_dotenv()
app = Flask(__name__)
CORS(app)

# 配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 524288000))

# 初始化管理器
model_manager = ModelManager()
task_manager = TaskManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # 检查文件类型
    if not file.filename.endswith(('.mp4', '.mov', '.avi', '.mkv')):
        return jsonify({'error': 'Unsupported file format'}), 400

    # 清理之前的任务
    task_manager.clear()

    # 保存文件
    task_id = str(uuid.uuid4())
    filename = f"{task_id}_{file.filename}"
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(video_path)

    # 启动转写任务
    threading.Thread(
        target=_process_video,
        args=(video_path, task_id),
        daemon=True
    ).start()

    return jsonify({
        'message': 'File uploaded and processing started',
        'task_id': task_id
    })

def _process_video(video_path: str, task_id: str):
    """处理视频转写的后台任务"""
    task_manager.start_new_task(task_id)

    # 下载并加载模型
    model_manager.download_and_load_model()

    # 提取音频
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}.wav")
    AudioUtils.extract_audio(video_path, audio_path)

    # 分片处理
    segments_dir = os.path.join(app.config['UPLOAD_FOLDER'], task_id)
    segments = AudioUtils.split_audio(audio_path, segments_dir)

    # 转录每个分片
    for i, segment_path in enumerate(segments):
        transcript = model_manager.transcribe_audio(segment_path)
        task_manager.save_transcript(i, transcript)

    task_manager.mark_processing_complete()

@app.route('/api/transcript')
def get_transcript():
    transcript = task_manager.get_transcript()
    return jsonify(transcript)

@app.route('/api/transcript/<int:segment_id>')
def get_segment_transcript(segment_id):
    transcript = task_manager.get_transcript(segment_id)
    if transcript is None:
        abort(404)
    return jsonify({'segment': segment_id, 'text': transcript})

@app.route('/api/clear', methods=['POST'])
def clear_task():
    task_manager.clear()
    return jsonify({'message': 'Task cleared'})

@app.route('/api/status')
def get_status():
    return jsonify({
        'processing_complete': task_manager.is_processing_complete(),
        'segments': len(task_manager.get_transcript())
    })

if __name__ == '__main__':
    app.run(debug=True)
```

### 步骤 4: 前端页面开发

#### 4.1 HTML 结构 (`templates/index.html`)

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频转写服务</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="container">
        <video id="videoPlayer" muted>
            <source id="videoSource" src="" type="video/mp4">
        </video>

        <input type="file" id="videoUpload" accept="video/*" class="upload-btn">
        <button id="playPauseBtn" class="play-pause-btn">▶ 播放</button>

        <div id="transcriptContainer" class="transcript-container"></div>
    </div>

    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
</body>
</html>
```

#### 4.2 CSS 样式 (`static/css/style.css`)

```css
body, html {
    height: 100%;
    margin: 0;
    overflow: hidden;
}

.container {
    width: 100%;
    height: 100%;
    position: relative;
}

#videoPlayer {
    width: 100%;
    height: 100%;
    object-fit: contain;
}

.upload-btn {
    position: absolute;
    top: 20px;
    left: 20px;
    cursor: pointer;
    opacity: 0.8;
}

.upload-btn:hover {
    opacity: 1;
}

.play-pause-btn {
    position: absolute;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    padding: 12px 24px;
    font-size: 20px;
    border: none;
    border-radius: 20px;
    cursor: pointer;
    background-color: rgba(255, 0, 0, 0.8);
    color: white;
}

.play-pause-btn:hover {
    background-color: rgba(255, 0, 0, 1);
}

.transcript-container {
    position: absolute;
    bottom: 30px;
    left: 50%;
    transform: translateX(-50%);
    max-width: 80%;
    text-align: center;
    color: white;
    background: rgba(0, 0, 0, 0.8);
    padding: 15px;
    border-radius: 8px;
}
```

#### 4.3 JavaScript 逻辑 (`static/js/app.js`)

```javascript
document.addEventListener('DOMContentLoaded', () => {
    const videoPlayer = document.getElementById('videoPlayer');
    const videoSource = document.getElementById('videoSource');
    const videoUpload = document.getElementById('videoUpload');
    const playPauseBtn = document.getElementById('playPauseBtn');
    const transcriptContainer = document.getElementById('transcriptContainer');

    let transcripts = {};
    let isFirstTranscriptReceived = false;

    // 上传视频
    videoUpload.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            await uploadFile(file);
        }
    });

    // 播放/暂停按钮
    playPauseBtn.addEventListener('click', () => {
        if (videoPlayer.paused) {
            videoPlayer.play();
            playPauseBtn.innerHTML = '⏸ 暂停';
        } else {
            videoPlayer.pause();
            playPauseBtn.innerHTML = '▶ 播放';
        }
    });

    // 更新字幕
    videoPlayer.addEventListener('timeupdate', () => {
        const currentTime = Math.floor(videoPlayer.currentTime);
        updateTranscript(currentTime);
    });

    async function uploadFile(file) {
        // 清除当前会话
        await clearTask();

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        if (result.error) {
            alert(result.error);
            return;
        }

        // 等待第一个转录结果
        while (!isFirstTranscriptReceived) {
            await checkTranscriptProgress();
        }

        // 加载视频到播放器
        const videoURL = URL.createObjectURL(file);
        videoSource.src = videoURL;
        videoPlayer.load();
    }

    async function checkTranscriptProgress() {
        const response = await fetch('/api/transcript');
        const result = await response.json();

        if (Object.keys(result).length > 0) {
            transcripts = result;
            isFirstTranscriptReceived = true;
        } else {
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }

    function updateTranscript(currentTime) {
        const segmentId = Math.floor(currentTime / 10);
        if (transcripts[segmentId]) {
            transcriptContainer.innerHTML = transcripts[segmentId];
        }
    }

    async function clearTask() {
        await fetch('/api/clear', { method: 'POST' });
        isFirstTranscriptReceived = false;
        transcripts = {};
        transcriptContainer.innerHTML = '';
    }

    // 页面刷新前清理
    window.addEventListener('beforeunload', clearTask);
});
```

### 步骤 5: 测试与验证

1. **单元测试** (`tests/test_api.py`):
   - 测试基础 API 路由
   - 测试文件上传功能
   - 测试转写 API

2. **集成测试** (`tests/test_integration.py`):
   - 完整流程测试（上传 -> 转写 -> 播放 -> 字幕显示）
   - 视频切换测试
   - 并发控制测试

## 四、关键技术实现

### 1. 模型下载与管理

使用 ModelScope 下载指定 MLX 模型：

```python
from modelscope import snapshot_download
model_dir = snapshot_download('mlx-community/Fun-ASR-MLT-Nano-2512-8bit')
```

### 2. 音频分片处理

将大音频文件拆分为 10s 分片，避免内存溢出：

```python
segments = AudioUtils.split_audio(audio_path, segments_dir)
```

### 3. 单任务管理机制

确保服务一次只处理一个视频转写任务，避免内存占用过高：

```python
# 单例模式
class TaskManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 初始化...
```

### 4. 前端等待机制

前端等待第一个转写结果返回后再开始播放视频：

```javascript
while (!isFirstTranscriptReceived) {
    await checkTranscriptProgress();
}
```

## 五、部署建议

### 开发环境

```bash
# 使用 uv 创建虚拟环境
uv venv
source .venv/bin/activate

# 安装依赖，使用清华镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 启动服务
flask run
```

### 生产环境

1. 使用 Gunicorn 作为 WSGI 服务器
2. 配置 Nginx 反向代理
3. 设置适当的进程和线程数量，避免内存问题

## 六、性能优化建议

### 内存优化

1. **音频分片**: 默认 10s 分片，可根据内存情况调整
2. **模型复用**: 转写多个分片时复用已加载模型
3. **文件清理**: 处理完成后删除临时文件

### 速度优化

1. **Metal 加速**: 利用 Apple Silicon 的 GPU 加速 MLX 推理
2. **异步处理**: 使用多线程后台处理视频转写

### 错误处理

1. **转写重试**: 遇到错误时自动重试
2. **异常监控**: 记录详细的错误日志
3. **资源清理**: 异常情况下及时释放资源

## 七、后续扩展建议

1. 支持更多视频格式 (MKV, AVI, MOV)
2. 添加字幕下载功能 (SRT, VTT)
3. 支持多语言转录
4. 提供字幕编辑功能
5. 实现用户会话管理
6. 添加转写进度显示
