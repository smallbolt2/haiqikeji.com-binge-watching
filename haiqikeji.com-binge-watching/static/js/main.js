$(document).ready(function() {
    let autoScroll = true;
    let lastLogCount = 0;
    const socket = io();
    
    // WebSocket连接处理
    socket.on('connect', function() {
        console.log('WebSocket connected');
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket disconnected');
    });
    
    // 处理实时日志
    socket.on('log_message', function(data) {
        const logEntry = createLogEntry(data);
        $('#log').append(logEntry);
        
        if (autoScroll) {
            $('#log').scrollTop($('#log')[0].scrollHeight);
        }
        
        lastLogCount++;
    });
    
    // 创建日志条目
    function createLogEntry(log) {
        const levelClass = log.level === 'ERROR' ? 'error' : 
                          log.level === 'INFO' ? 'info' : 
                          log.level === 'WARNING' ? 'warning' : 'secondary';
        
        const levelIcon = log.level === 'ERROR' ? 'fa-exclamation-circle' : 
                         log.level === 'INFO' ? 'fa-info-circle' : 
                         log.level === 'WARNING' ? 'fa-exclamation-triangle' : 'fa-circle';
        
        return `
            <div class="log-entry ${levelClass}">
                <div class="d-flex align-items-start">
                    <i class="fas ${levelIcon} me-2 mt-1"></i>
                    <div class="flex-grow-1">
                        <div class="timestamp">[${log.timestamp}]</div>
                        <div class="message">${log.message}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // 标签页切换
    $('.menu-item').click(function() {
        const tabId = $(this).data('tab');
        
        // 更新菜单项状态
        $('.menu-item').removeClass('active');
        $(this).addClass('active');
        
        // 更新标签页内容
        $('.tab-content').removeClass('active');
        $('#' + tabId).addClass('active');
    });
    
    // 更新当前时间
    function updateCurrentTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        $('#currentTime').text(timeString);
    }
    
    // 定期更新系统状态
    function updateStatus() {
        $.get('/api/status', function(data) {
            const runningUsers = data.running_users || 0;
            const totalUsers = data.total_users || 0;
            
            const statusClass = runningUsers > 0 ? 'success' : 'info';
            const statusIcon = runningUsers > 0 ? 'fa-check-circle' : 'fa-info-circle';
            const statusText = runningUsers > 0 ? `运行中 (${runningUsers}/${totalUsers})` : '已停止';
            
            $('#status').html(`
                <div class="status-display">
                    <i class="fas ${statusIcon}" style="color: ${statusClass === 'success' ? '#10b981' : '#3b82f6'}"></i>
                    <span>${statusText}</span>
                </div>
            `);
            
            // 更新系统状态
            $('#systemStatus').text(runningUsers > 0 ? '运行中' : '已停止');
            
        }).fail(function() {
            $('#status').html(`
                <div class="status-display">
                    <i class="fas fa-exclamation-triangle" style="color: #ef4444"></i>
                    <span>连接失败</span>
                </div>
            `);
        });
    }

    // 定期更新用户列表
    function updateUserList() {
        $.get('/api/users', function(data) {
            let html = '';
            let totalUsers = 0;
            let runningUsers = 0;
            let totalCourses = 0;
            let totalVideos = 0;
            
            data.forEach(function(user) {
                totalUsers++;
                
                const statusClass = user.status && user.status.includes('失败') ? 'danger' : 
                                  user.status && user.status.includes('成功') ? 'success' : 
                                  user.status && user.status.includes('等待') ? 'warning' : 'info';
                
                const statusIcon = user.status && user.status.includes('失败') ? 'fa-exclamation-circle' : 
                                 user.status && user.status.includes('成功') ? 'fa-check-circle' : 
                                 user.status && user.status.includes('等待') ? 'fa-clock' : 'fa-info-circle';
                
                html += `
                    <div class="user-item">
                        <div class="user-header">
                            <div class="user-name">
                                <i class="fas fa-user me-2" style="color: #3b82f6"></i>
                                ${user.username}
                            </div>
                            <div class="user-controls">
                                <button class="btn-start-user btn-sm btn-success me-2" data-username="${user.username}">
                                    <i class="fas fa-play"></i> 启动
                                </button>
                                <button class="btn-stop-user btn-sm btn-danger" data-username="${user.username}">
                                    <i class="fas fa-stop"></i> 停止
                                </button>
                            </div>
                        </div>
                        <div class="user-details">
                            <div class="user-detail">
                                <i class="fas fa-info-circle" style="color: #3b82f6"></i>
                                <span>状态: 未启动</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            if (data.length === 0) {
                html = `
                    <div class="loading-placeholder">
                        <i class="fas fa-users fa-3x mb-3" style="color: #cbd5e1"></i>
                        <p>暂无用户数据</p>
                        <small>请检查配置文件</small>
                    </div>
                `;
            }
            
            $('#userList').html(html);
            $('#userCount').text(totalUsers);
            
            // 更新统计信息
            $('#totalUsers').text(totalUsers);
            $('#runningUsers').text(runningUsers);
            $('#totalCourses').text(totalCourses);
            $('#totalVideos').text(totalVideos);
            
            // 添加数字动画效果
            animateNumbers();
        }).fail(function() {
            $('#userList').html(`
                <div class="loading-placeholder">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3" style="color: #ef4444"></i>
                    <p>加载用户数据失败</p>
                    <small>请检查网络连接</small>
                </div>
            `);
        });
    }

    // 定期更新运行中的用户状态
    function updateRunningUsers() {
        $.get('/api/status', function(data) {
            data.users.forEach(function(user) {
                const userItem = $(`.user-item:has(.user-name:contains("${user.username}"))`);
                if (userItem.length > 0) {
                    const statusClass = user.status && user.status.includes('失败') ? 'danger' : 
                                      user.status && user.status.includes('成功') ? 'success' : 
                                      user.status && user.status.includes('等待') ? 'warning' : 'info';
                    
                    const statusIcon = user.status && user.status.includes('失败') ? 'fa-exclamation-circle' : 
                                     user.status && user.status.includes('成功') ? 'fa-check-circle' : 
                                     user.status && user.status.includes('等待') ? 'fa-clock' : 'fa-info-circle';
                    
                    const userDetails = userItem.find('.user-details');
                    userDetails.html(`
                        <div class="user-detail">
                            <i class="fas ${statusIcon}" style="color: ${statusClass === 'success' ? '#10b981' : statusClass === 'danger' ? '#ef4444' : statusClass === 'warning' ? '#f59e0b' : '#3b82f6'}"></i>
                            <span>状态: ${user.status || '未知'}</span>
                        </div>
                        ${user.course ? `
                            <div class="user-detail">
                                <i class="fas fa-book" style="color: #f59e0b"></i>
                                <span>当前课程: ${user.course}</span>
                            </div>
                        ` : ''}
                        ${user.video ? `
                            <div class="user-detail">
                                <i class="fas fa-video" style="color: #8b5cf6"></i>
                                <span>当前视频: ${user.video}</span>
                            </div>
                        ` : ''}
                    `);
                    
                    // 更新按钮状态
                    const startBtn = userItem.find('.btn-start-user');
                    const stopBtn = userItem.find('.btn-stop-user');
                    
                    if (user.running) {
                        startBtn.prop('disabled', true).addClass('disabled');
                        stopBtn.prop('disabled', false).removeClass('disabled');
                    } else {
                        startBtn.prop('disabled', false).removeClass('disabled');
                        stopBtn.prop('disabled', true).addClass('disabled');
                    }
                }
            });
        });
    }

    // 数字动画效果
    function animateNumbers() {
        $('.stat-number').each(function() {
            const $this = $(this);
            const countTo = parseInt($this.text());
            
            $({ countNum: 0 }).animate({
                countNum: countTo
            }, {
                duration: 1000,
                easing: 'swing',
                step: function() {
                    $this.text(Math.floor(this.countNum));
                },
                complete: function() {
                    $this.text(this.countNum);
                }
            });
        });
    }
    
    // 显示通知
    function showNotification(message, type = 'info') {
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'error' ? 'alert-danger' : 
                          type === 'warning' ? 'alert-warning' : 'alert-info';
        
        const icon = type === 'success' ? 'fa-check-circle' : 
                    type === 'error' ? 'fa-exclamation-circle' : 
                    type === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle';
        
        const notification = $(`
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas ${icon} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `);
        
        $('#notificationContainer').append(notification);
        
        // 自动消失
        setTimeout(function() {
            notification.alert('close');
        }, 5000);
    }
    
    // 启动单个用户
    $(document).on('click', '.btn-start-user', function() {
        const username = $(this).data('username');
        const btn = $(this);
        
        btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> 启动中...');
        
        $.ajax({
            url: '/api/start',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ username: username }),
            success: function(response) {
                if (response.success) {
                    showNotification(response.message, 'success');
                } else {
                    showNotification(response.message, 'error');
                }
            },
            error: function() {
                showNotification('启动用户失败，请检查网络连接', 'error');
            },
            complete: function() {
                btn.prop('disabled', false).html('<i class="fas fa-play"></i> 启动');
            }
        });
    });
    
    // 停止单个用户
    $(document).on('click', '.btn-stop-user', function() {
        const username = $(this).data('username');
        const btn = $(this);
        
        btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> 停止中...');
        
        $.ajax({
            url: '/api/stop',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ username: username }),
            success: function(response) {
                if (response.success) {
                    showNotification(response.message, 'success');
                } else {
                    showNotification(response.message, 'error');
                }
            },
            error: function() {
                showNotification('停止用户失败，请检查网络连接', 'error');
            },
            complete: function() {
                btn.prop('disabled', false).html('<i class="fas fa-stop"></i> 停止');
            }
        });
    });
    
    // 启动全部用户
    $('#startAllBtn').click(function() {
        const btn = $(this);
        btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> 启动中...');
        
        // 获取所有用户并逐个启动
        $.get('/api/users', function(users) {
            let startedCount = 0;
            let totalUsers = users.length;
            
            if (totalUsers === 0) {
                showNotification('没有找到用户配置', 'warning');
                btn.prop('disabled', false).html('<i class="fas fa-play"></i> 启动全部');
                return;
            }
            
            users.forEach(function(user, index) {
                setTimeout(function() {
                    $.ajax({
                        url: '/api/start',
                        method: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify({ username: user.username }),
                        success: function(response) {
                            if (response.success) {
                                startedCount++;
                            }
                            
                            if (index === totalUsers - 1) {
                                showNotification(`成功启动 ${startedCount}/${totalUsers} 个用户`, 'success');
                                btn.prop('disabled', false).html('<i class="fas fa-play"></i> 启动全部');
                            }
                        },
                        error: function() {
                            if (index === totalUsers - 1) {
                                showNotification('启动用户时出现错误', 'error');
                                btn.prop('disabled', false).html('<i class="fas fa-play"></i> 启动全部');
                            }
                        }
                    });
                }, index * 1000); // 每个用户间隔1秒启动
            });
        });
    });
    
    // 停止全部用户
    $('#stopAllBtn').click(function() {
        const btn = $(this);
        btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> 停止中...');
        
        $.ajax({
            url: '/api/stop_all',
            method: 'POST',
            contentType: 'application/json',
            success: function(response) {
                if (response.success) {
                    showNotification(response.message, 'success');
                } else {
                    showNotification(response.message, 'error');
                }
            },
            error: function() {
                showNotification('停止所有用户失败，请检查网络连接', 'error');
            },
            complete: function() {
                btn.prop('disabled', false).html('<i class="fas fa-stop"></i> 停止全部');
            }
        });
    });
    
    // 日志控制
    $('#autoScrollBtn').click(function() {
        autoScroll = !autoScroll;
        $(this).toggleClass('active');
        if (autoScroll) {
            $('#log').scrollTop($('#log')[0].scrollHeight);
        }
    });
    
    $('#clearLogBtn').click(function() {
        $('#log').empty();
        lastLogCount = 0;
        showNotification('日志已清除', 'info');
    });
    
    // 初始化
    updateCurrentTime();
    updateStatus();
    updateUserList();
    updateRunningUsers();
    
    // 定时更新
    setInterval(updateCurrentTime, 1000);
    setInterval(updateStatus, 5000);
    setInterval(updateUserList, 10000);
    setInterval(updateRunningUsers, 3000);
}); 