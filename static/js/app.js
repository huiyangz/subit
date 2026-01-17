// Subit Frontend Application

class SubitApp {
    constructor() {
        this.videoId = null;
        this.transcriptions = [];
        this.pollingInterval = null;
        this.isTranscribing = false;
        this.canPlay = false;
        this.currentTime = 0;

        this.videoPlayer = document.getElementById('video-player');
        this.uploadInput = document.getElementById('upload-input');
        this.uploadBtn = document.getElementById('upload-btn');
        this.playPauseBtn = document.getElementById('play-pause-btn');
        this.playIcon = document.getElementById('play-icon');
        this.pauseIcon = document.getElementById('pause-icon');
        this.subtitleText = document.getElementById('subtitle-text');
        this.statusText = document.getElementById('status-text');
        this.progressText = document.getElementById('progress-text');

        this.init();
    }

    init() {
        // Upload button click
        this.uploadBtn.addEventListener('click', () => {
            this.uploadInput.click();
        });

        // File input change
        this.uploadInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileUpload(e.target.files[0]);
            }
        });

        // Play/Pause button
        this.playPauseBtn.addEventListener('click', () => {
            if (this.videoPlayer.paused) {
                this.videoPlayer.play();
            } else {
                this.videoPlayer.pause();
            }
        });

        // Video events
        this.videoPlayer.addEventListener('play', () => this.updatePlayPauseButton(true));
        this.videoPlayer.addEventListener('pause', () => this.updatePlayPauseButton(false));
        this.videoPlayer.addEventListener('timeupdate', () => this.handleTimeUpdate());
        this.videoPlayer.addEventListener('ended', () => this.updatePlayPauseButton(false));
    }

    async handleFileUpload(file) {
        // Reset state
        await this.reset();

        // Create form data
        const formData = new FormData();
        formData.append('file', file);

        this.updateStatus('正在上传视频...', false);
        this.progressText.style.display = 'none';

        try {
            // Upload video
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = { success: false, ...await response.json() };

            if (!result.success) {
                throw new Error(result.message || '上传失败');
            }

            this.videoId = result.video_id;
            this.updateStatus('正在转录语音...', true);

            // Load video
            this.videoPlayer.src = `/uploads/${this.videoId}${this.getExtension(file.name)}`;
            await this.videoPlayer.load();

            // Start transcription
            await this.startTranscription();

        } catch (error) {
            console.error('Upload error:', error);
            this.updateStatus(`错误: ${error.message}`, false);
            this.playPauseBtn.disabled = true;
        }
    }

    getExtension(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        return `.${ext}`;
    }

    async startTranscription() {
        try {
            const response = await fetch('/transcribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video_id: this.videoId })
            });

            const result = { success: false, ...await response.json() };

            if (!result.success) {
                throw new Error(result.message || '转录启动失败');
            }

            this.isTranscribing = true;
            this.pollTranscriptions();

        } catch (error) {
            console.error('Transcription error:', error);
            this.updateStatus(`错误: ${error.message}`, false);
            this.playPauseBtn.disabled = true;
        }
    }

    pollTranscriptions() {
        this.pollingInterval = setInterval(async () => {
            try {
                const response = await fetch('/transcriptions');
                const data = await response.json();

                this.transcriptions = data.transcriptions;
                this.updateProgress(data.completed, data.total);

                // Wait for first transcription before enabling play
                if (this.transcriptions.length > 0 && !this.canPlay) {
                    this.canPlay = true;
                    this.playPauseBtn.disabled = false;
                    this.updateStatus('转录进行中，可以开始播放', true);
                    this.updateSubtitle(this.currentTime);
                }

                // Check if transcription is complete
                if (data.completed >= data.total && data.total > 0) {
                    this.stopPolling();
                    this.updateStatus('转录完成', false);
                    this.progressText.style.display = 'none';
                }

            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 500);
    }

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    handleTimeUpdate() {
        this.currentTime = this.videoPlayer.currentTime;
        if (this.canPlay) {
            this.updateSubtitle(this.currentTime);
        }
    }

    updateSubtitle(time) {
        const subtitle = this.transcriptions.find(
            t => time >= t.start_time && time < t.end_time
        );

        if (subtitle && subtitle.text) {
            this.subtitleText.textContent = subtitle.text;
            this.subtitleText.style.opacity = '1';
        } else {
            this.subtitleText.textContent = '';
        }
    }

    updatePlayPauseButton(isPlaying) {
        if (isPlaying) {
            this.playIcon.style.display = 'none';
            this.pauseIcon.style.display = 'block';
        } else {
            this.playIcon.style.display = 'block';
            this.pauseIcon.style.display = 'none';
        }
    }

    updateStatus(text, showProgress) {
        this.statusText.textContent = text;
        this.progressText.style.display = showProgress ? 'inline' : 'none';
    }

    updateProgress(completed, total) {
        if (total > 0) {
            const percent = Math.round((completed / total) * 100);
            this.progressText.textContent = `${percent}%`;
        }
    }

    async reset() {
        // Stop polling
        this.stopPolling();

        // Reset state
        this.videoId = null;
        this.transcriptions = [];
        this.isTranscribing = false;
        this.canPlay = false;
        this.currentTime = 0;

        // Reset UI
        this.videoPlayer.src = '';
        this.videoPlayer.pause();
        this.subtitleText.textContent = '';
        this.playPauseBtn.disabled = true;
        this.updatePlayPauseButton(false);
        this.updateStatus('准备上传视频', false);
        this.progressText.style.display = 'none';

        // Reset server state
        try {
            await fetch('/reset', { method: 'POST' });
        } catch (error) {
            console.error('Reset error:', error);
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.subitApp = new SubitApp();
});
