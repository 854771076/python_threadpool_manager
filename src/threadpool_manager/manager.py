"""
线程池管理器实现
"""

import uuid
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import logging

from .managed_pool import ManagedThreadPool
from .managed_task import ManagedTask
from .enums import PoolStatus, TaskStatus
from .exceptions import (
    PoolNotFoundError, 
    TaskNotFoundError, 
    PoolAlreadyExistsError,
    InvalidPoolStateError
)


class ThreadPoolManager:
    """
    线程池管理器，统一管理所有线程池和任务
    """
    
    def __init__(self):
        """初始化线程池管理器"""
        self.pools: Dict[str, ManagedThreadPool] = {}
        self.tasks: Dict[str, ManagedTask] = {}  # 全局任务注册表
        self._lock = threading.RLock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        self.logger = logging.getLogger(__name__)
        
        # 启动清理线程
        self._start_cleanup_thread()
    # 停止线程池未执行future
    def cancel_pool_tasks(self, pool_id: str) -> bool:
        """
        停止线程池未执行future
        
        Args:
            pool_id: 线程池ID
            
        Returns:
            bool: 是否成功停止
        """
        with self._lock:
            pool = self.get_pool(pool_id)
            pool.cancel_tasks()
            self.logger.info(f"Canceled tasks in pool {pool_id}")
            return True
            
    def create_pool(self, name: str = None, max_workers: int = None) -> str:
        """
        创建新的线程池
        
        Args:
            name: 线程池名称，如果为None则使用UUID
            max_workers: 最大工作线程数
            
        Returns:
            str: 线程池ID
        """
        with self._lock:
            pool_id = str(uuid.uuid4())
            if not name:
                name = f"pool-{pool_id[:8]}"
            
            # 检查名称是否已存在
            for pool in self.pools.values():
                if pool.name == name:
                    raise PoolAlreadyExistsError(f"Pool with name '{name}' already exists")
            
            pool = ManagedThreadPool(pool_id, name, max_workers)
            self.pools[pool_id] = pool
            
            self.logger.info(f"Created pool {pool_id} with name '{name}'")
            return pool_id
    
    def get_pool(self, pool_id: str) -> ManagedThreadPool:
        """
        获取指定线程池
        
        Args:
            pool_id: 线程池ID
            
        Returns:
            ManagedThreadPool: 线程池对象
            
        Raises:
            PoolNotFoundError: 如果线程池不存在
        """
        pool = self.pools.get(pool_id)
        if not pool:
            raise PoolNotFoundError(f"Pool {pool_id} not found")
        return pool
    
    def close_pool(self, pool_id: str, wait: bool = True) -> bool:
        """
        关闭线程池
        
        Args:
            pool_id: 线程池ID
            wait: 是否等待所有任务完成
            
        Returns:
            bool: 是否成功关闭
        """
        with self._lock:
            pool = self.get_pool(pool_id)
            
            try:
                pool.shutdown(wait=wait)
                
                # 清理该线程池的所有任务
                pool_tasks = [
                    task_id for task_id, task in self.tasks.items()
                    if task.pool_id == pool_id and task.is_done()
                ]
                for task_id in pool_tasks:
                    del self.tasks[task_id]
                
                # 从管理器中移除线程池
                del self.pools[pool_id]
                
                self.logger.info(f"Closed pool {pool_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error closing pool {pool_id}: {e}")
                return False
    
    def force_close_pool(self, pool_id: str) -> List[str]:
        """
        强制关闭线程池，取消所有未完成的任务
        
        Args:
            pool_id: 线程池ID
            
        Returns:
            List[str]: 被取消的任务ID列表
        """
        with self._lock:
            pool = self.get_pool(pool_id)
            
            # 获取该线程池的所有活跃任务
            active_tasks = [
                task_id for task_id, task in self.tasks.items()
                if task.pool_id == pool_id and not task.is_done()
            ]
            
            # 立即关闭线程池
            cancelled_tasks = pool.shutdown_now()
            
            # 清理任务
            for task_id in active_tasks:
                if task_id in self.tasks:
                    del self.tasks[task_id]
            
            # 移除线程池
            del self.pools[pool_id]
            
            self.logger.info(f"Force closed pool {pool_id}, cancelled {len(active_tasks)} tasks")
            return active_tasks
    
    def submit_task(self, pool_id: str, task_func: Callable, 
                   task_name: str = None, *args, **kwargs) -> str:
        """
        向指定线程池提交任务
        
        Args:
            pool_id: 线程池ID
            task_func: 要执行的任务函数
            task_name: 任务名称
            *args, **kwargs: 任务函数参数
            
        Returns:
            str: 任务ID
            
        Raises:
            PoolNotFoundError: 如果线程池不存在
        """
        pool = self.get_pool(pool_id)
        
        with self._lock:
            task_id,future = pool.submit(task_func, task_name, *args, **kwargs)
            task = pool.get_task(task_id)
            
            # 注册到全局任务表
            self.tasks[task_id] = task
            
            self.logger.info(f"Submitted task {task_id} to pool {pool_id}")
            return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        pool = self.get_pool(task.pool_id)
        success = pool.cancel_task(task_id)
        
        if success and task.is_done():
            # 清理已完成的任务
            del self.tasks[task_id]
        
        return success
    
    def stop_task(self, task_id: str) -> bool:
        """
        停止正在执行的任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功停止
        """
        # 注意：Python的ThreadPoolExecutor不支持直接停止正在执行的任务
        # 这里我们只能通过取消来实现，对于已开始的任务无法强制停止
        return self.cancel_task(task_id)
    
    def get_task(self, task_id: str) -> ManagedTask:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            ManagedTask: 任务对象
            
        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        task = self.tasks.get(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return task
    
    def list_pools(self) -> List[Dict[str, Any]]:
        """
        获取所有线程池信息
        
        Returns:
            List[Dict]: 线程池信息列表
        """
        with self._lock:
            return [pool.get_info() for pool in self.pools.values()]
    
    def list_tasks(self, pool_id: str = None) -> List[Dict[str, Any]]:
        """
        获取任务列表
        
        Args:
            pool_id: 线程池ID，如果为None则返回所有任务
            
        Returns:
            List[Dict]: 任务信息列表
        """
        with self._lock:
            if pool_id:
                # 获取指定线程池的任务
                pool = self.get_pool(pool_id)
                return pool.list_tasks()
            else:
                # 获取所有任务
                return [task for pool in self.pools.values() for task in pool.list_tasks()]
    def clear_stopped_pools(self):
        """清理已停止的线程池"""
        with self._lock:
            stopped_pools = [
                pool_id for pool_id, pool in self.pools.items()
                if pool.status in [PoolStatus.STOPPED,PoolStatus.TERMINATED]
            ]
            
            for pool_id in stopped_pools:
                del self.pools[pool_id]
    def cleanup_completed_tasks(self) -> int:
        """
        清理已完成的任务
        
        Returns:
            int: 清理的任务数量
        """
        with self._lock:
            completed_task_ids = [
                task_id for task_id, task in self.tasks.items()
                if task.is_done()
            ]
            
            for task_id in completed_task_ids:
                del self.tasks[task_id]
            
            # 清理每个线程池的已完成任务
            total_cleaned = len(completed_task_ids)
            for pool in self.pools.values():
                total_cleaned += pool.cleanup_completed_tasks()
            
            if total_cleaned > 0:
                self.logger.info(f"Cleaned up {total_cleaned} completed tasks")
            
            return total_cleaned
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self._lock:
            total_tasks = len(self.tasks)
            active_tasks = len([t for t in self.tasks.values() if not t.is_done()])
            
            return {
                'total_pools': len(self.pools),
                'total_tasks': total_tasks,
                'active_tasks': active_tasks,
                'completed_tasks': total_tasks - active_tasks
            }
    
    def _start_cleanup_thread(self):
        """启动清理线程"""
        def cleanup_worker():
            while not self._stop_cleanup.wait(timeout=300):  # 每5分钟清理一次
                try:
                    self.cleanup_completed_tasks()
                    self.clear_stopped_pools()

                except Exception as e:
                    self.logger.error(f"Error in cleanup thread: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def shutdown(self):
        """关闭管理器，清理所有资源"""
        self.logger.info("Shutting down ThreadPoolManager")
        
        # 停止清理线程
        self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        # 关闭所有线程池
        with self._lock:
            for pool_id in list(self.pools.keys()):
                try:
                    self.close_pool(pool_id, wait=False)
                except Exception as e:
                    self.logger.error(f"Error closing pool {pool_id}: {e}")
            
            self.pools.clear()
            self.tasks.clear()
        
        self.logger.info("ThreadPoolManager shutdown complete")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown()
    
    def resize_pool(self, pool_id: str, new_max_workers: int) -> Dict[str, Any]:
        """
        动态调整指定线程池的最大工作线程数
        
        Args:
            pool_id: 线程池ID
            new_max_workers: 新的最大工作线程数
            
        Returns:
            Dict[str, Any]: 调整结果信息
            
        Raises:
            KeyError: 如果线程池不存在
            ValueError: 如果参数无效
        """
        with self._lock:
            if pool_id not in self.pools:
                raise KeyError(f"线程池 {pool_id} 不存在")
            
            pool = self.pools[pool_id]
            result = pool.resize(new_max_workers)
            
            if result['success']:
                self.logger.info(
                    f"成功调整线程池 {pool_id} 大小: "
                    f"max_workers={new_max_workers}, "
                    f"migrated_tasks={result.get('migrated_tasks', 0)}, "
                    f"completed_tasks={result.get('completed_tasks', 0)}"
                )
            else:
                self.logger.error(f"调整线程池 {pool_id} 大小失败: {result['message']}")
            
            return result
    
    def get_pool_resize_info(self, pool_id: str) -> Dict[str, Any]:
        """
        获取线程池调整大小的相关信息
        
        Args:
            pool_id: 线程池ID
            
        Returns:
            Dict[str, Any]: 包含当前状态和调整建议的信息
            
        Raises:
            KeyError: 如果线程池不存在
        """
        with self._lock:
            if pool_id not in self.pools:
                raise KeyError(f"线程池 {pool_id} 不存在")
            
            pool = self.pools[pool_id]
            return pool.get_resize_info()