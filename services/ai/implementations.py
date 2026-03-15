"""
具体提取器实现：基于 Ollama 的文本与图片提取器。
"""
from typing import List
from services.ai.schemas import TransactionSchema
from services.ai.prompts import prompt_manager
from logging_config import logger
import json
import re
from datetime import datetime


class OllamaTextExtractor:
    """
    使用 Ollama 文本模型提取交易记录。
    """
    
    def __init__(self, client, model: str, prompt_manager, categories: list = None):
        self.client = client
        self.model = model
        self.prompt_manager = prompt_manager
        self.categories = ",".join(categories) if categories else "餐饮,交通,购物,娱乐,医疗,收入,其他"
    
    def extract(self, text: str) -> List[TransactionSchema]:
        """
        从用户自然语言文本中提取交易。
        
        策略：
        1. 尝试直接解析（JSON/CSV/行格式） - 快速路径（Phase 1 逻辑）
        2. 失败则调用 Ollama AI 提取
        3. 解析并验证返回的 JSON
        """
        logger.info(f"📝 开始文本提取（长度: {len(text)}）")
        
        # === 快速路径：本地解析（保持 Phase 1 逻辑） ===
        # 可以复用 AIService 原来的 parse_text_input 中的快速解析部分
        # 这里为了简洁，先尝试 JSON/CSV/正则快速解析
        # 如果成功，直接返回，不调用 AI（节省 tokens）
        quick_result = self._quick_parse(text)
        if quick_result:
            logger.info(f"✅ 快速解析成功，提取 {len(quick_result)} 条")
            return quick_result
        
        # === AI 路径：调用 Ollama ===
        logger.info("快速解析失败，调用 AI 提取")
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = self.prompt_manager.get(
            "parse_text", 
            categories=self.categories,
            today=today
        )
        
        messages = [
            {"role": "system", "content": "你是专业财务助手，只输出JSON数组。"},
            {"role": "user", "content": f"{prompt}\n\n用户输入：{text}"}
        ]
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=messages[-1]["content"]  # 简化：直接传最后一条作为 prompt
            )
            ai_text = response.get("response", "").strip()
            logger.debug(f"AI 原始响应（前200字符）: {ai_text[:200]}")
            
            # 提取 JSON
            json_str = self._extract_json_from_text(ai_text)
            if not json_str:
                raise ValueError("AI 未返回有效 JSON")
            
            # 解析为字典列表
            data = json.loads(json_str)
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                raise ValueError(f"预期数组或对象，得到: {type(data)}")
            
            # 转换为 TransactionSchema
            transactions = []
            for item in data:
                try:
                    tx = TransactionSchema(
                        date=str(item['date']),
                        merchant=str(item['merchant']),
                        amount=float(item['amount']),
                        category=str(item.get('category', '其他')),
                        description=str(item.get('description', '')),
                        items=item.get('items', [])
                    )
                    if tx.is_valid():
                        transactions.append(tx)
                    else:
                        logger.warning(f"跳过无效交易: {item}")
                except Exception as e:
                    logger.warning(f"记录验证失败: {e}, 跳过: {item}")
            
            # 不再抛出错误，而是返回空列表，由 UI 处理
            if not transactions:
                logger.info("AI未提取到任何有效交易或内容不含记账关键信息")
            else:
                logger.info(f"✅ AI 提取成功，共 {len(transactions)} 条")
            
            return transactions
            
        except Exception as e:
            logger.error(f"AI 文本提取失败: {e}")
            raise
    
    def _quick_parse(self, text: str) -> List[TransactionSchema] | None:
        """
        快速解析：JSON数组、CSV、行格式（简洁版）。
        返回 None 表示无法快速解析，需要 AI。
        """
        import re
        import csv
        from io import StringIO
        from datetime import datetime
        
        text = text.strip()
        
        # 1. 尝试 JSON 数组
        try:
            json_match = re.search(r'\[[\s\S]*\]', text)
            if json_match:
                data = json.loads(json_match.group(0))
                if isinstance(data, list) and len(data) > 0:
                    return self._normalize_transactions(data)
        except:
            pass
        
        # 2. 尝试 CSV
        try:
            if ',' in text:
                reader = csv.DictReader(StringIO(text))
                rows = list(reader)
                if rows and any(k in rows[0] for k in ['date', '日期', '时间']):
                    return self._normalize_transactions(rows)
        except:
            pass
        
        # 3. 尝试行解析（简单空格分隔）
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        records = []
        for line in lines[:20]:
            if any(kw in line.lower() for kw in ['日期', '商户', '金额']):
                continue  # 跳过表头
            parts = line.split()
            if len(parts) >= 3:
                # 找金额（最后一个数字）
                for i in range(len(parts)-1, -1, -1):
                    try:
                        amount = float(parts[i].replace(',', ''))
                        date = parts[0]
                        merchant = ' '.join(parts[1:i])
                        records.append({
                            'date': date,
                            'merchant': merchant,
                            'amount': amount,
                            'category': '其他'
                        })
                        break
                    except:
                        continue
        
        if records:
            return self._normalize_transactions(records)
        
        return None
    
    def _normalize_transactions(self, data: List[dict]) -> List[TransactionSchema]:
        """将字典列表归一化为 TransactionSchema 列表"""
        normalized = []
        for item in data:
            try:
                amount = float(item.get('amount', 0))
                if abs(amount) < 0.01:
                    continue
                
                # 日期标准化
                date_str = str(item['date'])
                date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                if re.match(r'\d{1,2}-\d{1,2}', date_str):
                    year = datetime.now().year
                    date_str = f"{year}-{date_str}"
                
                # 类别归一化
                category = item.get('category', '其他')
                
                # 金额符号：支出转负
                if amount > 0 and category != '收入':
                    amount = -amount
                
                normalized.append(TransactionSchema(
                    date=date_str,
                    merchant=str(item.get('merchant', '未知')),
                    amount=round(amount, 2),
                    category=str(category),
                    description=str(item.get('description', '')),
                    items=item.get('items', [])
                ))
            except Exception as e:
                logger.warning(f"记录归一化失败: {e}, 跳过")
                continue
        
        return normalized
    
    def _extract_json_from_text(self, text: str) -> str | None:
        """
        从 AI 响应文本中提取 JSON 字符串。
        支持 ```json``` 代码块、`[...]` 数组、`{...}` 对象。
        """
        import re
        
        # 1. 代码块
        match = re.search(r'```(?:json)?\n([\s\S]*?)\n```', text)
        if match:
            return match.group(1).strip()
        
        # 2. 数组
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            return match.group(0)
        
        # 3. 查找所有独立 {} 对象（支持多行）
        # 使用非贪婪匹配，跨行
        objects = re.findall(r'\{.*?\}', text, re.DOTALL)
        if objects:
            cleaned = []
            for obj in objects:
                # 移除每行开头的序号
                obj = re.sub(r'(?m)^\s*\d+\.\s*', '', obj)
                cleaned.append(obj)
            return f"[{','.join(cleaned)}]"
        
        return None


class OllamaImageExtractor:
    """
    使用 Ollama 视觉模型从图片提取交易记录。
    """
    
    def __init__(self, client, model: str, prompt_manager, categories: list = None):
        self.client = client
        self.model = model
        self.prompt_manager = prompt_manager
        self.categories = ",".join(categories) if categories else "餐饮,交通,购物,娱乐,医疗,收入,其他"
    
    def extract(self, image_path: str) -> List[TransactionSchema]:
        """
        从图片提取交易。
        
        流程：
        1. 图片转 base64
        2. 构建 prompt（要求 JSON 输出）
        3. 调用 Ollama generate 接口（支持图片）
        4. 解析 JSON 响应
        5. 处理序号列表格式
        """
        import base64
        from pathlib import Path
        
        logger.info(f"🔍 开始图片提取: {image_path}")
        
        if not Path(image_path).exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")
        
        # 读取并编码图片
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
        # === AI 路径 ===
        logger.info(f"发送图片到 AI 模型: {self.model}")
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = self.prompt_manager.get(
            "ocr_image", 
            categories=self.categories,
            today=today
        )
        
        try:
            # 使用 generate 接口（支持 images 参数）
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                images=[image_base64],
                options={"temperature": 0.1}
            )
            ai_text = response.get("response", "").strip()
            logger.debug(f"AI 原始响应（前300字符）: {ai_text[:300]}")
            
            # 提取 JSON
            json_str = self._extract_json_from_text(ai_text)
            if not json_str:
                logger.error(f"未提取到 JSON，原始响应: {ai_text[:500]}")
                raise ValueError("AI未返回有效JSON格式")
            
            # 解析
            data = json.loads(json_str)
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                raise ValueError(f"预期数组或对象，得到: {type(data)}")
            
            # 转换为 TransactionSchema
            transactions = []
            for item in data:
                try:
                    tx = TransactionSchema(
                        date=str(item['date']),
                        merchant=str(item['merchant']),
                        amount=float(item['amount']),
                        category=str(item.get('category', '其他')),
                        description=str(item.get('description', '')),
                        items=item.get('items', [])
                    )
                    if tx.is_valid():
                        transactions.append(tx)
                    else:
                        logger.warning(f"跳过无效记录: {item}")
                except Exception as e:
                    logger.warning(f"交易验证失败，跳过: {e}, 数据: {item}")
            
            if not transactions:
                logger.info("图片中未提取到有效交易")
            else:
                logger.info(f"✅ 图片提取成功，共 {len(transactions)} 条")
                
            return transactions
            
        except Exception as e:
            logger.error(f"图片提取失败: {e}")
            raise
    
    def _extract_json_from_text(self, text: str) -> str | None:
        """
        从 AI 响应中提取 JSON，支持多种格式：
        - ```json``` 代码块
        - 数组 `[{...}, {...}]`
        - 序号列表 `1. {...}\n2. {...}`
        """
        import re
        
        # 1. 代码块优先
        match = re.search(r'```(?:json)?\n([\s\S]*?)\n```', text)
        if match:
            return match.group(1).strip()
        
        # 2. 尝试直接数组
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            json_str = match.group(0)
            # 检查是否包含序号前缀（如 "1. {"）
            if re.search(r'\d+\.\s*\{', json_str):
                # 拆分为多个对象，移除序号
                objects = re.findall(r'\d+\.\s*(\{.*?\})', json_str, re.DOTALL)
                if objects:
                    return f"[{','.join(objects)}]"
            return json_str
        
        # 3. 查找所有独立 {} 对象（支持多行）
        # 使用非贪婪匹配，跨行
        objects = re.findall(r'\{.*?\}', text, re.DOTALL)
        if objects:
            cleaned = []
            for obj in objects:
                # 移除每行开头的序号
                obj = re.sub(r'(?m)^\s*\d+\.\s*', '', obj)
                cleaned.append(obj)
            return f"[{','.join(cleaned)}]"
        
        return None
