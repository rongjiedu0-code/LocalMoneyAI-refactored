"""
数据库连接池：基于 sqlite3，支持上下文管理。
"""
import sqlite3
from contextlib import contextmanager
from typing import Optional
from logging_config import logger

_pool: Optional[str] = None  # 数据库路径


def init_pool(db_path: str = "money.db") -> None:
    """初始化连接池（简化版：只保存路径）。"""
    global _pool
    _pool = db_path
    logger.info(f"数据库初始化: {db_path}")


@contextmanager
def get_connection():
    """获取数据库连接（上下文管理器）。"""
    if _pool is None:
        raise RuntimeError("数据库未初始化，请先调用 init_pool()")

    conn = sqlite3.connect(_pool)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        conn.close()
