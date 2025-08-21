#!/usr/bin/env python3
"""
动态调整线程池大小的单元测试
"""

import unittest
import time
import threading
from concurrent.futures import wait

from src.threadpool_manager import ThreadPoolManager
from src.threadpool_manager.managed_pool import ManagedThreadPool
from src.threadpool_manager.enums import TaskStatus, PoolStatus


class TestDynamicResize(unittest.TestCase):
    """测试动态调整线程池大小功能"""
    
    def setUp(self):
        """测试前置设置"""
        self.manager = ThreadPoolManager()
        self.pool_id = self.manager.create_pool("test_resize", 2)
    
    def tearDown(self):
        """测试后清理"""
        try:
            self.manager.force_close_pool(self.pool_id)
        except:
            pass
    
    def test_basic_resize_increase(self):
        """测试基本的大小增加"""
        # 提交一些任务
        task_ids = []
        for i in range(3):
            task_id = self.manager.submit_task(
                self.pool_id, 
                lambda x: time.sleep(x), 
                f"task-{i}", 
                0.1
            )
            task_ids.append(task_id)
        
        # 增加线程池大小
        result = self.manager.resize_pool(self.pool_id, 5)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['migrated_tasks'], 3)
        self.assertIn('成功调整线程池', result['message'])
        
        # 验证新的大小
        pool_info = self.manager.get_pool_info(self.pool_id)
        self.assertEqual(pool_info['max_workers'], 5)
    
    def test_basic_resize_decrease(self):
        """测试基本的大小减少"""
        # 先增加大小
        self.manager.resize_pool(self.pool_id, 5)
        
        # 提交一些任务
        task_ids = []
        for i in range(3):
            task_id = self.manager.submit_task(
                self.pool_id, 
                lambda x: time.sleep(x), 
                f"task-{i}", 
                0.1
            )
            task_ids.append(task_id)
        
        # 减少线程池大小
        result = self.manager.resize_pool(self.pool_id, 2)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['migrated_tasks'], 3)
        
        # 验证新的大小
        pool_info = self.manager.get_pool_info(self.pool_id)
        self.assertEqual(pool_info['max_workers'], 2)
    
    def test_resize_same_size(self):
        """测试调整到相同大小"""
        result = self.manager.resize_pool(self.pool_id, 2)
        
        self.assertTrue(result['success'])
        self.assertIn('已经是', result['message'])
    
    def test_resize_invalid_size(self):
        """测试无效的线程池大小"""
        result = self.manager.resize_pool(self.pool_id, 0)
        
        self.assertFalse(result['success'])
        self.assertIn('必须大于等于', result['message'])
    
    def test_resize_nonexistent_pool(self):
        """测试调整不存在的线程池"""
        with self.assertRaises(KeyError):
            self.manager.resize_pool("nonexistent", 5)
    
    def test_resize_with_running_tasks(self):
        """测试调整时有运行中任务"""
        # 提交长时间运行的任务
        task_ids = []
        for i in range(2):
            task_id = self.manager.submit_task(
                self.pool_id, 
                lambda x: time.sleep(x), 
                f"long-task-{i}", 
                2
            )
            task_ids.append(task_id)
        
        # 等待任务开始执行
        time.sleep(0.5)
        
        # 调整线程池大小
        result = self.manager.resize_pool(self.pool_id, 3)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['running_tasks'], 2)  # 有2个运行中任务
        
        # 等待任务完成
        for task_id in task_ids:
            task = self.manager.get_task(task_id)
            if task:
                task.future.result(timeout=3)
    
    def test_resize_info(self):
        """测试获取调整信息"""
        info = self.manager.get_pool_resize_info(self.pool_id)
        
        self.assertEqual(info['pool_id'], self.pool_id)
        self.assertEqual(info['current_max_workers'], 2)
        self.assertTrue(info['can_resize'])
        self.assertEqual(info['status'], 'running')
    
    def test_resize_closed_pool(self):
        """测试调整已关闭的线程池"""
        self.manager.close_pool(self.pool_id)
        
        pool = self.manager.get_pool(self.pool_id)
        result = pool.resize(5)
        
        self.assertFalse(result['success'])
        self.assertIn('当前状态为', result['message'])
    
    def test_task_migration_preserves_task_id(self):
        """测试任务迁移时保持任务ID不变"""
        # 提交任务
        task_id = self.manager.submit_task(
            self.pool_id, 
            lambda: "test result", 
            "test-task"
        )
        
        # 调整线程池大小
        self.manager.resize_pool(self.pool_id, 3)
        
        # 验证任务ID仍然存在
        task = self.manager.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, task_id)
        self.assertEqual(task.name, "test-task")
    
    def test_concurrent_resize_requests(self):
        """测试并发调整请求"""
        results = []
        
        def resize_worker(new_size):
            try:
                result = self.manager.resize_pool(self.pool_id, new_size)
                results.append(result)
            except Exception as e:
                results.append({'success': False, 'error': str(e)})
        
        # 启动多个并发调整请求
        threads = []
        for size in [3, 4, 5]:
            thread = threading.Thread(target=resize_worker, args=(size,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 至少有一个请求应该成功
        success_count = sum(1 for r in results if r.get('success', False))
        self.assertGreaterEqual(success_count, 1)
    
    def test_resize_with_large_task_queue(self):
        """测试有大量任务时的调整"""
        # 提交大量任务
        task_ids = []
        for i in range(50):
            task_id = self.manager.submit_task(
                self.pool_id, 
                lambda x: time.sleep(x), 
                f"batch-task-{i}", 
                0.01
            )
            task_ids.append(task_id)
        
        # 调整线程池大小
        result = self.manager.resize_pool(self.pool_id, 10)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['migrated_tasks'], 50)
        
        # 等待所有任务完成
        for task_id in task_ids:
            task = self.manager.get_task(task_id)
            if task and task.future:
                task.future.result(timeout=5)


class TestManagedPoolResize(unittest.TestCase):
    """测试ManagedThreadPool的resize方法"""
    
    def setUp(self):
        """测试前置设置"""
        self.pool = ManagedThreadPool("test-pool", "Test Pool", 2)
    
    def tearDown(self):
        """测试后清理"""
        try:
            self.pool.shutdown()
        except:
            pass
    
    def test_managed_pool_resize(self):
        """测试ManagedThreadPool的resize方法"""
        # 提交任务
        task_id = self.pool.submit(lambda: time.sleep(0.1), "test-task")
        
        # 调整大小
        result = self.pool.resize(5)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['migrated_tasks'], 1)
        
        # 验证任务仍然存在
        task = self.pool.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, task_id)


if __name__ == '__main__':
    unittest.main()