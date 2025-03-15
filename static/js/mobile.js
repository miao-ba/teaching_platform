/**
 * 行動裝置特定功能與互動優化
 */

// 在 DOM 載入完成後執行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化側邊欄切換
    initMobileSidebar();
    
    // 初始化行動導航欄
    initMobileNav();
    
    // 初始化行動抽屜
    initMobileDrawers();
    
    // 初始化浮動動作按鈕
    initMobileFab();
    
    // 初始化下拉式重新整理
    initPullToRefresh();
    
    // 初始化觸控手勢
    initTouchGestures();
});

/**
 * 側邊欄行動裝置優化
 */
function initMobileSidebar() {
    // 獲取側邊欄開關按鈕
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    // 如果沒有側邊欄，則不進行初始化
    if (!sidebar || !sidebarToggle) return;
    
    // 創建背景遮罩
    let backdrop = document.querySelector('.sidebar-backdrop');
    if (!backdrop) {
        backdrop = document.createElement('div');
        backdrop.className = 'sidebar-backdrop';
        document.body.appendChild(backdrop);
    }
    
    // 切換側邊欄
    sidebarToggle.addEventListener('click', function(e) {
        e.preventDefault();
        sidebar.classList.toggle('show');
        backdrop.classList.toggle('show');
        document.body.classList.toggle('sidebar-open');
    });
    
    // 點擊背景關閉側邊欄
    backdrop.addEventListener('click', function() {
        sidebar.classList.remove('show');
        backdrop.classList.remove('show');
        document.body.classList.remove('sidebar-open');
    });
    
    // 在小屏幕上點擊側邊欄菜單項後自動關閉側邊欄
    if (window.innerWidth < 992) {
        const sidebarLinks = sidebar.querySelectorAll('.nav-link:not([data-bs-toggle])');
        sidebarLinks.forEach(link => {
            link.addEventListener('click', function() {
                sidebar.classList.remove('show');
                backdrop.classList.remove('show');
                document.body.classList.remove('sidebar-open');
            });
        });
    }
    
    // 偵測滑動手勢關閉側邊欄
    let touchStartX = 0;
    let touchEndX = 0;
    
    sidebar.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    }, false);
    
    sidebar.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, false);
    
    function handleSwipe() {
        if (touchStartX - touchEndX > 50 && window.innerWidth < 992) {
            // 向左滑動
            sidebar.classList.remove('show');
            backdrop.classList.remove('show');
            document.body.classList.remove('sidebar-open');
        }
    }
}

/**
 * 行動底部導航欄
 */
function initMobileNav() {
    const mobileNav = document.querySelector('.mobile-nav');
    if (!mobileNav) return;
    
    // 設置當前活動頁面
    const currentPath = window.location.pathname;
    const navItems = mobileNav.querySelectorAll('.mobile-nav-item');
    
    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (href && currentPath.startsWith(href)) {
            item.classList.add('active');
        }
    });
}

/**
 * 行動抽屜菜單
 */
function initMobileDrawers() {
    // 獲取所有抽屜開關按鈕
    const drawerToggles = document.querySelectorAll('[data-toggle="mobile-drawer"]');
    
    drawerToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('data-target');
            const drawer = document.querySelector(targetId);
            
            if (!drawer) return;
            
            // 創建或獲取背景遮罩
            let backdrop = document.querySelector(`${targetId}-backdrop`);
            if (!backdrop) {
                backdrop = document.createElement('div');
                backdrop.className = 'mobile-drawer-backdrop';
                backdrop.id = `${targetId.substr(1)}-backdrop`;
                document.body.appendChild(backdrop);
            }
            
            // 切換抽屜顯示
            drawer.classList.toggle('show');
            backdrop.classList.toggle('show');
            
            // 防止滾動
            if (drawer.classList.contains('show')) {
                document.body.style.overflow = 'hidden';
            } else {
                document.body.style.overflow = '';
            }
            
            // 點擊背景關閉抽屜
            backdrop.addEventListener('click', function() {
                drawer.classList.remove('show');
                backdrop.classList.remove('show');
                document.body.style.overflow = '';
            });
            
            // 關閉按鈕
            const closeButtons = drawer.querySelectorAll('[data-dismiss="mobile-drawer"]');
            closeButtons.forEach(btn => {
                btn.addEventListener('click', function() {
                    drawer.classList.remove('show');
                    backdrop.classList.remove('show');
                    document.body.style.overflow = '';
                });
            });
        });
    });
}

/**
 * 浮動動作按鈕
 */
function initMobileFab() {
    const fab = document.querySelector('.mobile-fab');
    if (!fab) return;
    
    // 如果 FAB 有子菜單
    const fabMenu = document.querySelector('.mobile-fab-menu');
    if (fabMenu) {
        fab.addEventListener('click', function(e) {
            e.preventDefault();
            fabMenu.classList.toggle('show');
        });
        
        // 點擊其他地方關閉子菜單
        document.addEventListener('click', function(e) {
            if (!fab.contains(e.target) && !fabMenu.contains(e.target)) {
                fabMenu.classList.remove('show');
            }
        });
    }
    
    // 滾動時自動隱藏/顯示 FAB
    let lastScrollTop = 0;
    window.addEventListener('scroll', function() {
        const st = window.pageYOffset || document.documentElement.scrollTop;
        
        if (st > lastScrollTop && st > 300) {
            // 向下滾動且超過 300px，隱藏 FAB
            fab.style.transform = 'translateY(80px)';
        } else {
            // 向上滾動或剛開始滾動，顯示 FAB
            fab.style.transform = 'translateY(0)';
        }
        
        lastScrollTop = st <= 0 ? 0 : st;
    }, false);
}

/**
 * 下拉式重新整理功能
 */
function initPullToRefresh() {
    const pullToRefreshElement = document.querySelector('.pull-to-refresh');
    const contentElement = document.querySelector('.pull-to-refresh-enabled');
    
    if (!pullToRefreshElement || !contentElement) return;
    
    let touchStartY = 0;
    let touchMoveY = 0;
    
    contentElement.addEventListener('touchstart', function(e) {
        touchStartY = e.touches[0].clientY;
    }, { passive: true });
    
    contentElement.addEventListener('touchmove', function(e) {
        if (contentElement.scrollTop === 0) {
            touchMoveY = e.touches[0].clientY;
            const distance = touchMoveY - touchStartY;
            
            if (distance > 0 && distance < 100) {
                pullToRefreshElement.style.transform = `translateY(${distance - 100}px)`;
                pullToRefreshElement.classList.add('visible');
                
                if (distance > 60) {
                    pullToRefreshElement.textContent = '放開以重新整理';
                } else {
                    pullToRefreshElement.textContent = '下拉重新整理';
                }
                
                e.preventDefault();
            }
        }
    });
    
    contentElement.addEventListener('touchend', function(e) {
        if (pullToRefreshElement.classList.contains('visible')) {
            const distance = touchMoveY - touchStartY;
            
            if (distance > 60) {
                // 執行重新整理
                pullToRefreshElement.classList.add('refreshing');
                pullToRefreshElement.textContent = '正在重新整理...';
                
                // 模擬重新整理操作
                setTimeout(function() {
                    location.reload();
                }, 1000);
            } else {
                // 不夠觸發重新整理，恢復原位
                pullToRefreshElement.style.transform = 'translateY(-100%)';
                pullToRefreshElement.classList.remove('visible');
            }
        }
    });
}

/**
 * 觸控手勢支援
 */
function initTouchGestures() {
    // 雙指縮放預防（防止不必要的縮放）
    document.addEventListener('touchmove', function(e) {
        if (e.touches.length > 1) {
            e.preventDefault();
        }
    }, { passive: false });
    
    // 向右滑動返回（僅在行動裝置瀏覽器支援）
    if ('ontouchstart' in window) {
        let touchStartX = 0;
        let touchEndX = 0;
        
        document.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
        }, false);
        
        document.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            handleHistorySwipe();
        }, false);
        
        function handleHistorySwipe() {
            // 向右滑動（從左邊緣開始）
            if (touchEndX - touchStartX > 100 && touchStartX < 50) {
                window.history.back();
            }
        }
    }
}