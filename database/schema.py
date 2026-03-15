"""
数据库模式定义：建表语句。
"""
from .connection import get_connection
from logging_config import logger

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    merchant TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT DEFAULT '',
    items TEXT DEFAULT '[]',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_category ON transactions(category);
"""


def init_schema() -> None:
    """初始化数据库模式。"""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
    logger.info("数据库模式初始化完成")
