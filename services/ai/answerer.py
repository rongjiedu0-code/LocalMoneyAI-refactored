"""
AI 问答器：基于统计数据生成自然语言回答。
"""
from typing import Dict, Any
from services.ai.client import OllamaClient
from services.ai.prompts import prompt_manager
from logging_config import logger
import json


class AIAnswerer:
    """
    使用 Ollama 模型回答关于财务数据的问题。

    策略：
    1. 使用 chat 接口（更符合对话场景）
    2. Prompt 模板化（prompt_manager.get("query_answer")）
    3. 降级：返回简单模板回答（Phase 1 逻辑）
    """

    def __init__(self, client: OllamaClient, model: str):
        self.client = client
        self.model = model
        self.logger = logger

    def answer(self, question: str, stats: Dict[str, Any]) -> str:
        """
        生成回答。

        参数:
            question: 用户问题
            stats: 统计数据字典（包含 total_income, total_expense, net, by_category, monthly_trend 等）

        返回:
            回答文本
        """
        self.logger.info(f"🤔 生成回答: {question[:50]}...")

        # 构建 prompt
        prompt = prompt_manager.get(
            "query_answer",
            stats_json=json.dumps(stats, ensure_ascii=False, indent=2),
            question=question
        )

        try:
            # 使用 chat 接口（OpenAI 格式）
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是专业财务分析师，回答简洁、客观。"},
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": 0.3}
            )

            answer = response.get("message", {}).get("content", "").strip()
            if not answer:
                raise ValueError("AI返回空回答")

            self.logger.info(f"✅ AI 回答生成成功（长度: {len(answer)}）")
            return answer

        except Exception as e:
            self.logger.error(f"AI 回答失败: {e}")
            return self._fallback_answer(question, stats)

    def _fallback_answer(self, question: str, stats: dict) -> str:
        """降级回答：简单模板"""
        try:
            total_income = stats.get('total_income', 0)
            total_expense = stats.get('total_expense', 0)
            net = stats.get('net', 0)

            if "总收入" in question or "收入" in question:
                return f"您的总收入为 ¥{total_income:.2f}。"
            elif "总支出" in question or "支出" in question:
                return f"您的总支出为 ¥{total_expense:.2f}。"
            elif "结余" in question:
                return f"您的结余为 ¥{net:.2f}（{'盈余' if net >= 0 else '亏损'}）。"
            else:
                return (f"根据统计：收入 ¥{total_income:.2f}，支出 ¥{total_expense:.2f}，"
                        f"结余 ¥{net:.2f}。")
        except Exception:
            return "抱歉，无法生成统计回答，请查看详细报表。"
