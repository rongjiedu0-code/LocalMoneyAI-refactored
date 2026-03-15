"""
AI提示词管理：多版本、可插拔。
"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class PromptTemplate:
    name: str
    template: str
    version: str = "1.0"
    description: str = ""


class PromptManager:
    def __init__(self):
        self._prompts: Dict[str, PromptTemplate] = {}

    def register(self, prompt: PromptTemplate):
        self._prompts[prompt.name] = prompt

    def get(self, name: str, **kwargs) -> str:
        if name not in self._prompts:
            raise KeyError(f"未找到提示词: {name}")
        template = self._prompts[name].template
        return template.format(**kwargs) if kwargs else template


# 初始化默认提示词
prompt_manager = PromptManager()

prompt_manager.register(PromptTemplate(
    name="ocr_image",
    template="""\
你是专业财务助手，擅长从图片/小票/发票中提取交易信息。当前日期：{today}。

【提取规则】
1. 日期：优先使用小票日期。如果只有"月-日"，补全为"{today}"的年份。如果小票无日期，使用"{today}"。
2. 金额：小票金额通常是支出（负数）。如果有多个金额，提取总金额或逐项提取。
3. 商户：从小票顶部/底部提取商家名称。
4. 类别：根据商户类型判断。可用分类：{categories}
   - 餐饮：餐厅、咖啡店、快餐、外卖
   - 交通：出租车、公交、地铁、加油、停车
   - 购物：超市、商场、便利店、网购
   - 娱乐：电影、KTV、游戏、体育
   - 医疗：医院、药店、诊所
   - 收入：工资、奖金、退款（正数）
   - 其他：无法归类的支出

【输出格式】仅输出 JSON 数组（即使只有 1 笔交易）：
[
  {{
    "date": "YYYY-MM-DD",
    "merchant": "商家名称",
    "amount": -数字（负数=支出，正数=收入，单位：元）,
    "category": "从上述分类选择",
    "description": "简要描述（如'午餐'、'超市购物'）",
    "items": ["商品1", "商品2"]  // 可选，如果小票有明细
  }}
]

【错误处理】
- 如果图片模糊/无法识别：返回 [{{"error": "image_unclear"}}]
- 如果图片无交易信息：返回 [{{"error": "no_transaction"}}]
- 如果识别到交易但信息不全：尽可能提取已知字段，缺失字段用空字符串

【示例】
小票内容："麦当劳 ￥35.00 2024-01-15 汉堡套餐"
输出：[{{"date": "2024-01-15", "merchant": "麦当劳", "amount": -35.00, "category": "餐饮", "description": "汉堡套餐"}}]
""",
    description="图片OCR提取交易（增强版）"
))

prompt_manager.register(PromptTemplate(
    name="parse_text",
    template="""\
你是一个财务记账助手。当前日期是：{today}。请从用户自然语言描述中提取所有交易，输出JSON数组。
每项包含：date(YYYY-MM-DD)、merchant(商家)、amount(数字，正收入负支出)、category(从给定列表选)、description、items。
示例：如果用户说"今天"，日期应解析为 {today}。
可用分类：{categories}

仅输出JSON数组，不要其他内容。
""",
    description="文本解析多笔交易"
))

prompt_manager.register(PromptTemplate(
    name="query_answer",
    template="""\
你是一个财务分析师。基于提供的统计JSON数据，用简洁自然语言回答用户问题。
回答需：1) 包含关键数字；2) 指出异常或趋势；3) 保持客观。
数据：{stats_json}
问题：{question}
回答：""",
    description="基于统计回答问题"
))
