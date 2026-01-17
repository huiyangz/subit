"""Tests for Subit Flask Application"""

import pytest
from pathlib import Path
import tempfile
import numpy as np
import soundfile as sf

# Import the app and utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from utils.state_manager import get_state_manager


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def reset_state():
    """Reset the state manager before and after tests."""
    state = get_state_manager()
    state.reset_state(cleanup_files=False)
    yield
    state.reset_state(cleanup_files=False)


@pytest.fixture
def sample_video():
    """Create a sample video (audio) file for testing."""
    with tempfile.NamedTemporaryFile(
        suffix='.wav',
        dir=app.config['UPLOAD_FOLDER'],
        delete=False
    ) as f:
        # Create 5 seconds of silence audio
        audio_data = np.zeros(16000 * 5, dtype=np.float32)
        sf.write(f.name, audio_data, 16000)
        yield Path(f.name), open(f.name, 'rb')

    # Clean up
    Path(f.name).unlink(missing_ok=True)


class TestIndexRoute:
    """Tests for the index route."""

    def test_index_get(self, client):
        """Test GET request to index returns HTML."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'html' in response.data.lower()


class TestUploadRoute:
    """Tests for the upload route."""

    def test_upload_no_file(self, client, reset_state):
        """Test upload with no file."""
        response = client.post('/upload')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'No file' in data['message']

    def test_upload_empty_filename(self, client, reset_state):
        """Test upload with empty filename."""
        response = client.post(
            '/upload',
            data={'file': (open(__file__, 'rb'), '')},
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        assert 'No file selected' in response.get_json()['message']

    def test_upload_invalid_type(self, client, reset_state):
        """Test upload with invalid file type."""
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            f.write(b'not a video')
            f.flush()
            response = client.post(
                '/upload',
                data={'file': (open(f.name, 'rb'), 'test.txt')},
                content_type='multipart/form-data'
            )
            assert response.status_code == 400
            assert 'Invalid file type' in response.get_json()['message']


class TestTranscribeRoute:
    """Tests for the transcribe route."""

    def test_transcribe_no_video(self, client, reset_state):
        """Test transcribe without uploading video first."""
        response = client.post(
            '/transcribe',
            json={'video_id': 'non-existent'},
            content_type='application/json'
        )
        assert response.status_code == 400
        assert 'No video uploaded' in response.get.get_json()['message']


class TestProgressRoute:
    """Tests for the progress route."""

    def test_progress_get(self, client, reset_state):
        """Test GET request to progress."""
        response = client.get('/progress')
        assert response.status_code == 200
        data = response.get.get_json()
        assert 'is_processing' in data
        assert 'progress' in data
        assert 'completed_chunks' in data
        assert 'total_chunks' in data


class TestTranscriptionsRoute:
    """Tests for the transcriptions route."""

    def test_transcriptions_get(self, client, reset_state):
        """Test GET request to transcriptions."""
        response = client.get('/transcriptions')
        assert response.status_code == 200
        data = response.get.get_json()
        assert 'transcriptions' in data
        assert 'total' in data
        assert 'completed' in data
        assert isinstance(data['transcriptions'], list)


class TestResetRoute:
    """Tests for the reset route."""

    def test_reset_post(self, client, reset_state):
        """Test POST request to reset."""
        response = client.post('/reset')
        assert response.status_code == 200
        data = response.get.get_json()
        assert data['success'] is True
        assert data['message'] == 'State reset'


class TestStateManager:
    """Tests for the state manager."""

    def test_singleton(self):
        """Test that state manager is a singleton."""
        state1 = get_state_manager()
        state2 = get_state_manager()
        assert state1 is state2

    def test_can_start_new_task(self, reset_state):
        """Test can_start_new_task."""
        state = get_state_manager()
        assert state.can_start_new_task() is True

    def test_start_task(self, reset_state):
        """Test start_task."""
        state = get_state_manager()
        video_path = Path('/tmp/test_video.mp4')

        task_id = state.start_task(video_path, 'test-id')
        assert task_id is not None
        assert state.is_processing is True
        assert state.video_id == 'test-id'

    def test_start_task_while_processing(self, reset_state):
        """Test start_task while another task is running."""
        state = get_state_manager()
        video_path = Path('/tmp/test_video.mp4')

        # Start first task
        state.start_task(video_path, 'test-id-1')
        assert state.is_processing is True

        # Try to start second task
        task_id = state.start_task(video_path, 'test-id-2')
        assert task_id is None

    def test_add_transcription(self, reset_state):
        """Test add_transcription."""
        state = get_state_manager()
        state.add_transcription(0, "测试文本", 0.0, 10.0)

        trans = state.get_transcriptions()
        assert len(trans) == 1
        assert trans[0]['text'] == "测试文本"
        assert trans[0]['start_time'] == 0.0
        assert trans[0]['end_time'] == 10.0

    def test_progress(self, reset_state):
        """Test get_progress."""
        state = get_state_manager()
        state.set_total_chunks(10)
        state.add_transcription(0, "文本", 0.0, 10.0)
        state.add_transcription(1, "文本2", 10.0, 20.0)

        progress = state.get_progress()
        assert progress['completed_chunks'] == 2
        assert progress['total_chunks'] == 10
        assert progress['progress'] == 20

    def test_reset(self, reset_state):
        """Test reset_state."""
        state = get_state_manager()
        video_path = Path('/tmp/test_video.mp4')
        state.start_task(video_path, 'test-id')

        assert state.is_processing is True
        state.reset_state(cleanup_files=False)
        assert state.is_processing is False
        assert state.video_id is None
