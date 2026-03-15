"""
重试装饰器：用于网络请求等易失败操作。
"""
import time
import functools
from typing import Callable, TypeVar, Any
from logging_config import logger

T = TypeVar('T')


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    重试装饰器。

    参数:
        max_attempts: 最大尝试次数（含首次）
        delay: 初始延迟秒数
        backoff: 延迟倍数（指数退避）
        exceptions: 捕获的异常类型元组

    示例:
        @retry(max_attempts=3, delay=1)
        def call_ollama(...):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"尝试 {attempt}/{max_attempts}: {func.__name__}")
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(f"重试耗尽，最终失败: {func.__name__} - {e}")
                        raise last_exception

                    logger.warning(f"尝试 {attempt} 失败，{current_delay:.1f}s后重试: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff

            raise last_exception  # 不应执行到这里
        return wrapper
    return decorator
