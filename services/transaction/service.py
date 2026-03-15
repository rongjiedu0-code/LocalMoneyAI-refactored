"""
交易服务：业务逻辑层（重构版）。
依赖：
  - AIExtractor: 文本/图片提取
  - TransactionRepository: 数据持久化
  - AIAnswerer: 智能问答（可选，延迟初始化）
"""
from typing import List, Dict, Any, Optional
import sqlite3
from services.ai.extractor import AIExtractor
from services.ai.answerer import AIAnswerer
from services.ai.client import OllamaClient
from services.transaction.repository import TransactionRepository
from services.transaction.validators import validate_category, validate_amount
from logging_config import logger
from config_loader import config
import time


class TransactionService:
    """
    交易业务服务。
    
    职责：
    - 接收文本/图片输入
    - 调用 AI 提取交易
    - 验证并保存到数据库
    - 查询与统计
    - 智能问答
    """
    
    def __init__(
        self,
        ai_extractor: AIExtractor = None,
        repository: TransactionRepository = None,
        answerer: AIAnswerer = None
    ):
        # 依赖注入（默认延迟创建）
        self.ai = ai_extractor or self._default_extractor()
        self.repo = repository or TransactionRepository()
        self._answerer = answerer
        self.logger = logger
    
    def _default_extractor(self) -> AIExtractor:
        """创建默认的 AIExtractor（延迟初始化）"""
        from services.ai import create_extractor, OllamaClient, prompt_manager
        client = OllamaClient()
        return create_extractor(
            client=client,
            config=config,
            prompt_manager=prompt_manager,
            fallback_enabled=config.ENABLE_FALLBACK
        )
    
    def _get_answerer(self) -> AIAnswerer:
        """懒加载 AIAnswerer"""
        if self._answerer is None:
            client = OllamaClient()
            self._answerer = AIAnswerer(
                client=client,
                model=config.TEXT_MODEL
            )
        return self._answerer
    
    # ============ 公共 API ============
    
    def extract_from_text(self, text: str) -> List[Dict]:
        """从文本提取交易，不直接入库。用于暂存区 (Staging)。"""
        self.logger.info(f"提取交易文本: {text[:50]}...")
        start = time.time()
        
        try:
            transactions = self.ai.from_text(text)
            validated_txs = []
            for tx in transactions:
                self._validate_tx(tx)
                validated_txs.append(tx.to_dict() if hasattr(tx, 'to_dict') else tx)
                
            elapsed = time.time() - start
            self.logger.info(f"✅ 文本提取完成，耗时{elapsed:.2f}s，共{len(validated_txs)}笔")
            return validated_txs
        except Exception as e:
            self.logger.error(f"提取失败: {e}", exc_info=True)
            raise

    def add_from_text(self, text: str) -> List[Dict]:
        """
        从文本添加交易。
        流程：
        1. AI 提取交易列表并验证
        2. 批量入库
        3. 返回添加的交易数据
        """
        validated_txs = self.extract_from_text(text)
        if validated_txs:
            self.save_transactions(validated_txs)
        return validated_txs
    
    def extract_from_image(self, image_path: str) -> List[Dict]:
        """从图片提取交易，不直接入库。用于暂存区 (Staging)。"""
        self.logger.info(f"提取图片交易: {image_path}")
        start = time.time()
        
        try:
            transactions = self.ai.from_image(image_path)
            validated_txs = []
            for tx in transactions:
                self._validate_tx(tx)
                validated_txs.append(tx.to_dict() if hasattr(tx, 'to_dict') else tx)
                
            elapsed = time.time() - start
            self.logger.info(f"✅ 图片提取完成，耗时{elapsed:.2f}s，共{len(validated_txs)}笔")
            return validated_txs
        except Exception as e:
            self.logger.error(f"图片提取失败: {e}", exc_info=True)
            raise

    def add_from_image(self, image_path: str) -> List[Dict]:
        """从图片添加交易并入库。"""
        validated_txs = self.extract_from_image(image_path)
        if validated_txs:
            self.save_transactions(validated_txs)
        return validated_txs
        
    def save_transactions(
        self,
        tx_dicts: List[Dict],
        conn: sqlite3.Connection = None
    ) -> int:
        """保存已验证的交易字典列表到数据库"""
        if not tx_dicts:
            return 0
        count = self.repo.insert_many(tx_dicts, conn=conn)
        self.logger.info(f"✅ 成功入库 {count} 笔交易")
        return count
    
    def list_transactions(
        self,
        page: int = 1,
        page_size: int = 50,
        start_date: str = None,
        end_date: str = None,
        category: str = None
    ) -> Dict[str, Any]:
        """
        分页查询交易列表。
        """
        return self.repo.list_paginated(
            page=page,
            page_size=page_size,
            start_date=start_date,
            end_date=end_date,
            category=category
        )
    
    def get_stats(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        获取统计摘要。
        """
        return self.repo.get_stats(start_date=start_date, end_date=end_date)
    
    def query(self, question: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        自然语言查询。
        
        流程：
        1. 获取统计数据
        2. AI 生成回答
        3. 返回 {answer, stats}
        """
        stats = self.get_stats(start_date, end_date)
        answerer = self._get_answerer()
        answer = answerer.answer(question, stats)
        return {"answer": answer, "stats": stats}
    
    # ============ 内部方法 ============
    
    def _validate_tx(self, tx):
        """
        验证单条交易（业务规则）。
        
        注意：TransactionSchema 已做基础验证，这里做额外检查。
        """
        # 类别有效性（允许不在预定义列表，这里只警告）
        # 预定义列表见 config.EXPENSE_CATEGORIES
        allowed_cats = config.EXPENSE_CATEGORIES if hasattr(config, 'EXPENSE_CATEGORIES') else []
        if allowed_cats and tx.category not in allowed_cats:
            self.logger.warning(f"类别 '{tx.category}' 不在预定义列表，但允许保存")
        
        # 金额合理性
        if not validate_amount(tx.amount):
            raise ValueError(f"金额异常: {tx.amount}（超出合理范围）")
