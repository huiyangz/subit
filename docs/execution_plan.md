# Subit - 视频语音转录服务执行计划

## 项目概述

使用Python + Flask构建一个视频语音转录服务，支持前端播放视频并同步显示AI生成的字幕。

- 前端：HTML + CSS + JavaScript（原生）
- 后端：Flask + MLX + ModelScope
- ASR模型：`mlx-community/Fun-ASR-MLT-Nano-2512-8bit`
- 音频处理库：`mlx-audio-plus`

## 项目结构

```
subit/
├── app.py                 # Flask主应用
├── config.py              # 配置文件
├── requirements.txt       # 依赖列表
├── pyproject.toml         # uv项目配置
├── docs/
│   ├── execution_plan.md  # 本执行计划
│   └── design_doc.md      # 设计文档
├── tests/
│   ├── __init__.py
│   └── test_app.py        # 应用测试
├── static/
│   ├── css/
│   │   └── style.css      # 前端样式
│   └── js/
│       └── app.js         # 前端逻辑
├── templates/
│   └── index.html         # 主页面
└── utils/
    ├── __init__.py
    ├── audio_processor.py # 音频分片处理
    ├── asr_model.py       # ASR模型封装
    └── state_manager.py   # 状态管理（防止并行）
```

## 详细执行步骤

### 步骤1：创建项目基础结构

1.1 创建目录结构
```bash
mkdir -p static/css static/js templates utils
```

1.2 创建 `pyproject.toml`
- 配置uv项目元数据
- 配置pip国内镜像源（阿里云/清华源）

1.3 创建 `requirements.txt`
```
flask>=3.0.0
modelscope>=1.12.0
mlx-audio-plus>=0.1.0
numpy>=1.24.0
librosa>=0.10.0
soundfile>=0.12.0
```

### 步骤2：实现后端核心模块

2.1 创建 `config.py`
- 定义配置常量：
  - MODEL_ID = "mlx-community/Fun-ASR-MLT-Nano-2512-8bit"
  - CHUNK_DURATION = 10  # 秒
  - UPLOAD_FOLDER = "uploads"
  - MODEL_CACHE_DIR = "models"
  - PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"

2.2 创建 `utils/state_manager.py`
- 实现单例模式管理全局状态
- 确保同时只处理一个视频
- 提供方法：
  - `reset_state()` - 重置所有状态
  - `is_processing()` - 检查是否正在处理
  - `set_processing(bool)` - 设置处理状态
  - `get_progress()` - 获取转录进度
  - `update_progress(dict)` - 更新进度
  - `get_transcriptions()` - 获取已转录文本
  - `add_transcription(dict)` - 添加转录结果
  - `get_current_video()` - 获取当前视频信息

2.3 创建 `utils/asr_model.py`
- 使用modelscope下载模型（自动检测本地缓存）
- 使用mlx-audio-plus进行推理
- 提供方法：
  - `load_model()` - 加载模型（单例）
  - `transcribe(audio_data)` - 推理单个音频片段
  - `cleanup()` - 清理模型资源

2.4 创建 `utils/audio_processor.py`
- 从视频提取音频
- 分片处理音频（可配置时长，默认10秒）
- 提供方法：
  - `extract_audio(video_path)` - 提取音频为numpy数组
  - `split_audio(audio_data, sample_rate, chunk_duration)` - 分片音频
  - `get_audio_duration(video_path)` - 获取视频时长

### 步骤3：实现Flask应用

3.1 创建 `app.py`
- 路由设计：
  - `/` - 主页面
  - `/upload` - 上传视频接口（POST）
  - `/transcribe` - 开始转录接口（POST）
  - `/progress` - 获取转录进度接口（GET/SSE）
  - `/transcriptions` - 获取字幕接口（GET）
  - `/reset` - 重置状态接口（POST）
- 实现防并发逻辑：
  - 使用state_manager确保单任务
  - 拒绝新请求直到当前任务完成

3.2 上传处理流程：
1. 接收视频文件，保存到uploads目录
2. 提取音频信息（时长、采样率）
3. 重置state_manager状态
4. 返回视频信息给前端

3.3 转录处理流程（后台任务）：
1. 加载ASR模型
2. 分片音频
3. 逐片调用ASR推理
4. 每完成一片，更新state_manager中的transcriptions和progress
5. 完成后标记处理完成

### 步骤4：实现前端

4.1 创建 `templates/index.html`
- 布局结构：
  ```
  <body>
    <div class="video-container">
      <div class="upload-button">左上角上传按钮</div>
      <video id="video-player">视频播放器</video>
      <div class="subtitle-area">字幕显示区域</div>
      <button class="play-pause-btn">播放/暂停按钮</button>
    </div>
  </body>
  ```

4.2 创建 `static/css/style.css`
- 样式要求：
  - video-container: 100vh高度，flex布局
  - video: height: 100%, width: auto, object-fit: contain
  - upload-button: 绝对定位，左上角，z-index高层级
  - subtitle-area: 视频下方，当前时间对应的字幕
  - play-pause-btn: 屏幕下方居中

4.3 创建 `static/js/app.js`
- 功能实现：
  - 上传视频：POST到/upload接口
  - 等待第一个转录结果：轮询/transcriptions
  - 视频加载后等待：暂停直到第一片转录完成
  - 播放控制：单个按钮切换播放/暂停状态
  - 字幕同步：监听timeupdate事件，查找当前时间对应的字幕
  - 进度显示：从/transcriptions获取实时更新
  - 换视频处理：调用/reset接口，清理前端状态

### 步骤5：创建设计文档

5.1 创建 `docs/design_doc.md`
- 技术选型说明
- 架构设计图
- 数据流图
- 接口文档
- 前后端交互时序图
- 性能优化考虑

### 步骤6：创建测试文件

6.1 创建 `tests/__init__.py`
- 空文件，标记为包

6.2 创建 `tests/test_app.py`
- 测试用例：
  - 测试Flask应用启动
  - 测试上传接口
  - 测试状态重置
  - 测试进度获取
  - （可选）模拟ASR推理测试

### 步骤7：创建启动脚本

7.1 创建 `run.sh`
```bash
#!/bin/bash
uv run python app.py
```

7.2 创建 `.env.example`
```bash
FLASK_ENV=development
FLASK_DEBUG=1
```

## 关键技术点说明

### 1. MLX模型加载
- 使用modelscope的snapshot_download下载模型到本地
- 支持本地缓存检测，避免重复下载
- 使用mlx-audio-plus进行快速推理

### 2. 音频分片处理
- 使用librosa或soundfile提取音频
- 按固定时长（10秒）分片
- 处理边界情况（最后一片可能不足10秒）
- 记录每片的时间偏移，用于字幕时间戳

### 3. 防并发机制
- 使用全局状态管理器
- Flask应用层面拒绝新请求
- 提供reset接口清理资源

### 4. 前端等待逻辑
- 上传后等待第一个转录完成再播放
- 使用setInterval轮询transcriptions接口
- 收到第一片数据后启用播放

### 5. 字幕同步
- 前端记录每片转录的时间范围
- 监听video.timeupdate事件
- 根据当前时间查找对应字幕

## 安装指南（用户自行执行）

```bash
# 使用uv创建环境
uv venv
source .venv/bin/activate

# 配置pip国内源（pyproject.toml中已配置）

# 安装依赖
uv pip install -r requirements.txt

# 启动服务
uv run python app.py
```

## 访问地址

服务启动后访问：http://localhost:5000
