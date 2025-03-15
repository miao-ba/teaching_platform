/**
 * 主題切換功能
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

// 頁面載入時初始化主題切換功能
document.addEventListener('DOMContentLoaded', function() {
    initThemeToggle();
});