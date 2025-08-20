"""
线程池管理器包

提供线程池和任务的统一管理功能
"""

from .manager import ThreadPoolManager
from .managed_pool import ManagedThreadPool
from .managed_task import ManagedTask
from .exceptions import ThreadPoolError, TaskError

__version__ = "1.0.0"
__all__ = ["ThreadPoolManager", "ManagedThreadPool", "ManagedTask", "ThreadPoolError", "TaskError"]