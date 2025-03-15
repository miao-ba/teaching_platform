/**
 * 音訊處理狀態追蹤模組
 * 用於實時追蹤音訊檔案的處理狀態並更新使用者介面
 */

class AudioStatusTracker {
    /**
     * 初始化狀態追蹤器
     * @param {number} audioId - 音訊檔案 ID
     * @param {Object} options - 設定選項
     */
    constructor(audioId, options = {}) {
        // 基本參數
        this.audioId = audioId;
        this.statusUrl = options.statusUrl || `/audio/status/${audioId}/`;
        this.refreshInterval = options.refreshInterval || 5000; // 預設 5 秒
        this.maxAttempts = options.maxAttempts || 60; // 預設最多嘗試 60 次 (5 分鐘)
        this.attemptCount = 0;

        // 狀態顯示元素
        this.statusBadgeSelector = options.statusBadgeSelector || '.status-badge';
        this.statusMessageSelector = options.statusMessageSelector || '.status-message';
        this.progressBarSelector = options.progressBarSelector || '.progress-bar';
        this.containerSelector = options.containerSelector || '.transcript-container';
        
        // 回調函數
        this.onStatusChange = options.onStatusChange || this.defaultStatusChangeHandler;
        this.onComplete = options.onComplete || this.defaultCompleteHandler;
        this.onError = options.onError || this.defaultErrorHandler;
        
        // 狀態追蹤
        this.currentStatus = null;
        this.intervalId = null;
        this.statusClasses = {
            'pending': 'bg-warning',
            'processing': 'bg-info',
            'completed': 'bg-success',
            'failed': 'bg-danger'
        };
    }
    
    /**
     * 開始追蹤狀態
     */
    startTracking() {
        // 立即執行一次
        this.checkStatus();
        
        // 設定定期檢查
        this.intervalId = setInterval(() => {
            this.checkStatus();
        }, this.refreshInterval);
        
        console.log(`開始追蹤音訊 #${this.audioId} 的處理狀態，每 ${this.refreshInterval/1000} 秒檢查一次`);
    }
    
    /**
     * 停止追蹤狀態
     */
    stopTracking() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
            console.log(`停止追蹤音訊 #${this.audioId} 的處理狀態`);
        }
    }
    
    /**
     * 檢查處理狀態
     */
    checkStatus() {
        this.attemptCount++;
        
        // 如果超過最大嘗試次數，停止追蹤
        if (this.attemptCount > this.maxAttempts) {
            console.log(`已達最大嘗試次數 (${this.maxAttempts})，停止追蹤`);
            this.stopTracking();
            return;
        }
        
        // 發送 AJAX 請求
        fetch(this.statusUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP 錯誤: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // 處理回應資料
                this.handleStatusUpdate(data);
            })
            .catch(error => {
                console.error('獲取狀態時出錯:', error);
                this.onError(error);
            });
    }
    
    /**
     * 處理狀態更新
     * @param {Object} data - 狀態資料
     */
    handleStatusUpdate(data) {
        // 檢查狀態是否有變化
        const hasChanged = this.currentStatus !== data.status;
        this.currentStatus = data.status;
        
        // 更新 UI
        this.updateStatusUI(data);
        
        // 如果狀態有變化，觸發回調
        if (hasChanged) {
            this.onStatusChange(data);
        }
        
        // 如果處理已完成或失敗，停止追蹤
        if (data.status === 'completed' || data.status === 'failed') {
            this.stopTracking();
            
            if (data.status === 'completed') {
                this.onComplete(data);
            } else {
                this.onError(new Error(data.message || '處理失敗'));
            }
        }
    }
    
    /**
     * 更新狀態 UI
     * @param {Object} data - 狀態資料
     */
    updateStatusUI(data) {
        // 更新狀態標籤
        const statusBadge = document.querySelector(this.statusBadgeSelector);
        if (statusBadge) {
            // 移除所有狀態類別
            Object.values(this.statusClasses).forEach(cls => {
                statusBadge.classList.remove(cls);
            });
            
            // 添加當前狀態類別
            const statusClass = this.statusClasses[data.status] || 'bg-secondary';
            statusBadge.classList.add(statusClass);
            statusBadge.textContent = data.status_display;
        }
        
        // 更新狀態訊息
        const statusMessage = document.querySelector(this.statusMessageSelector);
        if (statusMessage && data.message) {
            statusMessage.textContent = data.message;
        }
        
        // 更新進度條
        const progressBar = document.querySelector(this.progressBarSelector);
        if (progressBar) {
            let progressValue = 0;
            
            switch (data.status) {
                case 'pending':
                    progressValue = 10;
                    break;
                case 'processing':
                    progressValue = 50;
                    break;
                case 'completed':
                    progressValue = 100;
                    break;
                case 'failed':
                    progressValue = 100;
                    break;
            }
            
            progressBar.style.width = `${progressValue}%`;
            progressBar.setAttribute('aria-valuenow', progressValue);
        }
    }
    
    /**
     * 預設狀態變化處理器
     * @param {Object} data - 狀態資料
     */
    defaultStatusChangeHandler(data) {
        console.log(`音訊 #${this.audioId} 狀態變更為: ${data.status_display}`);
    }
    
    /**
     * 預設完成處理器
     * @param {Object} data - 狀態資料
     */
    defaultCompleteHandler(data) {
        console.log(`音訊 #${this.audioId} 處理完成! 耗時: ${data.processing_time || '未知'} 秒`);
        
        // 如果當前頁面是詳情頁，則重新載入頁面以顯示完整內容
        const container = document.querySelector(this.containerSelector);
        if (container && container.classList.contains('processing')) {
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    }
    
    /**
     * 預設錯誤處理器
     * @param {Error} error - 錯誤物件
     */
    defaultErrorHandler(error) {
        console.error(`音訊處理出錯: ${error.message}`);
    }
}

// 全域初始化函數
function initAudioStatusTracker(audioId, options = {}) {
    if (!audioId) {
        console.error('初始化音訊狀態追蹤器失敗: 缺少音訊 ID');
        return null;
    }
    
    const tracker = new AudioStatusTracker(audioId, options);
    tracker.startTracking();
    return tracker;
}

// 匯出為全域物件
window.AudioStatusTracker = AudioStatusTracker;
window.initAudioStatusTracker = initAudioStatusTracker;