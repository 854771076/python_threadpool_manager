// 线程池管理器前端JavaScript

/**
 * 线程池管理器前端应用
 */
class ThreadPoolManager {
    constructor() {
        this.baseUrl = '';
        this.refreshInterval = 3000; // 3秒自动刷新
        this.refreshTimer = null;
        
        // 添加分页状态
        this.pagination = {
            current_page: 1,
            per_page: 10,
            total_pages: 1,
            has_next: false,
            has_prev: false
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.initPaginationEvents();
        this.startAutoRefresh();
        this.loadInitialData();
    }

    initPaginationEvents() {
        // 分页事件绑定
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('page-link')) {
                e.preventDefault();
                const page = e.target.dataset.page;
                if (page) {
                    this.goToPage(parseInt(page));
                }
            }
        });

        // 每页条数变化
        document.addEventListener('change', (e) => {
            if (e.target.id === 'perPageSelect') {
                this.pagination.per_page = parseInt(e.target.value);
                this.pagination.current_page = 1;
                this.loadTasks();
            }
        });

        // 跳转到页码
        document.addEventListener('click', (e) => {
            if (e.target.id === 'goToPageBtn') {
                const input = document.getElementById('goToPageInput');
                const page = parseInt(input.value);
                if (page && page >= 1 && page <= this.pagination.total_pages) {
                    this.goToPage(page);
                }
            }
        });

        document.addEventListener('keypress', (e) => {
            if (e.target.id === 'goToPageInput' && e.key === 'Enter') {
                const page = parseInt(e.target.value);
                if (page && page >= 1 && page <= this.pagination.total_pages) {
                    this.goToPage(page);
                }
            }
        });
    }

    bindEvents() {
        // 确保DOM元素存在再绑定事件
        const createPoolForm = document.getElementById('createPoolForm');
        if (createPoolForm) {
            createPoolForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createPool();
            });
        }

        const submitTaskForm = document.getElementById('submitTaskForm');
        if (submitTaskForm) {
            submitTaskForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitTask();
            });
        }

        // 模态框事件
        const submitTaskModal = document.getElementById('submitTaskModal');
        if (submitTaskModal) {
            submitTaskModal.addEventListener('show.bs.modal', () => {
                this.loadPoolsForTaskModal();
            });
        }
    }

    async loadInitialData() {
        try {
            await Promise.all([
                this.loadPools(),
                this.loadTasks(),
                this.loadStats()
            ]);
        } catch (error) {
            console.error('初始化数据加载失败:', error);
            this.showError('数据加载失败，请刷新页面重试');
        }
    }

    async loadPools() {
        try {
            const response = await fetch('/api/pools');
            const result = await response.json();
            
            if (response.ok && result.success) {
                const pools = result.data || [];
                this.renderPools(pools);
                this.updatePoolFilter(pools);
            } else {
                throw new Error(result.error || '加载线程池失败');
            }
        } catch (error) {
            console.error('加载线程池失败:', error);
            this.renderPools([]);
        }
    }

    async loadTasks() {
        try {
            const params = new URLSearchParams({
                page: this.pagination.current_page,
                per_page: this.pagination.per_page
            });

            // 添加线程池过滤
            const poolFilter = document.getElementById('poolFilter');
            if (poolFilter && poolFilter.value) {
                params.append('pool_id', poolFilter.value);
            }

            const response = await fetch(`/api/tasks?${params}`);
            const result = await response.json();
            
            if (response.ok && result.success) {
                const tasks = result.data || [];
                this.renderTasks(tasks);
                
                // 更新分页信息
                if (result.pagination) {
                    this.pagination = {
                        ...this.pagination,
                        ...result.pagination
                    };
                    this.renderPagination();
                }
            } else {
                throw new Error(result.error || '加载任务失败');
            }
        } catch (error) {
            console.error('加载任务失败:', error);
            this.renderTasks([]);
        }
    }
    // 取消线程池任务
    async cancelPoolTasks(pool_id) {
        try {
            const response = await fetch(`/api/pools/${pool_id}/cancel_pool_tasks`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showSuccess('线程池任务已取消');
                this.loadTasks();
            } else {
                throw new Error(result.error || '取消线程池任务失败');
            }
        } catch (error) {
            console.error('取消线程池任务失败:', error);
            this.showError('取消线程池任务失败');
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.renderStats(result.data || {});
            } else {
                throw new Error(result.error || '加载统计信息失败');
            }
        } catch (error) {
            console.error('加载统计信息失败:', error);
            this.renderStats({});
        }
    }

    renderPools(pools) {
        const container = document.getElementById('poolsContainer');
        if (!container) return;

        if (!pools || pools.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="bi bi-inbox fs-1"></i>
                    <p>暂无线程池</p>
                    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#createPoolModal">
                        <i class="bi bi-plus"></i> 创建第一个线程池
                    </button>
                </div>
            `;
            return;
        }

        const poolsHtml = pools.map(pool => `
            <div class="card mb-3">
                <div class="card-header">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-0"><span>${pool.name} </span><span class="badge bg-secondary">${pool.max_workers} 线程</span></h6>
                            
                            <small class="text-muted">ID: ${pool.pool_id}</small>
                            
                        </div>
                        
                    </div>
                    <div>
                            
                            <button class="btn btn-sm btn-danger" onclick="threadPoolManager.closePool('${pool.pool_id}')">
                                <i class="bi bi-x"></i> 关闭
                            </button>
                            <button class="btn btn-sm btn-warning" onclick="threadPoolManager.cancelPoolTasks('${pool.pool_id}')">
                                <i class="bi bi-x"></i> 取消未执行任务
                            </button>
                        </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-4">
                            <small class="text-muted">待处理任务</small>
                            <h6>${pool.pending_tasks || 0}</h6>
                        </div>
                        <div class="col-4">
                            <small class="text-muted">运行中的任务</small>
                            <h6>${pool.running_tasks || 0}</h6>
                        </div>
                        <div class="col-4">
                            <small class="text-muted">已完成任务</small>
                            <h6>${pool.completed_tasks || 0}</h6>
                        </div>
                        <div class="col-4">
                            <small class="text-muted">已取消任务</small>
                            <h6>${pool.cancelled_tasks || 0}</h6>
                        </div>
                        <div class="col-4">
                            <small class="text-muted">失败任务</small>
                            <h6>${pool.failed_tasks || 0}</h6>
                        </div>
                        <div class="col-4">
                            <small class="text-muted">状态</small>
                            <h6>
                                <span class="badge ${pool.is_closed ? 'bg-danger' : 'bg-success'}">
                                    ${pool.is_closed ? '已关闭' : '运行中'}
                                </span>
                            </h6>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = poolsHtml;
    }

    renderTasks(tasks) {
        const container = document.getElementById('tasksContainer');
        if (!container) return;

        if (!tasks || tasks.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="bi bi-list-ul fs-1"></i>
                    <p>暂无任务</p>
                    <button class="btn btn-success" data-bs-toggle="modal" data-bs-target="#submitTaskModal">
                        <i class="bi bi-plus"></i> 提交第一个任务
                    </button>
                </div>
            `;
            return;
        }

        const tasksHtml = tasks.map(task => `
            <div class="task-item ${task.status}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${task.name}</h6>
                        <small class="text-muted">ID: ${task.task_id}</small>
                    </div>
                    <div class="text-end">
                        <span class="badge ${this.getStatusBadgeClass(task.status)}">
                            ${this.getStatusText(task.status)}
                        </span>
                    </div>
                </div>
                <div class="mt-2">
                    <small class="text-muted">线程池: ${task.pool_id || '未知'}</small>
                    <br>
                    <small class="text-muted">运行时间: ${this.formatDuration(task.duration)}</small>
                </div>
                
                ${task.result ? `
                    <div class="mt-2">
                        <div class="alert alert-success py-1">
                            <small><strong>结果:</strong> ${this.formatResult(task.result)}</small>
                        </div>
                    </div>
                ` : ''}
                
                ${task.exception ? `
                    <div class="mt-2">
                        <div class="alert alert-danger py-1">
                            <small><strong>异常:</strong> ${this.formatResult(task.exception)}</small>
                        </div>
                    </div>
                ` : ''}
                
                <div class="mt-2">
                    <button class="btn btn-sm btn-info" onclick="threadPoolManager.viewTaskDetails('${task.task_id}')">
                        <i class="bi bi-eye"></i> 详情
                    </button>
                    ${task.status === 'pending' ? `
                    <button class="btn btn-sm btn-warning" onclick="threadPoolManager.cancelTask('${task.task_id}')">
                        <i class="bi bi-stop"></i> 取消
                    </button>
                    ` : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = tasksHtml;
    }

    renderStats(stats) {
        const elements = {
            total_pools: document.getElementById('totalPools'),
            total_tasks: document.getElementById('totalTasks'),
            active_tasks: document.getElementById('activeTasks'),
            completed_tasks: document.getElementById('completedTasks')
        };

        Object.keys(elements).forEach(key => {
            if (elements[key]) {
                elements[key].textContent = stats[key] || 0;
            }
        });
    }

    goToPage(page) {
        if (page >= 1 && page <= this.pagination.total_pages) {
            this.pagination.current_page = page;
            this.loadTasks();
        }
    }

    nextPage() {
        if (this.pagination.has_next) {
            this.pagination.current_page++;
            this.loadTasks();
        }
    }

    prevPage() {
        if (this.pagination.has_prev) {
            this.pagination.current_page--;
            this.loadTasks();
        }
    }

    renderPagination() {
        const container = document.getElementById('paginationContainer');
        if (!container) return;

        if (this.pagination.total_pages <= 1) {
            container.innerHTML = '';
            return;
        }

        let html = `<nav aria-label="任务分页">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div>
                    <small class="text-muted">
                        显示 ${this.pagination.start_item}-${this.pagination.end_item} 条，共 ${this.pagination.total_items} 条
                    </small>
                </div>
                <div>
                    <select class="form-select form-select-sm" id="perPageSelect" style="width: auto;">
                        <option value="10" ${this.pagination.per_page === 10 ? 'selected' : ''}>10 条/页</option>
                        <option value="20" ${this.pagination.per_page === 20 ? 'selected' : ''}>20 条/页</option>
                        <option value="50" ${this.pagination.per_page === 50 ? 'selected' : ''}>50 条/页</option>
                        <option value="100" ${this.pagination.per_page === 100 ? 'selected' : ''}>100 条/页</option>
                    </select>
                </div>
            </div>
            <ul class="pagination justify-content-center">
                <li class="page-item ${!this.pagination.has_prev ? 'disabled' : ''}">
                    <a class="page-link" href="#" onclick="threadPoolManager.prevPage()">上一页</a>
                </li>`;

        // 页码显示逻辑
        const startPage = Math.max(1, this.pagination.current_page - 2);
        const endPage = Math.min(this.pagination.total_pages, this.pagination.current_page + 2);

        if (startPage > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
            if (startPage > 2) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `<li class="page-item ${i === this.pagination.current_page ? 'active' : ''}">
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            </li>`;
        }

        if (endPage < this.pagination.total_pages) {
            if (endPage < this.pagination.total_pages - 1) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${this.pagination.total_pages}">${this.pagination.total_pages}</a></li>`;
        }

        html += `<li class="page-item ${!this.pagination.has_next ? 'disabled' : ''}">
                    <a class="page-link" href="#" onclick="threadPoolManager.nextPage()">下一页</a>
                </li>
            </ul>
            <div class="d-flex justify-content-center mt-2">
                <div class="input-group" style="width: 200px;">
                    <input type="number" class="form-control form-control-sm" id="goToPageInput" 
                           min="1" max="${this.pagination.total_pages}" placeholder="页码">
                    <button class="btn btn-sm btn-primary" id="goToPageBtn">跳转</button>
                </div>
            </div>
        </nav>`;

        container.innerHTML = html;
    }

    updatePoolFilter(pools) {
        if (!pools || typeof DropdownUtils === 'undefined') return;
        DropdownUtils.updatePoolSelect(pools, 'poolFilter', '所有线程池');
    }

    async loadPoolsForTaskModal() {
        if (typeof DropdownUtils !== 'undefined') {
            DropdownUtils.loadPoolsForTaskModal();
        }
    }

    getStatusBadgeClass(status) {
        const classes = {
            'pending': 'bg-primary',
            'running': 'bg-warning',
            'completed': 'bg-success',
            'failed': 'bg-danger',
            'cancelled': 'bg-secondary'
        };
        return classes[status] || 'bg-secondary';
    }

    getStatusText(status) {
        const texts = {
            'pending': '待执行',
            'running': '运行中',
            'completed': '已完成',
            'failed': '已失败',
            'cancelled': '已取消'
        };
        return texts[status] || status;
    }

    formatDuration(seconds) {
        if (!seconds) return '0s';
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}m ${remainingSeconds}s`;
    }

    formatResult(result) {
        if (!result) return '';
        if (typeof result === 'object') {
            return JSON.stringify(result, null, 2);
        }
        return String(result);
    }

    async createPool() {
        const form = document.getElementById('createPoolForm');
        if (!form) return;

        const formData = new FormData(form);
        const data = {
            name: formData.get('name') || undefined,
            max_workers: parseInt(formData.get('max_workers')) || 5
        };

        try {
            const response = await fetch('/api/pools', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess('线程池创建成功');
                form.reset();
                const modal = bootstrap.Modal.getInstance(document.getElementById('createPoolModal'));
                modal.hide();
                await this.loadPools();
            } else {
                throw new Error(result.error || '创建线程池失败');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    async submitTask() {
        const form = document.getElementById('submitTaskForm');
        if (!form) return;

        const formData = new FormData(form);
        const data = {
            pool_id: formData.get('pool_id'),
            task_name: formData.get('task_name') || undefined,
            task_type: formData.get('task_type') || 'demo',
            duration: parseInt(formData.get('duration')) || 5
        };

        if (!data.pool_id) {
            this.showError('请选择线程池');
            return;
        }

        try {
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess('任务提交成功');
                form.reset();
                const modal = bootstrap.Modal.getInstance(document.getElementById('submitTaskModal'));
                modal.hide();
                await this.loadTasks();
            } else {
                throw new Error(result.error || '提交任务失败');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    async viewTaskDetails(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            const data = await response.json();
            const task = data.data;
            

            if (!response.ok) {
                throw new Error(task.error || '获取任务详情失败');
            }

            const modalHtml = `
                <div class="modal fade" id="taskDetailModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">任务详情</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <h6>基本信息</h6>
                                        <table class="table table-sm">
                                            <tr><td><strong>任务ID:</strong></td><td>${task.task_id || '未知'}</td></tr>
                                            <tr><td><strong>任务名称:</strong></td><td>${task.name || '未知'}</td></tr>
                                            <tr><td><strong>状态:</strong></td><td><span class="badge ${this.getStatusBadgeClass(task.status)}">${this.getStatusText(task.status)}</span></td></tr>
                                            <tr><td><strong>线程池:</strong></td><td>${task.pool_id || '未知'}</td></tr>
                                        </table>
                                    </div>
                                    <div class="col-md-6">
                                        <h6>时间信息</h6>
                                        <table class="table table-sm">
                                            <tr><td><strong>创建时间:</strong></td><td>${new Date(task.submit_time).toLocaleString()}</td></tr>
                                            <tr><td><strong>开始时间:</strong></td><td>${task.start_time ? new Date(task.start_time).toLocaleString() : '-'}</td></tr>
                                            <tr><td><strong>完成时间:</strong></td><td>${task.end_time ? new Date(task.end_time).toLocaleString() : '-'}</td></tr>
                                            <tr><td>-</td></tr>
                                        </table>
                                    </div>
                                    
                                </div>
                                
                                ${task.parameters ? `
                                    <div class="mt-3">
                                        <h6>参数</h6>
                                        <pre class="bg-light p-2"><code>${JSON.stringify(task.parameters, null, 2)}</code></pre>
                                    </div>
                                ` : ''}
                                
                                ${task.result ? `
                                    <div class="mt-3">
                                        <h6>执行结果</h6>
                                        <div class="alert alert-success">
                                            <pre class="mb-0"><code>${this.formatResult(task.result)}</code></pre>
                                        </div>
                                    </div>
                                ` : ''}
                                
                                ${task.exception || task.error ? `
                                    <div class="mt-3">
                                        <h6>错误信息</h6>
                                        <div class="alert alert-danger">
                                            <pre class="mb-0"><code>${this.formatResult(task.exception || task.error)}</code></pre>
                                        </div>
                                    </div>
                                ` : ''}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // 移除已存在的模态框
            const existingModal = document.getElementById('taskDetailModal');
            if (existingModal) {
                existingModal.remove();
            }

            // 添加新模态框到body
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('taskDetailModal'));
            modal.show();

            // 清理DOM
            document.getElementById('taskDetailModal').addEventListener('hidden.bs.modal', function() {
                this.remove();
            });

        } catch (error) {
            this.showError(error.message);
        }
    }

    async cancelTask(taskId) {
        if (!confirm('确定要取消这个任务吗？')) return;

        try {
            const response = await fetch(`/api/tasks/${taskId}`, {
                method: 'DELETE'
            });

            const result = await response.json();
            const success=result.success;
            
            if (success) {
                this.showSuccess('任务已取消');
                await this.loadTasks();
            } else {
                throw new Error(result.error || '取消任务失败');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    async closePool(poolId) {
        if (!confirm('确定要关闭这个线程池吗？这将取消所有待执行的任务。')) return;

        try {
            const response = await fetch(`/api/pools/${poolId}/force-close`, {
                method: 'DELETE'
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess('线程池已关闭');
                await Promise.all([
                    this.loadPools(),
                    this.loadTasks(),
                    this.loadStats()
                ]);
            } else {
                throw new Error(result.error || '关闭线程池失败');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    async forceClosePool(poolId) {
        if (!confirm('确定要强制关闭这个线程池吗？这将取消所有任务并终止正在运行的任务。')) return;

        try {
            const response = await fetch(`/api/pools/${poolId}/force-close`, {
                method: 'POST'
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess('线程池已强制关闭');
                await Promise.all([
                    this.loadPools(),
                    this.loadTasks(),
                    this.loadStats()
                ]);
            } else {
                throw new Error(result.error || '强制关闭线程池失败');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    startAutoRefresh() {
        this.stopAutoRefresh();
        this.refreshTimer = setInterval(() => {
            this.loadTasks();
            this.loadStats();
        }, this.refreshInterval);
    }

    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'danger');
    }

    showToast(message, type = 'info') {
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        const toastContainer = document.getElementById('toastContainer') || this.createToastContainer();
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toast = new bootstrap.Toast(toastContainer.lastElementChild);
        toast.show();
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(container);
        return container;
    }
}

// 全局函数
function refreshData() {
    if (window.threadPoolManager) {
        window.threadPoolManager.loadInitialData();
    }
}

function filterTasks() {
    if (window.threadPoolManager) {
        window.threadPoolManager.pagination.current_page = 1;
        window.threadPoolManager.loadTasks();
    }
}

function createPool() {
    if (window.threadPoolManager) {
        window.threadPoolManager.createPool();
    }
}

function submitTask() {
    if (window.threadPoolManager) {
        window.threadPoolManager.submitTask();
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', function() {
    window.threadPoolManager = new ThreadPoolManager();
});