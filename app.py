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