"""
数据库包初始化：导出核心函数。
"""
from .connection import init_pool, get_connection
from .schema import init_schema

__all__ = ["init_pool", "get_connection", "init_schema"]
