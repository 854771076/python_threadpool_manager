"""
自定义异常类
"""


class ThreadPoolError(Exception):
    """线程池相关异常"""
    pass


class TaskError(Exception):
    """任务相关异常"""
    pass


class PoolNotFoundError(ThreadPoolError):
    """线程池未找到异常"""
    pass


class TaskNotFoundError(TaskError):
    """任务未找到异常"""
    pass


class PoolAlreadyExistsError(ThreadPoolError):
    """线程池已存在异常"""
    pass


class InvalidPoolStateError(ThreadPoolError):
    """线程池状态无效异常"""
    pass