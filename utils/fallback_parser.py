"""
当AI模型不可用时，使用正则规则进行基础交易提取。
保证系统在离线/故障时仍能记录核心信息。
"""
import re
from datetime import datetime
from typing import List
from services.ai.schemas import TransactionSchema
from logging_config import logger


class FallbackParser:
    """规则引擎：正则提取金额、日期、简单分类。"""

    # 金额正则：支持 "35元", "-35", "35.5", "￥35"
    AMOUNT_PATTERN = r'(-?\d+(?:\.\d+)?)\s*(?:元|块|￥| dollars)?'

    # 日期正则：优先 "2026-02-23" 或 "2月23日"
    DATE_PATTERN = r'(\d{4})[-年](\d{1,2})[-月](\d{1,2})日?'

    # 分类关键词映射
    CATEGORY_KEYWORDS = {
        "餐饮": ["饭", "餐", "吃", "咖啡", "奶茶", "火锅", "烧烤", "肯德基", "麦当劳"],
        "交通": ["地铁", "公交", "打车", "滴滴", "油", "停车", "高铁", "飞机"],
        "购物": ["买", "购", "淘宝", "京东", "拼多多", "超市", "商场"],
        "娱乐": ["电影", "游戏", "门票", "旅行", "唱歌"],
        "医疗": ["医院", "药", "体检", "挂号"],
    }

    @classmethod
    def parse_text(cls, text: str) -> List[TransactionSchema]:
        """
        从文本中提取交易（降级方案）。
        返回至少一笔交易，日期默认为今天。
        """
        logger.info(f"使用降级解析文本: {text[:50]}...")

        # 提取金额
        amounts = re.findall(cls.AMOUNT_PATTERN, text)
        if not amounts:
            # 无金额，返回一笔未知交易
            return [cls._create_unknown_transaction(text)]

        transactions = []
        for amount_str in amounts:
            try:
                amount = float(amount_str)
            except ValueError:
                continue

            # 推断类别
            category = cls._guess_category(text)
            # 推断日期
            date_match = re.search(cls.DATE_PATTERN, text)
            if date_match:
                year, month, day = date_match.groups()
                date = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            else:
                date = datetime.now().strftime("%Y-%m-%d")

            # 商家：取动词后的名词（简单规则）
            merchant = cls._extract_merchant(text, amount_str)

            tx = TransactionSchema(
                date=date,
                merchant=merchant or "未知",
                amount=amount,
                category=category,
                description=f"[降级解析] {text}",
                items=[]
            )
            transactions.append(tx)

        if not transactions:
            return [cls._create_unknown_transaction(text)]

        return transactions

    @classmethod
    def _create_unknown_transaction(cls, text: str) -> TransactionSchema:
        """创建一笔未知交易（金额0，需用户手动修正）。"""
        return TransactionSchema(
            date=datetime.now().strftime("%Y-%m-%d"),
            merchant="未知",
            amount=0.0,
            category="其他",
            description=f"[降级解析失败] {text}",
            items=[]
        )

    @classmethod
    def _guess_category(cls, text: str) -> str:
        """根据关键词猜测类别。"""
        text_lower = text.lower()
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return category
        return "其他"

    @classmethod
    def _extract_merchant(cls, text: str, amount_str: str) -> str:
        """
        尝试提取商家名：在金额前的连续非数字字符。
        示例："在星巴克花了35元" → "星巴克"
        """
        # 找到金额出现的位置
        amount_pos = text.find(amount_str)
        if amount_pos == -1:
            return ""

        # 取金额前的10个字符
        prefix = text[max(0, amount_pos-10):amount_pos].strip()
        # 去除常见动词
        prefix = re.sub(r'^(花了|消费|购买|在|于|用)\s*', '', prefix)
        # 如果prefix太短，返回空
        if len(prefix) < 2 or len(prefix) > 20:
            return ""
        return prefix
