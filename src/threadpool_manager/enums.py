"""
枚举类型定义
"""

from enum import Enum


class PoolStatus(Enum):
    """线程池状态"""
    RUNNING = "running"
    SHUTDOWN = "shutdown"
    STOPPED = "stopped"
    TERMINATED = "terminated"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4