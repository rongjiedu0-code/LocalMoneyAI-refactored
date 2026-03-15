"""
配置加载器：支持多环境配置，类型安全。
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class AppConfig:
    """应用配置（类型安全）"""

    # Ollama 配置
    OLLAMA_HOST: str = "http://localhost:11434"
    TEXT_MODEL: str = "qwen2.5:7b"
    VISION_MODEL: str = "minicpm-v:latest"

    # 数据库
    DB_PATH: str = "money.db"

    # 日志
    LOG_LEVEL: str = "INFO"

    # 功能开关
    ENABLE_FALLBACK: bool = True

    # 网络配置
    REQUEST_TIMEOUT: int = 60
    MAX_RETRIES: int = 2

    # 国际化
    DEFAULT_LANGUAGE: str = "zh"

    # 支出类别
    EXPENSE_CATEGORIES: List[str] = field(default_factory=lambda: [
        "餐饮", "交通", "购物", "日用", "住房",
        "娱乐", "医疗", "教育", "通讯", "其他"
    ])

    # 当前环境
    ENV: str = "dev"

    def update(self, data: dict) -> None:
        """从字典更新配置"""
        for key, value in (data or {}).items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }


class ConfigManager:
    """配置管理器：支持多环境、热重载"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self._config = AppConfig()
        self._load()

    def _load(self) -> None:
        """加载当前环境的配置"""
        env = os.getenv("APP_ENV", "dev")
        data = self._read_config(env)
        data["ENV"] = env
        self._config.update(data)

    def _read_config(self, env: str) -> dict:
        """读取配置文件"""
        if not self.config_path.exists():
            return {}

        try:
            with self.config_path.open("r", encoding="utf-8") as fp:
                raw = json.load(fp)
                if isinstance(raw, dict):
                    return raw.get(env, {})
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ 配置文件读取失败: {e}")
        return {}

    def reload(self) -> AppConfig:
        """重新加载配置"""
        self._load()
        return self._config

    @property
    def config(self) -> AppConfig:
        """获取当前配置"""
        return self._config


# 全局配置实例
config_manager = ConfigManager()
config = config_manager.config
