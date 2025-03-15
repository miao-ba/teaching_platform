/**
 * 教學語音處理平台主要JavaScript功能
 * 提供基本的UI交互、主題切換和各種通用功能
 */

// 頁面載入時初始化所有功能
document.addEventListener('DOMContentLoaded', function() {
    // 初始化側邊欄切換功能
    initSidebar();
    
    // 初始化工具提示
    initTooltips();
    
    // 初始化主題切換
    initThemeToggle();
    
    // 自動消失的警告訊息
    initAlertDismiss();
});

/**
 * 側邊欄切換功能
 * 控制側邊欄的顯示/隱藏和行動裝置適配
 */
function initSidebar() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('sidebar-collapsed');
            document.querySelector('.content-wrapper').classList.toggle('content-wrapper-expanded');
        });
    }
    
    // 在行動裝置上的側邊欄顯示/隱藏
    const mobileToggle = document.getElementById('mobile-sidebar-toggle');
    if (mobileToggle) {
        mobileToggle.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('sidebar-mobile-show');
        });
    }
}

/**
 * 工具提示初始化
 * 使用Bootstrap的Tooltip功能
 */
function initTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
}

/**
 * 主題切換功能
 * 實現深色模式和淺色模式的切換
 */
function initThemeToggle() {
    // 獲取主題切換按鈕
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;
    
    // 檢查本地存儲的主題偏好
    const savedTheme = localStorage.getItem('theme');
    
    // 根據存儲的主題偏好或系統偏好設置初始主題
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
        if (savedTheme === 'dark') {
            themeToggle.checked = true;
        }
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        // 如果未設置偏好但系統使用深色模式，則使用深色主題
        document.documentElement.setAttribute('data-theme', 'dark');
        themeToggle.checked = true;
    }
    
    // 監聽主題切換事件
    themeToggle.addEventListener('change', function() {
        document.documentElement.classList.add('theme-changing');
        
        setTimeout(() => {
            if (this.checked) {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
            }
            
            setTimeout(() => {
                document.documentElement.classList.remove('theme-changing');
            }, 300);
        }, 150);
    });
    
    // 監聽系統主題變化
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            if (!localStorage.getItem('theme')) {
                if (e.matches) {
                    document.documentElement.setAttribute('data-theme', 'dark');
                    themeToggle.checked = true;
                } else {
                    document.documentElement.setAttribute('data-theme', 'light');
                    themeToggle.checked = false;
                }
            }
        });
    }
}

/**
 * 警告訊息自動消失
 * 控制Bootstrap的alert元素自動淡出
 */
function initAlertDismiss() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

/**
 * 通用輔助函數
 */

// 格式化時間為時:分:秒格式
function formatDuration(seconds) {
    if (!seconds) return '00:00:00';
    
    const hours = Math.floor(seconds / 3600);
    seconds %= 3600;
    const minutes = Math.floor(seconds / 60);
    seconds = Math.floor(seconds % 60);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// 格式化時間為分:秒格式
function formatTimestamp(seconds) {
    if (!seconds) return '00:00';
    
    const minutes = Math.floor(seconds / 60);
    seconds = Math.floor(seconds % 60);
    
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// 顯示通用的模態對話框
function showModal(title, message, callback) {
    const modal = document.getElementById('genericModal');
    
    if (modal) {
        const titleElement = modal.querySelector('.modal-title');
        const bodyElement = modal.querySelector('.modal-body');
        
        if (titleElement) titleElement.textContent = title;
        if (bodyElement) bodyElement.innerHTML = message;
        
        const modalInstance = new bootstrap.Modal(modal);
        modalInstance.show();
        
        if (callback && typeof callback === 'function') {
            modal.addEventListener('hidden.bs.modal', callback, { once: true });
        }
    }
}

// 表單資料的序列化
function serializeForm(form) {
    const formData = new FormData(form);
    const serialized = {};
    
    for (const [key, value] of formData.entries()) {
        serialized[key] = value;
    }
    
    return serialized;
}

// 防抖函數 - 避免頻繁調用
function debounce(func, wait) {
    let timeout;
    
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 節流函數 - 限制調用頻率
function throttle(func, limit) {
    let inThrottle;
    
    return function executedFunction(...args) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => {
                inThrottle = false;
            }, limit);
        }
    };
}