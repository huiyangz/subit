# Subit - 视频转写字幕工具

Subit是一个基于AI的视频转写工具，可以将视频文件转换为文本字幕。它使用MLX框架在Apple Silicon上进行高效的本地转录，支持多种视频格式。

## 功能特点

- 🎥 支持多种视频格式：MP4, MOV, AVI, MKV, WebM, FLV（不区分大小写）
- ⚡ 利用Apple Silicon的Metal加速进行高效转录
- 🔍 自动生成字幕并与视频播放同步
- 📁 简单易用的Web界面
- 🛡️ 安全的文件上传和处理机制
- 🧹 自动缓存管理，防止磁盘空间浪费

## 技术栈

- **后端**: Python, Flask, MLX, FFmpeg, ModelScope, mlx-audio-plus
- **前端**: HTML, JavaScript, 自定义CSS
- **模型**: mlx-community/Fun-ASR-MLT-Nano-2512-8bit

## 环境要求

- Apple Silicon Mac (推荐使用M1/M2/M3芯片)
- macOS 13.0+
- Python 3.9+
- FFmpeg
- uv (Python虚拟环境管理器)

## 安装步骤

1. **克隆仓库**:
   ```bash
   git clone https://github.com/huiyangz/subit.git
   cd subit
   ```

2. **使用uv创建并激活虚拟环境**:
   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. **使用uv安装依赖**:
   ```bash
   uv pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt 
   ```

4. **配置环境变量**:
   ```bash
   cp .env.example .env
   # 根据需要编辑 .env 文件
   ```

5. **安装FFmpeg**:
   ```bash
   brew install ffmpeg
   ```

## 运行方法

1. **启动服务器**：服务启动时会自动加载模型
   ```bash
   python app.py
   ```

2. **打开浏览器访问**:
   ```
   http://localhost:5000
   ```

## 使用说明

1. 点击"📁 上传视频"按钮上传视频文件
2. 等待视频处理完成
3. 点击底部的"▶ 播放"按钮开始视频播放
4. 字幕会根据视频播放时间自动同步显示在播放器上方
5. 上传新视频时系统会自动清理之前的缓存数据

## 核心技术特性

### 音频分片处理
系统自动将视频提取为音频，每10秒切割为一个分片，并行处理提高效率。

### 流式字幕更新
前端定期向后端获取最新的转写结果，确保字幕实时更新。

### 缓存管理策略
- 上传新视频时自动清理uploads目录中的旧文件
- 播放视频时清理除当前任务外的其他缓存数据
- 任务完成后自动清理临时文件

## 配置选项

可以通过.env文件修改以下配置：

- `SECRET_KEY`: Flask应用的密钥
- `UPLOAD_FOLDER`: 视频文件上传目录
- `MAX_CONTENT_LENGTH`: 最大上传文件大小（字节）
- `MODEL_DIR`: 模型文件存储目录
- `AUDIO_SEGMENT_DURATION`: 音频分片时长（秒）
- `MAX_CONCURRENT_TRANSCRIPTS`: 最大并发转录任务数
- `MLX_DEVICE`: MLX计算设备（metal或cpu）

## 项目结构

```
subit/
├── app.py                # Flask 应用主文件
├── .env                  # 环境变量配置
├── requirements.txt      # Python 依赖列表
├── static/               # 静态资源
│   ├── css/
│   │   └── style.css     # 自定义样式表
│   ├── js/
│   │   └── app.js        # 前端JavaScript逻辑
│   └── uploads/          # 临时文件存储目录
├── templates/            # HTML 模板
│   └── index.html        # 主页面模板
├── models/               # 模型文件目录
├── docs/                 # 文档目录
│   └── execution_plan.md # 执行计划文档
└── utils/                # 工具类
    ├── audio_utils.py    # 音频处理工具
    ├── model_utils.py    # 模型加载工具
    └── task_manager.py   # 任务管理工具
```

## API接口

### 上传视频
- `POST /upload` - 上传视频文件开始处理

### 获取转写结果
- `GET /api/transcript` - 获取所有分片的转写结果
- `GET /api/transcript/<segment_id>` - 获取指定分片的转写结果

### 任务管理
- `POST /api/clear` - 清除当前任务和所有缓存数据
- `POST /api/clear-cache` - 播放视频时清理其他缓存数据
- `GET /api/status` - 获取处理状态
- `GET /api/config` - 获取服务器配置信息

## 注意事项

- 首次运行时需要下载模型文件，可能需要一些时间
- 大文件上传可能需要较长的处理时间
- 建议上传小于1000MB的视频文件以获得最佳体验
- 处理过程中会消耗较多内存和CPU资源，建议关闭其他占用资源的应用
- 上传新视频时会自动重置前后端状态，避免并行处理冲突

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来帮助改进项目！