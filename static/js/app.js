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

        console.log('从后端收到的转写结果:', result);
        console.log('转写片段数量:', Object.keys(result).length);

        if (Object.keys(result).length > 0) {
            // 将字符串键转换为整数，确保正确的映射
            const formattedTranscripts = {};
            for (const key in result) {
                if (result.hasOwnProperty(key)) {
                    const segmentId = parseInt(key);
                    if (!isNaN(segmentId)) {
                        formattedTranscripts[segmentId] = result[key];
                    }
                    console.log(`处理片段 ${key} (${segmentId}): ${result[key]}`);
                }
            }
            transcripts = formattedTranscripts;
            isFirstTranscriptReceived = true;
            console.log('格式化后的转写结果:', transcripts);
            console.log('已准备好的片段:', Object.keys(transcripts));
        } else {
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }

    function updateTranscript(currentTime) {
        // 根据当前播放时间找到对应的10秒片段
        const segmentId = Math.floor(currentTime / 10);
        console.log(`当前时间: ${currentTime.toFixed(2)}s, 对应片段: ${segmentId}`);

        // 检查片段是否存在
        const availableSegments = Object.keys(transcripts).map(k => parseInt(k)).sort((a, b) => a - b);
        console.log('可用的片段:', availableSegments);
        console.log('片段存在性:', segmentId in transcripts, 'transcripts[segmentId]:', transcripts[segmentId]);

        if (transcripts[segmentId] !== undefined && transcripts[segmentId] !== null) {
            // 确保只显示文本内容
            let transcriptText = transcripts[segmentId];
            if (typeof transcriptText === 'object') {
                transcriptText = transcriptText.text || JSON.stringify(transcriptText);
            }
            transcriptContainer.innerHTML = transcriptText;
            console.log(`显示字幕: ${transcriptText}`);
        } else {
            console.log(`未找到片段 ${segmentId} 的字幕`);
            transcriptContainer.innerHTML = '';
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