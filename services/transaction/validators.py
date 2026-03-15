"""
交易相关验证：输入校验、业务规则。
"""
import os
from pathlib import Path
from typing import List
from logging_config import logger

class ValidationError(Exception):
    pass

def validate_image_file(path: str):
    """验证图片文件。"""
    p = Path(path)
    if not p.exists():
        raise ValidationError(f"文件不存在: {path}")
    if p.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
        raise ValidationError(f"不支持的文件格式: {p.suffix}")
    if p.stat().st_size > 10 * 1024 * 1024:  # 10MB
        raise ValidationError("文件过大（限制10MB）")

def validate_text_input(text: str):
    """验证文本输入。"""
    if not text or not text.strip():
        raise ValidationError("输入不能为空")
    if len(text) > 1000:
        raise ValidationError("输入过长（限制1000字符）")

def validate_category(category: str, allowed: List[str]) -> bool:
    return category in allowed

def validate_amount(amount: float) -> bool:
    """金额合理性检查（比如单笔不超过10万）。"""
    return -100000 < amount < 100000
