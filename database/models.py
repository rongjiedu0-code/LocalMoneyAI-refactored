"""
数据模型与验证：使用 dataclass 确保数据一致性。
"""
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Any
import json


@dataclass
class Transaction:
    date: str          # YYYY-MM-DD
    merchant: str
    amount: float      # 正数收入，负数支出
    category: str
    description: str = ""
    items: List[str] = None

    def __post_init__(self):
        if self.items is None:
            self.items = []
        # 验证日期格式
        try:
            date.fromisoformat(self.date)
        except ValueError:
            raise ValueError(f"Invalid date format: {self.date}")

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        """从字典构造，允许字段缺失。"""
        return cls(
            date=data.get("date", str(date.today())),
            merchant=data.get("merchant", "未知"),
            amount=float(data.get("amount", 0)),
            category=data.get("category", "其他支出"),
            description=data.get("description", ""),
            items=data.get("items", [])
        )


@dataclass
class QueryResult:
    natural_answer: str
    summary_data: Any   # 原始统计JSON
