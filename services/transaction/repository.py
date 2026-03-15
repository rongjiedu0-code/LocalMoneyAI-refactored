"""
交易数据访问层（DAO）：封装所有 SQL 操作。
"""
from typing import List, Dict, Any, Optional
import sqlite3
from database.queries import (
    SELECT_TRANSACTIONS,
    SUMMARY_BY_CATEGORY,
    MONTHLY_TREND,
    SUMMARY_STATS
)
from database.connection import get_connection
from logging_config import logger
import json


class TransactionRepository:
    """
    交易表的数据库操作封装。
    
    职责：
    - 增删改查（CRUD）
    - 统计查询（按类别、月度趋势）
    - 不包含业务逻辑（如验证）
    """
    
    def __init__(self):
        pass  # 无状态，使用 get_connection() 获取连接
    
    def insert(self, tx_data: Dict[str, Any]) -> int:
        """
        插入单条交易记录。
        
        参数:
            tx_data: 包含 date, merchant, amount, category, description, items 的字典
            
        返回:
            插入记录的 ID
        """
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO transactions (date, merchant, amount, category, description, items)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                self._to_insert_tuple(tx_data)
            )
            return cursor.lastrowid
    
    def insert_many(
        self,
        tx_list: List[Dict[str, Any]],
        conn: sqlite3.Connection = None
    ) -> int:
        """
        批量插入交易记录。
        
        返回:
            影响的行数
        """
        if not tx_list:
            return 0
        if conn is None:
            with get_connection() as managed_conn:
                return self.insert_many(tx_list, conn=managed_conn)
        rows = [self._to_insert_tuple(tx) for tx in tx_list]
        conn.executemany(
            """
            INSERT INTO transactions (date, merchant, amount, category, description, items)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows
        )
        return len(rows)
    
    def find_by_id(self, tx_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 查询交易"""
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM transactions WHERE id = ?",
                (tx_id,)
            )
            row = cursor.fetchone()
            if row:
                data = dict(row)
                if 'items' in data and isinstance(data['items'], str):
                    try:
                        data['items'] = json.loads(data['items'])
                    except:
                        data['items'] = []
                return data
            return None
    
    def list_all(self) -> List[Dict[str, Any]]:
        """查询所有交易（无分页，慎用）"""
        with get_connection() as conn:
            cursor = conn.execute("SELECT * FROM transactions ORDER BY date DESC, created_at DESC")
            rows = cursor.fetchall()
            data = []
            for row in rows:
                item = dict(row)
                if 'items' in item and isinstance(item['items'], str):
                    try:
                        item['items'] = json.loads(item['items'])
                    except:
                        item['items'] = []
                data.append(item)
            return data
    
    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        start_date: str = None,
        end_date: str = None,
        category: str = None
    ) -> Dict[str, Any]:
        """
        分页查询交易列表。
        
        参数:
            page: 页码（从1开始）
            page_size: 每页大小
            start_date: 开始日期（YYYY-MM-DD，可选）
            end_date: 结束日期（YYYY-MM-DD，可选）
            category: 类别筛选（可选）
            
        返回:
            {
                "data": [...],
                "pagination": {
                    "page": 1,
                    "page_size": 50,
                    "total": 100,
                    "pages": 2
                }
            }
        """
        offset = (page - 1) * page_size
        
        # 构建动态 WHERE 子句
        where_clauses = []
        params = []
        
        if start_date:
            where_clauses.append("date >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("date <= ?")
            params.append(end_date)
        if category and category != "全部":
            where_clauses.append("category = ?")
            params.append(category)
        
        where_sql = " AND ".join(where_clauses)
        if where_sql:
            where_sql = "WHERE " + where_sql
        
        # 查询数据
        with get_connection() as conn:
            query = SELECT_TRANSACTIONS.format(dynamic_where=where_sql)
            cursor = conn.execute(query, params + [page_size, offset])
            rows = cursor.fetchall()
            
            # 查询总数
            count_query = f"SELECT COUNT(*) FROM transactions {where_sql}"
            total = conn.execute(count_query, params).fetchone()[0]
        
        # 格式化结果
        data = []
        for row in rows:
            item = dict(row)
            if 'items' in item and isinstance(item['items'], str):
                try:
                    item['items'] = json.loads(item['items'])
                except:
                    item['items'] = []
            data.append(item)
        
        return {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        }
    
    def get_stats(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        获取统计摘要（优化版：单次查询）。
        
        返回:
            {
                "total_income": 5000.0,
                "total_expense": 3000.0,
                "net": 2000.0,
                "by_category": [{"category": "餐饮", "income": 0, "expense": 1500.0, "net": -1500.0}, ...],
                "monthly_trend": [{"month": "2024-01", "income": 5000.0, "expense": 3000.0, "net": 2000.0}, ...],
                "period": {"start": "2024-01-01", "end": "2024-01-31"}
            }
        """
        where_clauses = []
        params = []
        
        if start_date:
            where_clauses.append("date >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("date < ?")  # 改为 <，避免边界问题
            params.append(end_date)
        
        where_sql = " AND ".join(where_clauses)
        if where_sql:
            where_sql = "WHERE " + where_sql
        
        with get_connection() as conn:
            # 优化：单次查询获取所有数据
            query = f"""
            WITH aggregated AS (
                SELECT 
                    strftime('%Y-%m', date) as month,
                    category,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                    SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as expense,
                    SUM(amount) as net
                FROM transactions
                {where_sql}
                GROUP BY month, category
            )
            SELECT 
                month,
                category,
                income,
                expense,
                net,
                SUM(income) OVER () as total_income,
                SUM(expense) OVER () as total_expense
            FROM aggregated
            ORDER BY month
            """
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        # 空数据检查
        if not rows:
            return self._empty_stats(start_date, end_date)
        
        # 解析数据
        monthly_trend = []
        by_category = []
        total_income = 0
        total_expense = 0
        
        for row in rows:
            month, category, income, expense, net, t_income, t_expense = row
            total_income = t_income or 0
            total_expense = t_expense or 0
            
            # 月度趋势（去重合并）
            if not monthly_trend or monthly_trend[-1]["month"] != month:
                monthly_trend.append({
                    "month": month,
                    "income": income or 0,
                    "expense": abs(expense or 0),  # 支出转为正数
                    "net": net or 0
                })
            else:
                # 合并同月数据
                monthly_trend[-1]["income"] += income or 0
                monthly_trend[-1]["expense"] += abs(expense or 0)
                monthly_trend[-1]["net"] += net or 0
            
            # 类别汇总
            by_category.append({
                "category": category,
                "income": income or 0,
                "expense": abs(expense or 0),
                "net": net or 0
            })
        
        return {
            "total_income": total_income,
            "total_expense": abs(total_expense),  # 支出转为正数
            "net": total_income + total_expense,  # 直接相加（支出已是负数）
            "by_category": by_category,
            "monthly_trend": monthly_trend,
            "period": {"start": start_date, "end": end_date}
        }
    
    def _empty_stats(self, start_date, end_date):
        """返回空数据的默认结构"""
        return {
            "total_income": 0,
            "total_expense": 0,
            "net": 0,
            "by_category": [],
            "monthly_trend": [],
            "period": {"start": start_date, "end": end_date}
        }

    def _to_insert_tuple(self, tx_data: Dict[str, Any]):
        items = tx_data.get('items', [])
        if isinstance(items, list):
            items_json = json.dumps(items)
        else:
            items_json = str(items)
        return (
            tx_data['date'],
            tx_data['merchant'],
            tx_data['amount'],
            tx_data['category'],
            tx_data.get('description', ''),
            items_json
        )
