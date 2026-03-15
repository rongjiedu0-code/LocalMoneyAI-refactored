"""
Ollama客户端封装：支持流式、超时、重试。
"""
import requests
from requests.exceptions import RequestException
from config_loader import config
from utils.retry import retry
from logging_config import logger
from typing import Dict, Any, List


class OllamaClient:
    """Ollama API客户端。"""

    def __init__(self, host: str = None, timeout: int = None):
        self.host = host or config.OLLAMA_HOST
        self.timeout = timeout or config.REQUEST_TIMEOUT
        logger.info(f"OllamaClient初始化: {self.host}")

    @retry(max_attempts=3, delay=2.0)
    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        images: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用 /api/chat 接口（OpenAI 兼容格式）。

        参数:
            model: 模型名称
            messages: 消息列表 [{role: "user"/"system", content: "..."}]
            images: 图片base64字符串列表（可选，与最后一条消息关联）
            **kwargs: stream、options 等

        返回:
            Ollama 响应字典
        """
        data = {
            "model": model,
            "messages": messages,
            "stream": False,
            **kwargs
        }

        # 如果有图片，添加到最后一个消息
        if images:
            if not messages:
                raise ValueError("提供images时必须有messages")
            messages[-1]["images"] = images

        response = requests.post(
            f"{self.host}/api/chat",
            json=data,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    @retry(max_attempts=3, delay=2.0)
    def generate(
        self,
        model: str,
        prompt: str,
        images: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用 /api/generate 接口（传统格式，兼容图片）。

        参数:
            model: 模型名称
            prompt: 提示词
            images: 图片base64字符串列表（可选）
            **kwargs: options 等

        返回:
            Ollama 响应字典
        """
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            **kwargs
        }
        if images:
            data["images"] = images

        response = requests.post(
            f"{self.host}/api/generate",
            json=data,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def _encode_image(self, path: str) -> str:
        """Base64编码图片。"""
        import base64
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def list_models(self) -> List[Dict]:
        """列出本地已下载模型。"""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []
