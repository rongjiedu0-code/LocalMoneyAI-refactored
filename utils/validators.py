"""
验证与解析工具：确保AI输出的JSON有效，提取金额等。
"""
import json
import re
from typing import Any, Dict, List

def safe_json_loads(text: str) -> Any:
    """
    从可能包含多余字符的模型输出中提取并解析JSON。
    策略：找第一个 { 或 [ 到最后一个 } 或 ]。
    """
    text = text.strip()
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 寻找JSON块
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end])
            except:
                pass
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end])
            except:
                pass
    raise ValueError(f"无法从模型输出解析JSON: {text[:100]}...")

def parse_amount(amount_str: Any) -> float:
    """
    将各种形式的金额字符串转为浮点数。
    处理：带人民币符号、逗号、负号方向。
    """
    if isinstance(amount_str, (int, float)):
        return float(amount_str)
    if not isinstance(amount_str, str):
        raise ValueError(f"不支持金额类型: {type(amount_str)}")
    
    # 移除货币符号和逗号
    cleaned = re.sub(r'[^\d\.\-]', '', amount_str)
    if not cleaned or cleaned == '-':
        raise ValueError(f"金额解析失败: {amount_str}")
    return float(cleaned)
