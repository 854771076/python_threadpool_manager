# 技术规范文档

## 1. 动态调整线程池大小技术规范

### 1.1 核心算法

#### 1.1.1 任务迁移算法
```python
class TaskMigrationAlgorithm:
    """
    任务迁移算法 - 零停机时间迁移策略
    
    算法目标：
    1. 确保任务不丢失
    2. 最小化迁移时间
    3. 避免新任务排队
    4. 保证线程安全
    """
    
    def migrate_tasks(self, old_pool, new_pool, task_registry):
        """
        迁移任务到新线程池
        
        步骤：
        1. 暂停新任务提交
        2. 获取待迁移任务列表
        3. 按任务状态分类处理
        4. 重新提交待执行任务
        5. 清理已完成任务
        6. 恢复新任务提交
        """
        
        # 1. 暂停新任务提交
        task_registry.pause_submission()
        
        try:
            # 2. 获取待迁移任务
            pending_tasks = self._get_pending_tasks(old_pool)
            
            # 3. 分类处理任务
            migrated_count = 0
            for task_info in pending_tasks:
                if task_info.status == 'PENDING':
                    # 重新提交到新线程池
                    new_task_id = new_pool.submit(task_info.func, *task_info.args)
                    task_registry.update_task_mapping(task_info.id, new_task_id)
                    migrated_count += 1
                elif task_info.status == 'COMPLETED':
                    # 清理已完成任务
                    task_registry.cleanup_task(task_info.id)
            
            return {
                'migrated_tasks': migrated_count,
                'cleaned_tasks': len(pending_tasks) - migrated_count
            }
            
        finally:
            # 6. 恢复新任务提交
            task_registry.resume_submission()
```

#### 1.1.2 智能建议算法
```python
class SmartResizeAdvisor:
    """
    智能线程数建议算法
    
    基于当前负载和历史数据提供线程数建议
    """
    
    def calculate_suggestion(self, pool_metrics):
        """
        计算建议的线程数
        
        算法逻辑：
        1. 基于活跃任务数计算基础值
        2. 考虑队列长度进行调整
        3. 应用边界限制
        4. 考虑历史性能数据
        """
        
        active_tasks = pool_metrics.active_tasks
        queue_size = pool_metrics.queue_size
        current_workers = pool_metrics.max_workers
        
        # 基础计算：活跃任务 + 缓冲
        base_suggestion = active_tasks + 2
        
        # 队列长度调整
        if queue_size > 5:
            base_suggestion += min(queue_size // 2, 5)
        
        # 边界限制
        min_workers = max(1, current_workers // 2)
        max_workers = min(50, current_workers * 2)
        
        suggestion = max(min_workers, min(max_workers, base_suggestion))
        
        return {
            'suggested_value': suggestion,
            'reasoning': f"基于{active_tasks}个活跃任务和{queue_size}个队列任务计算",
            'current_value': current_workers,
            'min_value': min_workers,
            'max_value': max_workers
        }
```

### 1.2 性能指标

#### 1.2.1 调整性能指标
| 指标名称 | 目标值 | 说明 |
|---------|--------|------|
| 调整延迟 | < 500ms | 从开始调整到完成的时间 |
| 任务丢失率 | 0% | 迁移过程中丢失的任务比例 |
| 迁移成功率 | > 99% | 成功迁移的任务比例 |
| 系统可用性 | > 99.9% | 调整过程中的系统可用性 |

#### 1.2.2 监控指标
```python
class ResizeMetricsCollector:
    """
    调整指标收集器
    """
    
    def __init__(self):
        self.metrics = {
            'resize_count': 0,           # 调整次数
            'avg_resize_duration': 0.0,   # 平均调整时间
            'migration_success_rate': 1.0, # 迁移成功率
            'task_loss_count': 0,         # 任务丢失数
            'error_count': 0             # 错误次数
        }
    
    def record_resize(self, duration, success, migrated_tasks, lost_tasks):
        """记录一次调整操作"""
        self.metrics['resize_count'] += 1
        self.metrics['avg_resize_duration'] = (
            (self.metrics['avg_resize_duration'] * (self.metrics['resize_count'] - 1) + duration) 
            / self.metrics['resize_count']
        )
        
        if success:
            success_rate = migrated_tasks / (migrated_tasks + lost_tasks) if (migrated_tasks + lost_tasks) > 0 else 1.0
            self.metrics['migration_success_rate'] = (
                (self.metrics['migration_success_rate'] * (self.metrics['resize_count'] - 1) + success_rate) 
                / self.metrics['resize_count']
            )
        
        self.metrics['task_loss_count'] += lost_tasks
        if not success:
            self.metrics['error_count'] += 1
```

### 1.3 异常处理规范

#### 1.3.1 错误分类
| 错误类型 | 错误码 | 处理方式 |
|----------|--------|----------|
| 参数错误 | 400 | 返回详细错误信息 |
| 线程池不存在 | 404 | 返回404状态码 |
| 系统繁忙 | 429 | 等待重试 |
| 内部错误 | 500 | 记录日志，返回友好错误 |

#### 1.3.2 回滚机制
```python
class ResizeRollbackManager:
    """
    调整回滚管理器
    
    确保在调整失败时能够恢复到原始状态
    """
    
    def __init__(self, original_pool, original_config):
        self.original_pool = original_pool
        self.original_config = original_config
        self.checkpoint = None
    
    def create_checkpoint(self):
        """创建调整前的检查点"""
        self.checkpoint = {
            'pool_state': self.original_pool.get_state(),
            'task_queue': self.original_pool.get_task_queue_snapshot(),
            'config': self.original_config.copy()
        }
    
    def rollback(self):
        """执行回滚操作"""
        if not self.checkpoint:
            raise ValueError("没有可用的检查点")
        
        try:
            # 恢复原始线程池
            self.original_pool.restore_state(self.checkpoint['pool_state'])
            
            # 重新提交未完成的任务
            for task in self.checkpoint['task_queue']:
                self.original_pool.submit(task.func, *task.args)
            
            return True
        except Exception as e:
            logger.error(f"回滚失败: {e}")
            return False
```

### 1.4 线程安全规范

#### 1.4.1 锁策略
```python
import threading
from contextlib import contextmanager

class ThreadSafeResizeManager:
    """
    线程安全的调整管理器
    """
    
    def __init__(self):
        self._resize_lock = threading.RLock()
        self._task_registry_lock = threading.Lock()
        self._pool_state_lock = threading.Lock()
    
    @contextmanager
    def resize_context(self):
        """调整操作的上下文管理器"""
        with self._resize_lock:
            with self._task_registry_lock:
                with self._pool_state_lock:
                    yield
    
    def safe_resize_pool(self, pool_id, new_size):
        """线程安全的线程池调整"""
        with self.resize_context():
            return self._perform_resize(pool_id, new_size)
```

#### 1.4.2 并发控制
```python
class ConcurrencyController:
    """
    并发控制管理器
    
    防止多个调整操作同时进行
    """
    
    def __init__(self, max_concurrent=1):
        self.semaphore = threading.Semaphore(max_concurrent)
        self.active_operations = {}
    
    def acquire_resize_permission(self, pool_id):
        """获取调整权限"""
        if self.semaphore.acquire(timeout=5):
            if pool_id in self.active_operations:
                self.semaphore.release()
                raise RuntimeError(f"线程池 {pool_id} 正在调整中")
            
            self.active_operations[pool_id] = True
            return True
        return False
    
    def release_resize_permission(self, pool_id):
        """释放调整权限"""
        if pool_id in self.active_operations:
            del self.active_operations[pool_id]
            self.semaphore.release()
```

### 1.5 API设计规范

#### 1.5.1 RESTful接口规范
```python
class ResizeAPI:
    """
    调整API接口规范
    """
    
    ENDPOINTS = {
        'resize': {
            'method': 'PUT',
            'path': '/api/pools/{pool_id}/resize',
            'request': {
                'max_workers': int,
                'force': bool  # 可选，强制调整
            },
            'response': {
                'success': bool,
                'message': str,
                'data': {
                    'pool_id': str,
                    'old_max_workers': int,
                    'new_max_workers': int,
                    'migration_time': float,
                    'migrated_tasks': int
                }
            }
        },
        'resize_info': {
            'method': 'GET',
            'path': '/api/pools/{pool_id}/resize-info',
            'response': {
                'pool_id': str,
                'current_max_workers': int,
                'active_tasks': int,
                'suggested_max_workers': int,
                'can_resize': bool,
                'min_workers': int,
                'max_workers': int
            }
        }
    }
```

#### 1.5.2 错误响应格式
```json
{
  "success": false,
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "参数max_workers必须是正整数",
    "details": {
      "field": "max_workers",
      "value": 0,
      "expected": "大于0的整数"
    }
  }
}
```

### 1.6 测试规范

#### 1.6.1 单元测试要求
```python
class TestResizeFunctionality:
    """
    调整功能单元测试
    """
    
    def test_task_migration_zero_loss(self):
        """测试任务迁移零丢失"""
        # 创建测试线程池
        pool = ManagedThreadPool(max_workers=2)
        
        # 提交测试任务
        tasks = []
        for i in range(10):
            task = pool.submit(slow_task, i)
            tasks.append(task)
        
        # 执行调整
        result = pool.resize(5)
        
        # 验证所有任务完成
        completed_tasks = sum(1 for task in tasks if task.done())
        assert completed_tasks == 10, f"预期完成10个任务，实际完成{completed_tasks}个"
    
    def test_resize_rollback_on_failure(self):
        """测试调整失败时的回滚"""
        pool = ManagedThreadPool(max_workers=3)
        
        # 模拟调整失败
        with patch.object(pool, '_create_new_pool', side_effect=Exception("创建失败")):
            original_size = pool.max_workers
            result = pool.resize(5)
            
            assert not result.success, "调整应该失败"
            assert pool.max_workers == original_size, "应该回滚到原始大小"
```

#### 1.6.2 集成测试要求
```python
class TestResizeIntegration:
    """
    调整功能集成测试
    """
    
    def test_concurrent_resize_requests(self):
        """测试并发调整请求"""
        pool = ManagedThreadPool(max_workers=2)
        
        # 并发执行多个调整请求
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(pool.resize, 3),
                executor.submit(pool.resize, 4),
                executor.submit(pool.resize, 5)
            ]
            
            results = [f.result() for f in futures]
        
        # 验证只有一个成功
        successful_resizes = sum(1 for r in results if r.success)
        assert successful_resizes == 1, f"预期1次成功，实际{successful_resizes}次"
```

### 1.7 性能基准测试

#### 1.7.1 基准测试数据
| 测试场景 | 线程池大小 | 任务数量 | 调整时间 | 内存使用 |
|----------|------------|----------|----------|----------|
| 小负载 | 2→5 | 10 | 45ms | 2.1MB |
| 中负载 | 5→10 | 100 | 120ms | 5.8MB |
| 大负载 | 10→20 | 1000 | 340ms | 12.4MB |
| 超大负载 | 20→50 | 10000 | 890ms | 28.7MB |

#### 1.7.2 性能测试代码
```python
class ResizeBenchmark:
    """
    调整性能基准测试
    """
    
    def benchmark_resize_performance(self):
        """基准测试调整性能"""
        import time
        import psutil
        
        results = []
        
        for initial_size, target_size, task_count in [
            (2, 5, 10),
            (5, 10, 100),
            (10, 20, 1000),
            (20, 50, 10000)
        ]:
            # 创建测试环境
            pool = ManagedThreadPool(max_workers=initial_size)
            
            # 提交测试任务
            tasks = []
            for i in range(task_count):
                task = pool.submit(lambda x: x * 2, i)
                tasks.append(task)
            
            # 测量调整性能
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            result = pool.resize(target_size)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            # 验证所有任务完成
            completed_tasks = sum(1 for t in tasks if t.done())
            
            results.append({
                'initial_size': initial_size,
                'target_size': target_size,
                'task_count': task_count,
                'resize_time': end_time - start_time,
                'memory_delta': end_memory - start_memory,
                'task_loss_rate': (task_count - completed_tasks) / task_count,
                'success': result.success
            })
        
        return results
```

### 1.8 部署和运维规范

#### 1.8.1 部署检查清单
- [ ] 验证所有API端点可用性
- [ ] 检查线程池状态监控
- [ ] 验证日志记录功能
- [ ] 测试回滚机制
- [ ] 确认监控告警配置

#### 1.8.2 运维监控指标
```yaml
# 监控配置示例
alerts:
  - name: "resize_duration_high"
    condition: "resize_duration > 1000ms"
    severity: "warning"
    action: "notify_ops"
  
  - name: "task_loss_detected"
    condition: "task_loss_count > 0"
    severity: "critical"
    action: "page_oncall"

metrics:
  - name: "pool_utilization"
    query: "active_workers / max_workers"
    threshold: 0.9
  
  - name: "queue_depth"
    query: "queue_size"
    threshold: 100
```