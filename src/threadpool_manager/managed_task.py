"""
任务包装器实现
"""

import uuid
from datetime import datetime
from typing import Any, Optional, Callable
from concurrent.futures import Future

from .enums import TaskStatus


class ManagedTask:
    """
    对任务的包装，提供额外的管理功能
    """
    
    def __init__(self, task_id: str, name: str, pool_id: str, task_func: Callable, 
                 future: Future=None, args=(), kwargs=None):
        """
        初始化任务包装器
        
        Args:
            task_id: 任务唯一标识
            name: 任务名称
            pool_id: 所属线程池ID
            future: concurrent.futures.Future对象
            task_func: 要执行的任务函数
            *args, **kwargs: 任务函数的参数
        """
        self.task_id = task_id
        self.name = name
        self.pool_id = pool_id
        self.future = future
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs or {}
        
        # 时间相关
        self.submit_time = datetime.now()
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # 状态相关
        self.status = TaskStatus.PENDING
        self.result: Any = None
        self.exception: Optional[Exception] = None
        
        # 添加回调以跟踪状态变化
        
    def set_future(self, future: Future):
        """设置任务的Future对象"""
        self.future = future
        self.future.add_done_callback(self._on_task_complete)
    def _on_task_complete(self, future: Future):
        """
        任务完成时的回调函数
        
        Args:
            future: 完成的任务future
        """
        self.end_time = datetime.now()
        
        if future.cancelled():
            self.status = TaskStatus.CANCELLED
        elif future.exception():
            self.status = TaskStatus.FAILED
            self.exception = future.exception()
        else:
            self.status = TaskStatus.COMPLETED
            self.result = future.result()
    
    def mark_running(self):
        """标记任务开始运行"""
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.RUNNING
            self.start_time = datetime.now()
    
    def cancel(self) -> bool:
        """
        取消任务
        
        Returns:
            bool: 是否成功取消
        """
        if self.status == TaskStatus.PENDING:
            success = self.future.cancel()
            if success:
                self.status = TaskStatus.CANCELLED
                self.end_time = datetime.now()
            return success
        elif self.status == TaskStatus.RUNNING:
            # 对于运行中的任务，尝试取消
            success = self.future.cancel()
            if success:
                self.status = TaskStatus.CANCELLED
                self.end_time = datetime.now()
            return success
        return False
    
    def get_status(self) -> TaskStatus:
        """获取任务当前状态"""
        return self.status
    
    def get_result(self, timeout: Optional[float] = None) -> Any:
        """
        获取任务执行结果
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            任务执行结果
            
        Raises:
            Exception: 如果任务执行失败，抛出异常
        """
        return self.future.result(timeout)
    
    def get_info(self) -> dict:
        """
        获取任务详细信息
        
        Returns:
            dict: 任务信息字典
        """
        return {
            'task_id': self.task_id,
            'name': self.name,
            'pool_id': self.pool_id,
            'status': self.status.value,
            'submit_time': self.submit_time.isoformat(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'result': str(self.result) if self.result is not None else None,
            'exception': str(self.exception) if self.exception else None,
            'running_time': self._get_running_time()
        }
    def start(self, *args, **kwargs):
        """启动任务"""
        self.mark_running()
        return self.task_func(*self.args, **self.kwargs) 
    def _get_running_time(self) -> Optional[float]:
        """
        获取任务运行时间（秒）
        
        Returns:
            float: 运行时间（秒），如果未开始运行返回None
        """
        if not self.start_time:
            return None
        
        end_time = self.end_time or datetime.now()
        return (end_time - self.start_time).total_seconds()
    
    def is_done(self) -> bool:
        """检查任务是否已完成"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
    
    def is_running(self) -> bool:
        """检查任务是否正在运行"""
        return self.status == TaskStatus.RUNNING
    
    def is_pending(self) -> bool:
        """检查任务是否待执行"""
        return self.status == TaskStatus.PENDING