"""
AI服务数据模型：定义交易记录结构。
"""
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime


@dataclass
class TransactionSchema:
    """单条交易记录的数据模型"""

    date: str
    merchant: str
    amount: float
    category: str
    description: str = ""
    items: List[str] = None  # 明细列表
    confidence: float = 0.8

    def __post_init__(self):
        """后处理：确保 items 是列表"""
        if self.items is None:
            self.items = []
        elif isinstance(self.items, str):
            try:
                import json
                self.items = json.loads(self.items)
            except:
                self.items = []

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'TransactionSchema':
        """从字典创建实例"""
        # 确保必要字段存在
        required = ['date', 'merchant', 'amount', 'category']
        for field in required:
            if field not in data:
                raise ValueError(f"缺少必要字段: {field}")

        return cls(
            date=str(data['date']),
            merchant=str(data['merchant']),
            amount=float(data['amount']),
            category=str(data['category']),
            description=str(data.get('description', '')),
            items=str(data.get('items', '[]')),
            confidence=float(data.get('confidence', 0.8))
        )

    def is_valid(self) -> bool:
        """
        验证该交易是否包含有效内容。
        规则：金额不为 0, 且类别不为空。
        """
        if not self.category or self.category.strip() == "" or self.category == "未知":
            return False
        if abs(self.amount) < 0.01:
            return False
        return True


# 可选：定义其他相关模型
@dataclass
class AIExtractResponse:
    """AI提取响应"""
    transactions: List[TransactionSchema]
    total_count: int
    processing_time: float
    model_used: str
