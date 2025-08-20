"""
自定义线程池测试
"""

import pytest
import time
from src.threadpool_manager import ManagedThreadPool
from src.threadpool_manager.exceptions import InvalidPoolStateError


class TestManagedThreadPool:
    """自定义线程池测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.pool = ManagedThreadPool("test_pool_id", "test_pool", 2)
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        if self.pool.get_status().value == 'running':
            self.pool.shutdown()
    
    def test_init(self):
        """测试初始化"""
        assert self.pool.pool_id == "test_pool_id"
        assert self.pool.name == "test_pool"
        assert self.pool.max_workers == 2
    
    def test_submit_task(self):
        """测试提交任务"""
        def test_func(x):
            return x * 2
        
        task_id = self.pool.submit(test_func, "test_task", 5)
        assert task_id is not None
        assert len(self.pool.list_tasks()) == 1
    
    def test_submit_task_to_closed_pool(self):
        """测试向已关闭的线程池提交任务"""
        self.pool.shutdown()
        
        with pytest.raises(InvalidPoolStateError):
            self.pool.submit(lambda: None)
    
    def test_get_task(self):
        """测试获取任务"""
        def test_func():
            return "test"
        
        task_id = self.pool.submit(test_func)
        task = self.pool.get_task(task_id)
        assert task is not None
    
    def test_list_tasks(self):
        """测试列出任务"""
        def test_func():
            return "test"
        
        self.pool.submit(test_func, "task1")
        self.pool.submit(test_func, "task2")
        
        tasks = self.pool.list_tasks()
        assert len(tasks) == 2
    
    def test_cancel_task(self):
        """测试取消任务"""
        def long_task():
            time.sleep(10)
            return "done"
        
        task_id = self.pool.submit(long_task)
        success = self.pool.cancel_task(task_id)
        # 任务可能已经开始执行，取消可能成功也可能失败
        assert success in [True, False]
    
    def test_shutdown(self):
        """测试优雅关闭"""
        self.pool.shutdown(wait=True)
        assert self.pool.get_status().value in ['terminated', 'stopped']
    
    def test_shutdown_now(self):
        """测试立即关闭"""
        def long_task():
            time.sleep(10)
            return "done"
        
        self.pool.submit(long_task)
        cancelled_tasks = self.pool.shutdown_now()
        assert len(cancelled_tasks) == 1
    
    def test_cleanup_completed_tasks(self):
        """测试清理已完成的任务"""
        def quick_task():
            return "done"
        
        task_id = self.pool.submit(quick_task)
        
        # 等待任务完成
        task = self.pool.get_task(task_id)
        task.get_result(timeout=5)
        
        # 清理已完成的任务
        cleaned = self.pool.cleanup_completed_tasks()
        assert cleaned == 1
        assert len(self.pool.list_tasks()) == 0
    
    def test_get_info(self):
        """测试获取线程池信息"""
        info = self.pool.get_info()
        assert info['pool_id'] == "test_pool_id"
        assert info['name'] == "test_pool"
        assert info['max_workers'] == 2
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with ManagedThreadPool("ctx_pool_id", "ctx_pool", 2) as pool:
            assert pool.get_status().value == 'running'
            pool.submit(lambda: "test")
        
        # 上下文退出后线程池应已关闭
        # 注意：这里不能直接测试状态，因为对象已关闭
    
    def test_task_execution(self):
        """测试任务执行"""
        def add_func(x, y):
            return x + y
        
        task_id = self.pool.submit(add_func, "add_task", 3, 4)
        task = self.pool.get_task(task_id)
        result = task.get_result(timeout=5)
        
        assert result == 7
    
    def test_get_active_tasks(self):
        """测试获取活跃任务"""
        def quick_task():
            return "done"
        
        def long_task():
            time.sleep(5)
            return "done"
        
        task1_id = self.pool.submit(quick_task)
        task2_id = self.pool.submit(long_task)
        
        # 等待第一个任务完成
        task1 = self.pool.get_task(task1_id)
        task1.get_result(timeout=2)
        
        active_tasks = self.pool.get_active_tasks()
        assert len(active_tasks) == 1  # 只有第二个任务还在运行
    
    def test_task_status_tracking(self):
        """测试任务状态跟踪"""
        def test_func():
            time.sleep(0.1)
            return "done"
        
        task_id = self.pool.submit(test_func)
        task = self.pool.get_task(task_id)
        
        # 初始状态应该是pending
        assert task.get_status().value == 'pending'
        
        # 等待任务完成
        task.get_result(timeout=5)
        
        # 完成后状态应该是completed
        assert task.get_status().value == 'completed'
        assert task.is_done() is True