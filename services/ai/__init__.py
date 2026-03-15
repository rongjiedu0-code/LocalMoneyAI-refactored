"""
AI 服务包初始化：导出核心组件。
"""
from .client import OllamaClient
from .extractor import create_extractor, AIExtractor
from .schemas import TransactionSchema
from .prompts import prompt_manager
from .implementations import OllamaTextExtractor, OllamaImageExtractor

__all__ = [
    "OllamaClient",
    "create_extractor",
    "AIExtractor",
    "TransactionSchema",
    "prompt_manager",
    "OllamaTextExtractor",
    "OllamaImageExtractor"
]
