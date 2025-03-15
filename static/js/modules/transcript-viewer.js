/**
 * 轉錄文本瀏覽器模組
 * 提供轉錄文本的顯示、高亮和片段播放功能
 */

// 全域變數
let audioPlayer = null;
let segments = [];
let highlightClass = 'bg-light';
let activeSegment = null;

/**
 * 初始化轉錄文本瀏覽器
 */
function initTranscriptViewer() {
    // 獲取音訊播放器
    if (window.AudioPlayer) {
        audioPlayer = window.AudioPlayer;
    } else {
        console.error('無法找到 AudioPlayer 物件');
        return;
    }
    
    // 獲取所有片段元素
    segments = document.querySelectorAll('.segment');
    
    // 設置片段播放按鈕事件
    setupSegmentPlayButtons();
    
    // 設置文本片段點擊事件
    setupSegmentClickEvents();
    
    // 添加滾動到當前播放片段的功能
    setupScrollToCurrentSegment();
    
    // 導出高亮當前片段的函數到全域
    window.highlightCurrentSegment = highlightCurrentSegment;
}

/**
 * 設置片段播放按鈕事件
 */
function setupSegmentPlayButtons() {
    const playButtons = document.querySelectorAll('.play-segment');
    
    playButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const startTime = parseFloat(this.dataset.start);
            const endTime = parseFloat(this.dataset.end);
            
            // 使用 AudioPlayer 播放片段
            audioPlayer.playSegment(startTime, endTime);
            
            // 高亮顯示當前片段
            const segment = this.closest('.segment');
            highlightSegment(segment);
        });
    });
}

/**
 * 設置文本片段點擊事件
 */
function setupSegmentClickEvents() {
    segments.forEach(segment => {
        segment.addEventListener('click', function(e) {
            // 避免點擊按鈕時觸發
            if (e.target.closest('.play-segment')) {
                return;
            }
            
            const startTime = parseFloat(this.dataset.start);
            const endTime = parseFloat(this.dataset.end);
            
            // 使用 AudioPlayer 播放片段
            audioPlayer.playSegment(startTime, endTime);
            
            // 高亮顯示當前片段
            highlightSegment(this);
        });
    });
}

/**
 * 設置滾動到當前播放片段的功能
 */
function setupScrollToCurrentSegment() {
    const transcriptContainer = document.querySelector('.transcript-segments');
    if (!transcriptContainer) return;
    
    // 添加滾動事件監聽器，用於調整高亮狀態
    transcriptContainer.addEventListener('scroll', function() {
        if (activeSegment) {
            // 檢查活動片段是否在可視區域內
            const rect = activeSegment.getBoundingClientRect();
            const containerRect = transcriptContainer.getBoundingClientRect();
            
            const isVisible = (
                rect.top >= containerRect.top &&
                rect.bottom <= containerRect.bottom
            );
            
            // 如果不可見，取消高亮
            if (!isVisible) {
                unhighlightAllSegments();
                activeSegment = null;
            }
        }
    });
}

/**
 * 高亮顯示指定片段
 * @param {HTMLElement} segment - 要高亮的片段元素
 */
function highlightSegment(segment) {
    if (!segment) return;
    
    // 先取消所有片段的高亮
    unhighlightAllSegments();
    
    // 高亮當前片段
    segment.classList.add(highlightClass);
    activeSegment = segment;
    
    // 滾動到可視區域
    scrollToSegment(segment);
}

/**
 * 取消所有片段的高亮
 */
function unhighlightAllSegments() {
    segments.forEach(segment => {
        segment.classList.remove(highlightClass);
    });
}

/**
 * 滾動到指定片段
 * @param {HTMLElement} segment - 要滾動到的片段元素
 */
function scrollToSegment(segment) {
    const container = segment.closest('.transcript-segments');
    if (!container) return;
    
    const containerRect = container.getBoundingClientRect();
    const segmentRect = segment.getBoundingClientRect();
    
    // 檢查片段是否在可視區域內
    const isVisible = (
        segmentRect.top >= containerRect.top &&
        segmentRect.bottom <= containerRect.bottom
    );
    
    // 如果不在可視區域內，滾動到該片段
    if (!isVisible) {
        const scrollTop = segment.offsetTop - container.offsetTop - (container.clientHeight / 3);
        container.scrollTo({
            top: scrollTop,
            behavior: 'smooth'
        });
    }
}

/**
 * 根據當前播放時間高亮相應片段
 * @param {number} currentTime - 當前播放時間
 */
function highlightCurrentSegment(currentTime) {
    let matchedSegment = null;
    
    // 查找對應的片段
    segments.forEach(segment => {
        const startTime = parseFloat(segment.dataset.start);
        const endTime = parseFloat(segment.dataset.end);
        
        if (currentTime >= startTime && currentTime < endTime) {
            matchedSegment = segment;
        }
    });
    
    // 如果找到匹配的片段，高亮顯示它
    if (matchedSegment && matchedSegment !== activeSegment) {
        highlightSegment(matchedSegment);
    }
}

// 在文檔加載完成後初始化
document.addEventListener('DOMContentLoaded', function() {
    // 檢查是否存在轉錄文本片段
    const hasTranscript = document.querySelector('.transcript-segments');
    if (hasTranscript) {
        // 確保在音訊播放器初始化後再初始化轉錄文本瀏覽器
        if (window.AudioPlayer) {
            initTranscriptViewer();
        } else {
            // 如果音訊播放器尚未初始化，等待一個短時間後再試
            setTimeout(initTranscriptViewer, 500);
        }
    }
});