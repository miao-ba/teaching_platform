/**
 * 音訊播放器模組
 * 提供進階的音訊控制功能，包括播放、暫停、音量控制、速度控制和片段播放
 */

// 播放器狀態和元素引用
let audioElement = null;
let playPauseButton = null;
let progressBar = null;
let progressContainer = null;
let currentTimeDisplay = null;
let totalTimeDisplay = null;
let volumeSlider = null;
let volumeToggle = null;
let speedSelector = null;
let isInitialized = false;

// 當前播放片段的信息
let currentSegment = null;

/**
 * 初始化音訊播放器
 * @param {string} audioElementId - 音訊元素的ID
 * @param {string} containerId - 播放器容器的ID (可選)
 */
function initAudioPlayer(audioElementId = 'audio-player', containerId = 'audio-player-container') {
    // 如果已經初始化，則不再重複
    if (isInitialized) return;
    
    // 獲取音訊元素
    audioElement = document.getElementById(audioElementId);
    if (!audioElement) {
        console.error('音訊元素未找到:', audioElementId);
        return;
    }
    
    // 獲取容器元素
    const container = document.getElementById(containerId) || audioElement.closest('.audio-player-card');
    if (!container) {
        console.error('播放器容器未找到');
        return;
    }
    
    // 獲取控制元素
    playPauseButton = container.querySelector('.btn-play-pause');
    progressBar = container.querySelector('.progress-bar');
    progressContainer = container.querySelector('.audio-progress');
    currentTimeDisplay = container.querySelector('.time-current');
    totalTimeDisplay = container.querySelector('.time-total');
    volumeSlider = container.querySelector('.volume-slider');
    volumeToggle = container.querySelector('.volume-toggle');
    speedSelector = container.querySelector('.playback-speed');
    
    // 設置事件監聽器
    setupEventListeners();
    
    // 顯示音訊總時長
    audioElement.addEventListener('loadedmetadata', updateTotalTime);
    // 如果音訊已經加載，則立即更新總時長
    if (audioElement.readyState >= 2) {
        updateTotalTime();
    }
    
    isInitialized = true;
    console.log('音訊播放器初始化完成');
}

/**
 * 設置播放器的事件監聽器
 */
function setupEventListeners() {
    // 播放/暫停按鈕
    if (playPauseButton) {
        playPauseButton.addEventListener('click', togglePlay);
    }
    
    // 音訊時間更新
    audioElement.addEventListener('timeupdate', updateProgress);
    
    // 進度條點擊
    if (progressContainer) {
        progressContainer.addEventListener('click', setProgress);
    }
    
    // 音量控制
    if (volumeSlider) {
        volumeSlider.addEventListener('input', setVolume);
    }
    
    // 音量開關
    if (volumeToggle) {
        volumeToggle.addEventListener('click', toggleMute);
    }
    
    // 播放速度控制
    if (speedSelector) {
        speedSelector.addEventListener('change', setPlaybackSpeed);
    }
    
    // 播放結束
    audioElement.addEventListener('ended', handlePlaybackEnd);
    
    // 空格鍵控制播放/暫停
    document.addEventListener('keydown', function(e) {
        // 只有當焦點不在表單控制項上時才觸發
        if (e.code === 'Space' && 
            !['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(document.activeElement.tagName)) {
            e.preventDefault();
            togglePlay();
        }
    });
}

/**
 * 切換播放/暫停狀態
 */
function togglePlay() {
    if (audioElement.paused) {
        audioElement.play()
            .then(() => {
                playPauseButton.innerHTML = '<i class="bi bi-pause-fill"></i>';
            })
            .catch(error => {
                console.error('播放失敗:', error);
            });
    } else {
        audioElement.pause();
        playPauseButton.innerHTML = '<i class="bi bi-play-fill"></i>';
    }
}

/**
 * 更新進度條和當前時間顯示
 */
function updateProgress() {
    if (!audioElement || !progressBar || !currentTimeDisplay) return;
    
    const currentTime = audioElement.currentTime;
    const duration = audioElement.duration || 0;
    
    // 更新進度條
    if (duration > 0) {
        const progressPercent = (currentTime / duration) * 100;
        progressBar.style.width = `${progressPercent}%`;
    } else {
        progressBar.style.width = '0%';
    }
    
    // 更新當前時間顯示
    currentTimeDisplay.textContent = formatTime(currentTime);
    
    // 如果正在播放片段，檢查是否需要停止
    if (currentSegment && currentTime >= currentSegment.end) {
        audioElement.pause();
        playPauseButton.innerHTML = '<i class="bi bi-play-fill"></i>';
        currentSegment = null;
    }
    
    // 檢查是否需要高亮顯示當前片段
    if (window.highlightCurrentSegment) {
        window.highlightCurrentSegment(currentTime);
    }
}

/**
 * 根據點擊位置設置播放進度
 * @param {Event} e - 點擊事件
 */
function setProgress(e) {
    if (!audioElement || !progressContainer) return;
    
    const duration = audioElement.duration;
    if (!duration) return;
    
    const clickPosition = e.offsetX;
    const containerWidth = progressContainer.clientWidth;
    const seekTime = (clickPosition / containerWidth) * duration;
    
    audioElement.currentTime = seekTime;
}

/**
 * 更新總時長顯示
 */
function updateTotalTime() {
    if (!audioElement || !totalTimeDisplay) return;
    
    const duration = audioElement.duration || 0;
    totalTimeDisplay.textContent = formatTime(duration);
}

/**
 * 設置音量
 */
function setVolume() {
    if (!audioElement || !volumeSlider || !volumeToggle) return;
    
    const volume = volumeSlider.value / 100;
    audioElement.volume = volume;
    
    // 更新音量圖標
    updateVolumeIcon(volume);
}

/**
 * 切換靜音狀態
 */
function toggleMute() {
    if (!audioElement || !volumeSlider || !volumeToggle) return;
    
    if (audioElement.volume > 0) {
        // 保存當前音量值
        audioElement.dataset.previousVolume = audioElement.volume;
        audioElement.volume = 0;
        volumeSlider.value = 0;
        volumeToggle.innerHTML = '<i class="bi bi-volume-mute"></i>';
    } else {
        // 恢復先前的音量值或預設為 0.5
        const previousVolume = audioElement.dataset.previousVolume || 0.5;
        audioElement.volume = previousVolume;
        volumeSlider.value = previousVolume * 100;
        updateVolumeIcon(previousVolume);
    }
}

/**
 * 更新音量圖標
 * @param {number} volume - 音量值 (0-1)
 */
function updateVolumeIcon(volume) {
    if (!volumeToggle) return;
    
    if (volume <= 0) {
        volumeToggle.innerHTML = '<i class="bi bi-volume-mute"></i>';
    } else if (volume < 0.5) {
        volumeToggle.innerHTML = '<i class="bi bi-volume-down"></i>';
    } else {
        volumeToggle.innerHTML = '<i class="bi bi-volume-up"></i>';
    }
}

/**
 * 設置播放速度
 */
function setPlaybackSpeed() {
    if (!audioElement || !speedSelector) return;
    
    const speed = parseFloat(speedSelector.value);
    audioElement.playbackRate = speed;
}

/**
 * 處理播放結束事件
 */
function handlePlaybackEnd() {
    if (!playPauseButton) return;
    
    playPauseButton.innerHTML = '<i class="bi bi-play-fill"></i>';
    currentSegment = null;
}

/**
 * 播放特定片段
 * @param {number} startTime - 開始時間 (秒)
 * @param {number} endTime - 結束時間 (秒)
 */
function playSegment(startTime, endTime) {
    if (!audioElement || !playPauseButton) return;
    
    // 設置片段信息
    currentSegment = {
        start: startTime,
        end: endTime
    };
    
    // 設置播放位置
    audioElement.currentTime = startTime;
    
    // 開始播放
    audioElement.play()
        .then(() => {
            playPauseButton.innerHTML = '<i class="bi bi-pause-fill"></i>';
        })
        .catch(error => {
            console.error('播放失敗:', error);
        });
}

/**
 * 格式化時間為 HH:MM:SS 格式
 * @param {number} seconds - 時間秒數
 * @returns {string} 格式化後的時間字符串
 */
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '00:00:00';
    
    seconds = Math.floor(seconds);
    const hours = Math.floor(seconds / 3600);
    seconds %= 3600;
    const minutes = Math.floor(seconds / 60);
    seconds %= 60;
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// 導出全局方法
window.AudioPlayer = {
    init: initAudioPlayer,
    play: () => {
        if (audioElement) audioElement.play();
    },
    pause: () => {
        if (audioElement) audioElement.pause();
    },
    seek: (time) => {
        if (audioElement) audioElement.currentTime = time;
    },
    setVolume: (volume) => {
        if (audioElement) {
            audioElement.volume = volume;
            if (volumeSlider) volumeSlider.value = volume * 100;
            updateVolumeIcon(volume);
        }
    },
    setSpeed: (speed) => {
        if (audioElement) {
            audioElement.playbackRate = speed;
            if (speedSelector) speedSelector.value = speed;
        }
    },
    playSegment: playSegment
};

// 在文檔加載完成後自動初始化
document.addEventListener('DOMContentLoaded', function() {
    initAudioPlayer();
});