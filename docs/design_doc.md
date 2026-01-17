# Subit - 技术设计文档

## 1. 技术选型

### 1.1 前端技术栈
- **HTML5**: 原生语义化标签
- **CSS3**: Flexbox布局，自适应设计
- **JavaScript (ES6+)**: 原生JS，无框架依赖
- **Fetch API**: 与后端通信

### 1.2 后端技术栈
- **Flask**: 轻量级Web框架
- **ModelScope**: 模型下载和管理
- **MLX**: Apple Silicon加速推理
- **mlx-audio-plus**: MLX音频处理库
- **librosa/soundfile**: 音频提取和处理

### 1.3 ASR模型
- **模型**: `mlx-community/Fun-ASR-MLT-Nano-2512-8bit`
- **优势**:
  - 支持MLX加速，适合Mac设备
  - 模型大小适中（8bit量化）
  - 支持多语言识别

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ┌─────┐         ┌──────────────┐             │   │
│  │  │ CSS │────┐    │  JavaScript   │             │   │
│  │  └─────┘    │    │              │             │   │
│  │              ├───►              │──────┐      │   │
│  │  ┌─────┐    │    │              │      │      │   │
│  │  │ HTML│────┘    │              │      ▼      │   │
│  │  └─────┘         └──────────────┘   Fetch API   │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                               │
│                          ▼                               │
└──────────────────────────┼───────────────────────────────┘
                           │ HTTP
                           ▼
┌─────────────────────────────────────────────────────────┐
│                      Flask Server                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │              State Manager (Singleton)          │   │
│  │  - current_video    - is_processing              │   │
│  │  - transcriptions   - progress                   │   │
│  └─────────────────────────────────────────────────┘   │
│                           │                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │              API Routes                          │   │
│  │  /upload      /transcribe   /progress           │   │
│  │  /transcriptions  /reset                         │   │
│  └─────────────────────────────────────────────────┘   │
│                           │                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Audio Processor                      │   │
│  │  - extract_audio()                               │   │
│  │  - split_audio()                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                           │                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │              ASR Model                            │   │
│  │  - load_model()                                  │   │
│  │  - transcribe()                                  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │  ModelScope (Model Cache) │
              │  Fun-ASR-MLT-Nano-2512   │
              └──────────────────────────┘
```

### 2.2 数据流图

```
[1] 上传视频
User → (POST /upload) → Flask → 保存视频 → 提取音频信息 → 返回视频元数据

[2] 开始转录
User → (POST /transcribe) → Flask → 检查状态 → 开始后台任务
                                          ↓
                                  [后台任务]
                                  加载ASR模型
                                  提取完整音频
                                  分片处理
                                  ┌─────────────────┐
                                  │  For each chunk │
                                  │  1. ASR推理     │
                                  │  2. 保存结果    │
                                  │  3. 更新进度    │
                                  └─────────────────┘
                                          ↓
                                  标记完成

[3] 获取进度
User ← (GET /progress) ← Flask ← 返回当前处理百分比

[4] 获取字幕
User ← (GET /transcriptions) ← Flask ← 返回所有转录结果

[5] 重置状态
User → (POST /reset) → Flask → 清理中间文件 → 重置状态管理器
```

### 2.3 前后端交互时序图

```
用户              浏览器                    Flask服务器                  ASR模型
 │                │                          │                          │
 ├─ 点击上传按钮 ─┤                          │                          │
 │                ├─ POST /upload ──────────►│                          │
 │                │                          ├─ 保存视频               │
 │                │                          ├─ 提取音频信息           │
 │                │◄──── 视频元数据 ─────────┤                          │
 │                │                          │                          │
 ├─ 看到准备就绪 ─┤                          │                          │
 │                ├─ POST /transcribe ──────►│                          │
 │                │                          ├─ 检查状态               │
 │                │                          ├─ 启动后台任务           │
 │                │                          │   ├─ 加载模型 ────────►│
 │                │                          │   │◄──── 完成 ─────────┤
 │                │                          │   ├─ 提取音频           │
 │                │                          │   ├─ 分片处理           │
 │                │                          │   │                      │
 │                ├─ 轮询 /transcriptions ─►│   │                      │
 │                │◄─ [] (空) ───────────────┤   │                      │
 │                │                          │   ├─ 推理第1片 ────────►│
 │                │                          │   │◄──── 文本 ─────────┤
 │                │                          │   ├─ 保存结果           │
 │                │                          │   │                      │
 │                ├─ 轮询请求 ──────────────►│◄─ [{text, start, end}] ─┤
 │                │◄─ 第一片字幕 ────────────┤   │                      │
 │                │                          │   ├─ 推理第2片 ────────►│
 │                │                          │   │◄──── 文本 ─────────┤
 │                │                          │   ├─ 保存结果           │
 │                │                          │   │                      │
 │                │◄─ 显示字幕，允许播放 ─────┤   │                      │
 │                ├─ 点击播放 ───────────────►│   │                      │
 │                │                          │   └─ ...继续处理      │
 │                │◄─ 实时更新字幕 ─────────┤                          │
 │                │                          │                          │
```

## 3. 核心模块设计

### 3.1 StateManager (状态管理器)

**职责**: 管理全局状态，确保单任务处理

**数据结构**:
```python
class StateManager:
    _instance = None

    def __init__(self):
        self.current_video = None      # 当前视频文件路径
        self.is_processing = False     # 是否正在处理
        self.processing_id = None      # 当前处理任务的ID
        self.transcriptions = []       # 转录结果列表
        self.progress = 0              # 当前进度百分比
        self.audio_duration = 0        # 音频总时长
        self.total_chunks = 0          # 总分片数
        self.completed_chunks = 0       # 已完成分片数
```

**关键方法**:
- `reset_state()`: 清理所有状态，删除临时文件
- `can_start_new_task()`: 检查是否可以开始新任务
- `lock()`: 锁定状态，防止并发
- `unlock()`: 解锁状态

### 3.2 ASRModel (ASR模型封装)

**职责**: 管理模型加载和推理

**数据结构**:
```python
class ASRModel:
    _model = None
    _processor = None
    _model_loaded = False
```

**关键方法**:
- `load_model()`: 单例加载模型
  - 检查本地缓存
  - 如不存在，从ModelScope下载
  - 使用mlx加载模型权重
- `transcribe(audio_data, sample_rate)`: 推理
  - 预处理音频
  - 调用mlx-audio-plus推理
  - 后处理结果
- `cleanup()`: 释放模型内存

### 3.3 AudioProcessor (音频处理器)

**职责**: 从视频提取音频并分片

**关键方法**:
- `extract_audio(video_path)`:
  - 使用ffmpeg提取音频track
  - 转换为目标采样率
  - 返回numpy数组和采样率
- `split_audio(audio_data, sample_rate, chunk_duration)`:
  - 计算每片的样本数
  - 分割数组
  - 返回分片列表
- `get_audio_duration(video_path)`:
  - 使用ffprobe获取时长

## 4. API接口设计

### 4.1 POST /upload
上传视频文件

**Request**:
- Content-Type: multipart/form-data
- file: 视频文件

**Response**:
```json
{
  "success": true,
  "video_id": "uuid",
  "filename": "video.mp4",
  "duration": 120.5,
  "ready": true
}
```

### 4.2 POST /transcribe
开始转录任务

**Request**:
```json
{
  "video_id": "uuid"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Transcription started",
  "task_id": "task-uuid"
}
```

**Error Response** (当已有任务在处理时):
```json
{
  "success": false,
  "message": "Another task is in progress"
}
```

### 4.3 GET /progress
获取转录进度

**Response**:
```json
{
  "is_processing": true,
  "progress": 45,
  "completed_chunks": 12,
  "total_chunks": 24
}
```

### 4.4 GET /transcriptions
获取已转录的文本

**Response**:
```json
{
  "transcriptions": [
    {
      "index": 0,
      "text": "这是第一段文字",
      "start_time": 0.0,
      "end_time": 10.0
    },
    {
      "index": 1,
      "text": "这是第二段文字",
      "start_time": 10.0,
      "end_time": 20.0
    }
  ],
  "total": 24,
  "completed": 12
}
```

### 4.5 POST /reset
重置状态，清理资源

**Response**:
```json
{
  "success": true,
  "message": "State reset"
}
```

## 5. 前端设计

### 5.1 页面布局

```
┌─────────────────────────────────────┐
│ [上传]                          100vh
│                                     │
│                                     │
│         视频播放器 (height: 100%)   │
│                                     │
│         [当前字幕显示]              │
│                                     │
│                                     │
│         [播放/暂停]                 │
└─────────────────────────────────────┘
```

### 5.2 关键逻辑

**上传流程**:
1. 点击上传按钮，触发文件选择
2. 选择文件后，POST到/upload
3. 等待响应，显示"准备就绪"
4. 自动调用POST /transcribe

**等待播放流程**:
1. 转录开始后，禁用播放按钮
2. 启动setInterval轮询/transcriptions
3. 收到第一个结果后，启用播放按钮
4. 清除定时器，改用timeupdate同步

**字幕同步**:
1. 监听video.timeupdate事件
2. 获取当前播放时间 currentTime
3. 在transcriptions数组中查找：
   - start_time <= currentTime < end_time
4. 更新字幕显示区域

**播放/暂停**:
1. 单个按钮控制
2. 切换 video.play() / video.pause()
3. 更新按钮图标（▶/⏸）

**换视频/刷新**:
1. 触发前调用 POST /reset
2. 清空前端状态
3. 重新开始上传流程

## 6. 性能优化

### 6.1 内存管理
- 模型单例，避免重复加载
- 音频分片处理，避免一次性加载全部
- 及时释放临时音频数据

### 6.2 并发控制
- 使用状态锁，确保同一时间只有一个任务
- 拒绝新请求，返回明确的错误信息

### 6.3 前端优化
- 使用requestAnimationFrame优化UI更新
- 节流轮询请求（避免过于频繁）
- 使用WeakMap存储字幕数据

## 7. 错误处理

### 7.1 后端错误
- 模型加载失败：返回500错误
- 音频提取失败：返回400错误
- 并发请求：返回409错误

### 7.2 前端错误
- 网络错误：显示提示信息
- 视频格式不支持：提示用户
- 转录超时：提供重试选项

## 8. 安全考虑

### 8.1 文件上传
- 限制文件类型（视频格式）
- 限制文件大小
- 文件名处理（防止路径遍历）

### 8.2 资源清理
- 定期清理临时文件
- 提供reset接口主动清理
