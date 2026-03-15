"""
AI 提取器接口与实现：文本、图片、降级策略。
"""
from abc import ABC, abstractmethod
from typing import List, Protocol
from services.ai.schemas import TransactionSchema


class ITextExtractor(Protocol):
    """文本提取器接口（结构子类型）"""
    def extract(self, text: str) -> List[TransactionSchema]: ...


class IImageExtractor(Protocol):
    """图片提取器接口（结构子类型）"""
    def extract(self, image_path: str) -> List[TransactionSchema]: ...


class AIExtractor:
    """
    组合提取器：按优先级尝试多个提取器。

    策略：
    1. 文本：主提取器 → 降级提取器（如果启用）
    2. 图片：主提取器 → 失败即抛出（图片暂无降级）
    """

    def __init__(
        self,
        text_extractor: ITextExtractor,
        image_extractor: IImageExtractor,
        fallback_extractor: ITextExtractor | None = None
    ):
        self.text_extractor = text_extractor
        self.image_extractor = image_extractor
        self.fallback_extractor = fallback_extractor

    def from_text(self, text: str) -> List[TransactionSchema]:
        """
        从文本提取交易。

        降级策略：
        - 主提取器失败 → 如果配置了 fallback，使用 fallback_extractor
        - 全部失败 → 抛出异常
        """
        try:
            return self.text_extractor.extract(text)
        except Exception as e:
            # 主提取器失败
            if self.fallback_extractor:
                try:
                    return self.fallback_extractor.extract(text)
                except Exception as fb_e:
                    raise RuntimeError(
                        f"文本提取失败（主: {e}，降级: {fb_e}）"
                    ) from fb_e
            raise

    def from_image(self, image_path: str) -> List[TransactionSchema]:
        """
        从图片提取交易。

        注意：图片暂无降级策略（因为降级为文本提取无意义）。
        """
        return self.image_extractor.extract(image_path)


# 便捷工厂函数
def create_extractor(
    client,
    config,
    prompt_manager,
    fallback_enabled: bool = True
) -> AIExtractor:
    """
    创建 AIExtractor 实例（依赖注入）。

    参数:
        client: OllamaClient 实例
        config: AppConfig 配置
        prompt_manager: PromptManager 实例
        fallback_enabled: 是否启用文本降级
    """
    from .implementations import OllamaTextExtractor, OllamaImageExtractor
    from utils.fallback_parser import FallbackParser

    # 主提取器
    text_extractor = OllamaTextExtractor(
        client=client,
        model=config.TEXT_MODEL,
        prompt_manager=prompt_manager,
        categories=config.EXPENSE_CATEGORIES
    )

    image_extractor = OllamaImageExtractor(
        client=client,
        model=config.VISION_MODEL,
        prompt_manager=prompt_manager,
        categories=config.EXPENSE_CATEGORIES
    )

    # 降级提取器（文本）
    fallback_extractor = None
    if fallback_enabled:
        fallback_extractor = FallbackTextExtractor(FallbackParser)

    return AIExtractor(
        text_extractor=text_extractor,
        image_extractor=image_extractor,
        fallback_extractor=fallback_extractor
    )


class FallbackTextExtractor:
    """
    降级文本提取器：包装 FallbackParser。
    实现 ITextExtractor 接口。
    """

    def __init__(self, parser_class):
        self.parser_class = parser_class

    def extract(self, text: str) -> List[TransactionSchema]:
        # FallbackParser.parse_text 返回 TransactionSchema 列表
        return self.parser_class.parse_text(text)
