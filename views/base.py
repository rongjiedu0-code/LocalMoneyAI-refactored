"""
页面抽象基类：所有页面必须继承此类。
"""
from abc import ABC, abstractmethod
from typing import Any
import streamlit as st
from services.transaction.service import TransactionService
from services.ai.extractor import create_extractor
from services.ai.answerer import AIAnswerer
from services.ai.client import OllamaClient
from services.ai.prompts import prompt_manager
from config_loader import config

class BasePage(ABC):
    """所有页面的基类，提供公共功能和依赖注入。"""

    def __init__(self):
        # 从session state获取或创建服务
        self.tx_service = st.session_state.get("tx_service")

        if not self.tx_service:
            self._init_services()

    def _init_services(self):
        """初始化服务并缓存到session state。"""
        client = OllamaClient()
        ai_extractor = create_extractor(
            client=client,
            config=config,
            prompt_manager=prompt_manager,
            fallback_enabled=config.ENABLE_FALLBACK
        )
        ai_answerer = AIAnswerer(client=client, model=config.TEXT_MODEL)

        tx = TransactionService(ai_extractor=ai_extractor, answerer=ai_answerer)
        st.session_state.tx_service = tx
        self.tx_service = tx

    @abstractmethod
    def render(self):
        """渲染页面内容，子类必须实现。"""
        pass

    def show_error(self, message: str):
        """显示错误信息。"""
        st.error(f"❌ {message}")

    def show_success(self, message: str):
        """显示成功信息。"""
        st.success(f"✅ {message}")

    def show_info(self, message: str):
        """显示提示信息。"""
        st.info(f"ℹ️ {message}")
