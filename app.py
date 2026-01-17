"""Subit - Video Speech Transcription Service

Flask application for video upload with real-time ASR transcription.
"""

import os
import uuid
import threading
from pathlib import Path
from typing import Optional

from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

import config
from utils.state_manager import get_state_manager
from utils.audio_processor import (
    process_video_audio,
    get_audio_duration,
    stream_audio_chunks,
    AudioStreamCancelled,
)
from utils.asr_model import get_asr_model

app = Flask(__name__)

# Configure Flask
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = str(config.UPLOAD_FOLDER)
app.secret_key = os.getenv("SECRET_KEY", "subsub-secret-key-change-in-production")


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return Path(filename).suffix.lower() in config.ALLOWED_VIDEO_EXTENSIONS


def run_transcription_task(video_path: Path, video_id: str) -> None:
    """Run transcription task in background thread."""
    import traceback

    state = get_state_manager()

    try:
        # Get ASR model (already loaded at startup)
        asr_model = get_asr_model()

        # Get duration and chunk count (lightweight, doesn't load audio)
        total_chunks, duration = process_video_audio(video_path)

        # Update state with duration and total chunks
        state.set_audio_duration(duration)
        state.set_total_chunks(total_chunks)

        # Stream audio chunks and transcribe
        for i, (chunk, start_time, end_time) in enumerate(
            stream_audio_chunks(video_path, cancelled_check=state.is_cancelled)
        ):
            # Check if task was cancelled
            if state.is_cancelled():
                print("Transcription cancelled")
                return

            # Transcribe chunk
            text = asr_model.transcribe(chunk)

            # Add transcription to state
            state.add_transcription(i, text.strip(), start_time, end_time)

    except AudioStreamCancelled:
        print("Transcription cancelled")
    except Exception as e:
        if state.is_cancelled():
            print("Transcription cancelled")
        else:
            print(f"Error during transcription: {e}")
            traceback.print_exc()
    finally:
        # Mark task as completed
        state.complete_task()


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_video():
    """Upload a video file."""
    state = get_state_manager()

    # Cancel any existing transcription task
    if state.is_processing:
        state.cancel_task()

        # Wait for the old thread to complete (with longer timeout)
        # Need to wait for any GPU inference to complete
        old_thread = state.get_current_thread()
        if old_thread and old_thread.is_alive():
            old_thread.join(timeout=10.0)

    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify(
            {"success": False, "message": "Invalid file type"}
        ), 400

    # Generate unique filename
    video_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    ext = Path(filename).suffix
    safe_filename = f"{video_id}{ext}"
    save_path = config.UPLOAD_FOLDER / safe_filename

    # Save file
    file.save(str(save_path))

    # Get video duration
    duration = get_audio_duration(save_path)

    # Reset state and clean up old files (except the newly uploaded video)
    state.reset_state(cleanup_files=True, except_video=save_path)

    # Store video info in state
    state.current_video = save_path
    state.video_id = video_id
    state.audio_duration = duration

    return jsonify(
        {
            "success": True,
            "video_id": video_id,
            "filename": filename,
            "duration": duration,
            "ready": True,
        }
    )


@app.route("/transcribe", methods=["POST"])
def start_transcription():
    """Start transcription for uploaded video."""
    state = get_state_manager()

    # Check if a task is already running
    if not state.can_start_new_task():
        return jsonify(
            {"success": False, "message": "Another task is in progress"}
        ), 409

    data = request.get_json()
    video_id = data.get("video_id") if data else None

    # Validate video_id
    if video_id and not state.is_same_video(video_id):
        return jsonify({"success": False, "message": "Invalid video_id"}), 400

    if state.current_video is None:
        return jsonify(
            {"success": False, "message": "No video uploaded"}
        ), 400

    # Start the transcription task
    task_id = state.start_task(state.current_video, video_id or state.video_id)

    if task_id is None:
        return jsonify(
            {"success": False, "message": "Failed to start task"}
        ), 500

    # Run transcription in background thread
    thread = threading.Thread(
        target=run_transcription_task,
        args=(state.current_video, state.video_id),
        daemon=True,
    )
    state.set_current_thread(thread)
    thread.start()

    return jsonify(
        {
            "success": True,
            "message": "Transcription started",
            "task_id": task_id,
        }
    )


@app.route("/progress")
def get_progress():
    """Get current transcription progress."""
    state = get_state_manager()
    progress = state.get_progress()
    return jsonify(progress)


@app.route("/config")
def get_config():
    """Get client configuration."""
    return jsonify(
        {
            "max_file_size": config.MAX_CONTENT_LENGTH,
            "max_file_size_mb": config.MAX_CONTENT_LENGTH / 1024 / 1024,
        }
    )


@app.route("/transcriptions")
def get_transcriptions():
    """Get all transcriptions."""
    state = get_state_manager()
    transcriptions = state.get_transcriptions()

    return jsonify(
        {
            "transcriptions": transcriptions,
            "total": state.total_chunks,
            "completed": len(transcriptions),
        }
    )


@app.route("/reset", methods=["POST"])
def reset_state():
    """Reset the state and clean up resources."""
    state = get_state_manager()
    state.reset_state(cleanup_files=True)

    return jsonify({"success": True, "message": "State reset"})


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(config.UPLOAD_FOLDER, filename)


def initialize_model():
    """Load ASR model at startup."""
    print("Loading ASR model...")
    asr_model = get_asr_model()
    asr_model.load_model()
    print("ASR model loaded successfully!")


if __name__ == "__main__":
    # Load model before starting the server
    initialize_model()

    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
