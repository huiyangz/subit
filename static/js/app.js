document.addEventListener('DOMContentLoaded', () => {
    const videoPlayer = document.getElementById('videoPlayer');
    const videoSource = document.getElementById('videoSource');
    const videoUpload = document.getElementById('videoUpload');
    const playPauseBtn = document.getElementById('playPauseBtn');
    const transcriptContainer = document.getElementById('transcriptContainer');

    let transcripts = {};
    let isFirstTranscriptReceived = false;

    // 上传视频
    videoUpload.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            await uploadFile(file);
        }
    });

    // 播放/暂停按钮
    playPauseBtn.addEventListener('click', () => {
        if (videoPlayer.paused) {
            videoPlayer.play();
            playPauseBtn.innerHTML = '⏸ 暂停';
        } else {
            videoPlayer.pause();
            playPauseBtn.innerHTML = '▶ 播放';
        }
    });

    // 更新字幕
    videoPlayer.addEventListener('timeupdate', () => {
        const currentTime = Math.floor(videoPlayer.currentTime);
        updateTranscript(currentTime);
    });

    async function uploadFile(file) {
        // 清除当前会话
        await clearTask();

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        if (result.error) {
            alert(result.error);
            return;
        }

        // 等待第一个转录结果
        while (!isFirstTranscriptReceived) {
            await checkTranscriptProgress();
        }

        // 加载视频到播放器
        const videoURL = URL.createObjectURL(file);
        videoSource.src = videoURL;
        videoPlayer.load();
    }

    async function checkTranscriptProgress() {
        const response = await fetch('/api/transcript');
        const result = await response.json();

        if (Object.keys(result).length > 0) {
            transcripts = result;
            isFirstTranscriptReceived = true;
        } else {
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }

    function updateTranscript(currentTime) {
        const segmentId = Math.floor(currentTime / 10);
        if (transcripts[segmentId]) {
            // 确保正确显示文本，防止[object Object]显示
            const transcriptText = typeof transcripts[segmentId] === 'string'
                ? transcripts[segmentId]
                : JSON.stringify(transcripts[segmentId]);
            transcriptContainer.innerHTML = transcriptText;
        }
    }

    async function clearTask() {
        await fetch('/api/clear', { method: 'POST' });
        isFirstTranscriptReceived = false;
        transcripts = {};
        transcriptContainer.innerHTML = '';
    }

    // 页面刷新前清理
    window.addEventListener('beforeunload', clearTask);
});