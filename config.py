"""Configuration for Subit ASR Service"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# ASR Model Configuration
MODEL_ID = "mlx-community/Fun-ASR-MLT-Nano-2512-8bit"
CHUNK_DURATION = 10  # seconds
SAMPLE_RATE = 16000  # target sample rate for ASR

# Directory Configuration
UPLOAD_FOLDER = BASE_DIR / "uploads"
MODEL_CACHE_DIR = BASE_DIR / "models"
TEMP_DIR = BASE_DIR / "temp"

# Create directories if they don't exist
for dir_path in [UPLOAD_FOLDER, MODEL_CACHE_DIR, TEMP_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Flask Configuration
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

# File Upload Configuration
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

# Polling Configuration
POLL_INTERVAL = 500  # milliseconds
