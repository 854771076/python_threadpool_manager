"""
自定义线程池实现
"""

import uuid
import threading
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor, Future

from .enums import PoolStatus, TaskStatus
from .managed_task import ManagedTask
from .exceptions import InvalidPoolStateError


class ManagedThreadPool:
    """
    自定义线程池，提供任务管理和状态跟踪功能
    """
    
    def __init__(self, pool_id: str, name: str, max_workers: int = None):
        """
        初始化线程池
        
        Args:
            pool_id: 线程池唯一标识
            name: 线程池名称
            max_workers: 最大工作线程数
        """
        self.pool_id = pool_id
        self.name = name
        self.max_workers = max_workers or 5
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.status = PoolStatus.RUNNING
        
        # 任务管理
        self.tasks: Dict[str, ManagedTask] = {}
        self._lock = threading.RLock()
    def cancel_tasks(self):
        """取消所有未运行任务"""
        with self._lock:
            for task in self.tasks.values():
                if not task.is_done() and not task.is_running():
                    task.cancel()
    def submit(self, task_func: Callable, task_name: str = None, 
               *args, **kwargs) -> str:
        """
        提交任务到线程池
        
        Args:
            task_func: 要执行的任务函数
            task_name: 任务名称，如果为None则使用UUID
            *args, **kwargs: 任务函数参数
            
        Returns:
            str: 任务ID
            
        Raises:
            InvalidPoolStateError: 如果线程池已关闭
        """
        with self._lock:
            if self.status != PoolStatus.RUNNING:
                raise InvalidPoolStateError(f"Pool {self.pool_id} is not running")
            
            # 生成任务ID和名称
            task_id = str(uuid.uuid4())
            if not task_name:
                task_name = f"task-{task_id[:8]}"
             # 创建任务包装器
            managed_task = ManagedTask(
                task_id=task_id,
                name=task_name,
                pool_id=self.pool_id,
                task_func=task_func,
                args=args,
                kwargs=kwargs
            )
            # 存储任务
            self.tasks[task_id] = managed_task

            # 提交任务到线程池
            future = self.executor.submit(managed_task.start)
            # 设置任务的Future对象
            managed_task.set_future(future)
            
           
            
            return task_id
    
    def get_task(self, task_id: str) -> Optional[ManagedTask]:
        """
        获取指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            ManagedTask: 任务对象，如果未找到返回None
        """
        return self.tasks.get(task_id)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有任务信息
        
        Returns:
            List[Dict]: 任务信息列表
        """
        with self._lock:
            return [task.get_info() for task in self.tasks.values()]
    
    def get_active_tasks(self) -> List[ManagedTask]:
        """
        获取活跃任务（未完成的任务）
        
        Returns:
            List[ManagedTask]: 活跃任务列表
        """
        return [task for task in self.tasks.values() if not task.is_done()]
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        task = self.get_task(task_id)
        if task:
            return task.cancel()
        return False
    
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
            
            return len(completed_task_ids)
    
    def shutdown(self, wait: bool = True):
        """
        优雅关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
        """
        with self._lock:
            if self.status == PoolStatus.RUNNING:
                self.status = PoolStatus.SHUTDOWN
                self.executor.shutdown(wait=wait)
                if wait:
                    self.status = PoolStatus.TERMINATED
                else:
                    self.status = PoolStatus.STOPPED
    
    def shutdown_now(self) -> List[Any]:
        """
        立即关闭线程池，尝试停止所有正在执行的任务
        
        Returns:
            List[Any]: 未执行的任务列表
        """
        with self._lock:
            if self.status == PoolStatus.RUNNING:
                self.status = PoolStatus.STOPPED
                
                # 取消所有待执行的任务
                cancelled_tasks = []
                for task in self.tasks.values():
                    if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                        cancelled_tasks.append(task)
                
                # 立即关闭线程池
                self.executor.shutdown(wait=False)
                
                return cancelled_tasks
        return []
    
    def get_status(self) -> PoolStatus:
        """获取线程池当前状态"""
        return self.status
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取线程池详细信息
        
        Returns:
            Dict[str, Any]: 线程池信息
        """
        active_tasks = self.get_active_tasks()
        all_tasks = list(self.tasks.values())
        
        return {
            'pool_id': self.pool_id,
            'name': self.name,
            'status': self.status.value,
            'max_workers': self.max_workers,
            'total_tasks': len(all_tasks),
            'active_tasks': len(active_tasks),
            'pending_tasks': len([t for t in all_tasks if t.status == TaskStatus.PENDING]),
            'running_tasks': len([t for t in all_tasks if t.status == TaskStatus.RUNNING]),
            'completed_tasks': len([t for t in all_tasks if t.is_done()]),
            'cancelled_tasks': len([t for t in all_tasks if t.status == TaskStatus.CANCELLED]),
            'failed_tasks': len([t for t in all_tasks if t.status == TaskStatus.FAILED])
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown(wait=True)