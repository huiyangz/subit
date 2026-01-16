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

# 初始化目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化管理器
model_manager = ModelManager()
task_manager = TaskManager()

# 添加锁以防止并行处理
import threading
process_lock = threading.Lock()

# 在启动服务器时就加载模型
print("服务启动时加载模型...")
try:
    model_manager.download_and_load_model()
except Exception as e:
    print(f"模型加载失败，将在首次使用时尝试加载: {e}")

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

    # 检查文件类型（不区分大小写）
    filename_lower = file.filename.lower()
    if not filename_lower.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv')):
        return jsonify({'error': 'Unsupported file format'}), 400

    # 彻底清理之前的所有任务数据
    print("收到新的视频上传请求，开始彻底清理所有缓存数据")

    # 先清理uploads目录中所有临时文件
    try:
        upload_dir = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                file_path = os.path.join(upload_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"已删除旧的临时文件: {file_path}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        print(f"已删除旧的临时目录: {file_path}")
                except Exception as e:
                    print(f"删除文件时出错 {file_path}: {e}")
    except Exception as e:
        print(f"清理uploads目录时出错: {e}")

    # 然后清理任务管理器状态
    task_manager.clear()

    # 保存文件
    task_id = str(uuid.uuid4())
    filename = f"{task_id}_{file.filename}"
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(video_path)

    # 启动转写任务（使用锁防止并行处理）
    threading.Thread(
        target=_process_video_safe,
        args=(video_path, task_id),
        daemon=True
    ).start()

    return jsonify({
        'message': 'File uploaded and processing started',
        'task_id': task_id
    })

def _process_video_safe(video_path: str, task_id: str):
    """安全处理视频转写的后台任务，使用锁防止并行处理"""
    with process_lock:
        # 首先检查是否存在正在处理的任务
        if hasattr(task_manager, 'is_processing') and task_manager.is_processing:
            print("已有任务在处理中，新任务将替代旧任务")
            task_manager.clear()

        try:
            # 设置处理中标记
            task_manager.is_processing = True
            _process_video(video_path, task_id)
        finally:
            # 清除处理中标记
            task_manager.is_processing = False

def _process_video(video_path: str, task_id: str):
    """处理视频转写的后台任务"""
    # 提取音频
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}.wav")
    # 分片处理
    segments_dir = os.path.join(app.config['UPLOAD_FOLDER'], task_id)

    # 初始化新任务，保存文件路径以用于后续清理
    task_manager.start_new_task(task_id, video_path, audio_path, segments_dir)

    # 如果模型未加载，尝试加载
    if not model_manager.model:
        model_manager.download_and_load_model()

    # 提取音频
    AudioUtils.extract_audio(video_path, audio_path)
    segments = AudioUtils.split_audio(audio_path, segments_dir)

    print(f"音频分片完成，共 {len(segments)} 个片段，每个大约 10 秒")

    # 转录每个分片
    for i, segment_path in enumerate(segments):
        print(f"正在转写分片 {i}")
        transcript = model_manager.transcribe_audio(segment_path)
        print(f"分片 {i} 转写完成，结果长度: {len(transcript)}")
        task_manager.save_transcript(i, transcript)
        print(f"已保存分片 {i} 的转写结果")

    print(f"总共有 {len(task_manager.transcripts)} 个分片的转写结果")
    task_manager.mark_processing_complete()
    print("转写全部完成")

@app.route('/api/transcript')
def get_transcript():
    transcripts = task_manager.get_transcript()
    print(f"API 请求: 共 {len(transcripts)} 个分片结果")
    return jsonify(transcripts)

@app.route('/api/transcript/<int:segment_id>')
def get_segment_transcript(segment_id):
    transcript = task_manager.get_transcript(segment_id)
    if transcript is None:
        abort(404)
    return jsonify({'segment': segment_id, 'text': transcript})

@app.route('/api/clear', methods=['POST'])
def clear_task():
    print("收到清理请求，开始彻底清理所有任务数据和缓存")

    # 清理任务数据
    task_manager.clear()

    # 清理uploads目录中所有临时文件
    try:
        upload_dir = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                file_path = os.path.join(upload_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"已删除临时文件: {file_path}")
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    print(f"已删除临时目录: {file_path}")
        print("所有缓存数据已清理完毕")
    except Exception as e:
        print(f"清理缓存时出错: {e}")

    return jsonify({'message': 'Task cleared and all cache removed'})

@app.route('/api/status')
def get_status():
    return jsonify({
        'processing_complete': task_manager.is_processing_complete(),
        'segments': len(task_manager.get_transcript())
    })

if __name__ == '__main__':
    app.run(debug=True)