# Subit - 视频语音转录服务

基于 MLX 的视频语音转录服务，专为 Apple Silicon 优化。使用 Fun-ASR 模型实现实时语音识别，支持流式音频处理，内存占用低。

## 功能特性

- 实时语音识别（ASR），使用 Fun-ASR-MLT-Nano 模型
- 流式音频处理，支持大视频文件（不一次性加载到内存）
- 支持多语言混合转录
- 上传新视频时自动取消旧任务
- 网页端字幕同步显示
- 视频播放控制

## 技术栈

- **后端**: Flask
- **语音识别**: MLX Audio + Fun-ASR-MLT-Nano 8bit 模型
- **音频处理**: FFmpeg（流式提取）
- **模型来源**: ModelScope
- **前端**: 原生 JavaScript + HTML5 Video

## 系统要求

- Apple Silicon (M1/M2/M3) Mac
- Python 3.10+
- FFmpeg（用于音频提取）
- MLX 框架

## 安装

### 1. 克隆项目

```bash
git clone https://github.com/huiyangz/subit.git
cd subit
```

### 2. 安装依赖

使用 uv：

```bash
uv pip install -r requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple 
```

### 3. 确认 FFmpeg 已安装

```bash
ffmpeg -version
ffprobe -version
```

如未安装，使用 Homebrew 安装：

```bash
brew install ffmpeg
```

## 配置

编辑 `config.py` 修改配置：

```python
# ASR 模型 ID
MODEL_ID = "mlx-community/Fun-ASR-MLT-Nano-2512-8bit"

# 音频分块时长（秒）
CHUNK_DURATION = 10

# 目标采样率
SAMPLE_RATE = 16000

# 最大上传文件大小（字节）
MAX_CONTENT_LENGTH = 1000 * 1024 * 1024  # 1000MB

# Flask 配置
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
```

## 运行

```bash
python app.py
```

或使用启动脚本：

```bash
./run.sh
```

启动后访问 http://localhost:5000

## 使用方法

1. 点击左上角上传按钮选择视频文件
2. 等待转录完成（可随时开始播放）
3. 使用底部播放按钮控制视频
4. 字幕会根据播放时间自动显示

## API 接口

| 接口 | 方法 | 说明 |
|--------|------|------|
| `/` | GET | 主页 |
| `/upload` | POST | 上传视频文件 |
| `/transcribe` | POST | 开始转录 |
| `/transcriptions` | GET | 获取转录结果 |
| `/progress` | GET | 获取转录进度 |
| `/config` | GET | 获取客户端配置 |
| `/reset` | POST | 重置状态 |
| `/uploads/<filename>` | GET | 获取上传的视频 |

## 项目结构

```
subit/
├── app.py                 # Flask 主应用
├── config.py              # 配置文件
├── requirements.txt        # Python 依赖
├── run.sh                 # 启动脚本
├── static/                # 静态资源
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── templates/
│   └── index.html       # 主页面
├── uploads/               # 上传的视频（自动创建）
├── models/                # 模型缓存（自动创建）
├── temp/                 # 临时文件（自动创建）
└── utils/                 # 工具模块
    ├── audio_processor.py   # 音频处理
    ├── asr_model.py       # ASR 模型封装
    └── state_manager.py   # 状态管理
```

## 依赖项

- `flask>=3.0.0` - Web 框架
- `modelscope>=1.12.0` - 模型下载
- `mlx-audio-plus>=0.1.0` - MLX 音频处理
- `numpy>=1.24.0` - 数值计算
- `librosa>=0.10.0` - 音频处理（备用）
- `soundfile>=0.12.0` - 音频读写

## 许可证

MIT License
