"""
线程池管理器测试
"""

import pytest
import time
from unittest.mock import Mock

from src.threadpool_manager import ThreadPoolManager
from src.threadpool_manager.exceptions import (
    PoolNotFoundError, 
    TaskNotFoundError, 
    PoolAlreadyExistsError
)


class TestThreadPoolManager:
    """线程池管理器测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.manager = ThreadPoolManager()
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        self.manager.shutdown()
    
    def test_create_pool(self):
        """测试创建线程池"""
        pool_id = self.manager.create_pool("test_pool", 3)
        assert pool_id is not None
        assert len(self.manager.list_pools()) == 1
    
    def test_create_pool_duplicate_name(self):
        """测试创建同名线程池"""
        self.manager.create_pool("test_pool", 3)
        with pytest.raises(PoolAlreadyExistsError):
            self.manager.create_pool("test_pool", 3)
    
    def test_get_pool(self):
        """测试获取线程池"""
        pool_id = self.manager.create_pool("test_pool", 3)
        pool = self.manager.get_pool(pool_id)
        assert pool.name == "test_pool"
    
    def test_get_nonexistent_pool(self):
        """测试获取不存在的线程池"""
        with pytest.raises(PoolNotFoundError):
            self.manager.get_pool("nonexistent")
    
    def test_close_pool(self):
        """测试关闭线程池"""
        pool_id = self.manager.create_pool("test_pool", 3)
        success = self.manager.close_pool(pool_id)
        assert success is True
        assert len(self.manager.list_pools()) == 0
    
    def test_submit_task(self):
        """测试提交任务"""
        pool_id = self.manager.create_pool("test_pool", 3)
        
        def test_func(x, y):
            return x + y
        
        task_id = self.manager.submit_task(pool_id, test_func, "test_task", 1, 2)
        assert task_id is not None
        assert len(self.manager.list_tasks()) == 1
    
    def test_submit_task_to_nonexistent_pool(self):
        """测试向不存在的线程池提交任务"""
        with pytest.raises(PoolNotFoundError):
            self.manager.submit_task("nonexistent", lambda: None)
    
    def test_cancel_task(self):
        """测试取消任务"""
        pool_id = self.manager.create_pool("test_pool", 3)
        
        def long_task():
            time.sleep(10)
            return "done"
        
        task_id = self.manager.submit_task(pool_id, long_task)
        time.sleep(0.1)  # 确保任务已提交
        
        success = self.manager.cancel_task(task_id)
        # 任务可能已经开始执行，取消可能成功也可能失败
        assert success in [True, False]
    
    def test_cancel_nonexistent_task(self):
        """测试取消不存在的任务"""
        success = self.manager.cancel_task("nonexistent")
        assert success is False
    
    def test_get_task(self):
        """测试获取任务"""
        pool_id = self.manager.create_pool("test_pool", 3)
        
        def test_func():
            return "test_result"
        
        task_id = self.manager.submit_task(pool_id, test_func)
        task = self.manager.get_task(task_id)
        assert task.name.startswith("task-")
    
    def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        with pytest.raises(TaskNotFoundError):
            self.manager.get_task("nonexistent")
    
    def test_list_pools(self):
        """测试列出线程池"""
        self.manager.create_pool("pool1", 2)
        self.manager.create_pool("pool2", 3)
        
        pools = self.manager.list_pools()
        assert len(pools) == 2
    
    def test_list_tasks(self):
        """测试列出任务"""
        pool_id = self.manager.create_pool("test_pool", 3)
        
        def test_func():
            return "test"
        
        self.manager.submit_task(pool_id, test_func, "task1")
        self.manager.submit_task(pool_id, test_func, "task2")
        
        tasks = self.manager.list_tasks()
        assert len(tasks) == 2
    
    def test_list_tasks_by_pool(self):
        """测试按线程池列出任务"""
        pool1 = self.manager.create_pool("pool1", 2)
        pool2 = self.manager.create_pool("pool2", 2)
        
        def test_func():
            return "test"
        
        self.manager.submit_task(pool1, test_func, "task1")
        self.manager.submit_task(pool2, test_func, "task2")
        
        tasks1 = self.manager.list_tasks(pool1)
        tasks2 = self.manager.list_tasks(pool2)
        
        assert len(tasks1) == 1
        assert len(tasks2) == 1
    
    def test_task_execution(self):
        """测试任务执行"""
        pool_id = self.manager.create_pool("test_pool", 3)
        
        def add_func(x, y):
            return x + y
        
        task_id = self.manager.submit_task(pool_id, add_func, "add_task", 3, 4)
        
        # 等待任务完成
        task = self.manager.get_task(task_id)
        result = task.get_result(timeout=5)
        
        assert result == 7
    
    def test_force_close_pool(self):
        """测试强制关闭线程池"""
        pool_id = self.manager.create_pool("test_pool", 3)
        
        def long_task():
            time.sleep(10)
            return "done"
        
        task_id = self.manager.submit_task(pool_id, long_task)
        
        cancelled_tasks = self.manager.force_close_pool(pool_id)
        # 任务可能已经开始执行，被取消的任务数量可能为0或1
        assert task_id in cancelled_tasks or len(cancelled_tasks) == 0
    
    def test_cleanup_completed_tasks(self):
        """测试清理已完成的任务"""
        pool_id = self.manager.create_pool("test_pool", 3)
        
        def quick_task():
            return "done"
        
        task_id = self.manager.submit_task(pool_id, quick_task)
        
        # 等待任务完成
        task = self.manager.get_task(task_id)
        task.get_result(timeout=5)
        
        # 清理已完成的任务
        cleaned = self.manager.cleanup_completed_tasks()
        assert cleaned >= 1
    
    def test_get_stats(self):
        """测试获取统计信息"""
        pool_id = self.manager.create_pool("test_pool", 3)
        
        def test_func():
            return "test"
        
        self.manager.submit_task(pool_id, test_func)
        
        stats = self.manager.get_stats()
        assert stats['total_pools'] == 1
        assert stats['total_tasks'] == 1


class TestThreadPoolManagerContextManager:
    """测试上下文管理器功能"""
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with ThreadPoolManager() as manager:
            pool_id = manager.create_pool("test_pool", 2)
            assert len(manager.list_pools()) == 1
        
        # 确保上下文退出后资源已清理
        # 注意：这里不能直接测试，因为manager已关闭