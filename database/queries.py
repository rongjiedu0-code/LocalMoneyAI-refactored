"""
SQL查询常量：避免字符串散落各处，便于维护与优化。
"""
from typing import List, Dict, Any

# 按条件查询交易
SELECT_TRANSACTIONS = """
SELECT id, date, merchant, amount, category, description, items, created_at
FROM transactions
WHERE 1=1
{dynamic_where}
ORDER BY date DESC, created_at DESC
LIMIT ? OFFSET ?
"""

# 按类别汇总（可选日期范围）
SUMMARY_BY_CATEGORY = """
SELECT category, SUM(amount) as total
FROM transactions
WHERE 1=1
{dynamic_where}
GROUP BY category
"""

# 月度趋势
MONTHLY_TREND = """
SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
FROM transactions
WHERE 1=1
{dynamic_where}
GROUP BY month
ORDER BY month
"""

# 统计摘要（一个查询搞定）
SUMMARY_STATS = """
SELECT
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
    SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as total_expense,
    COUNT(*) as count
FROM transactions
WHERE 1=1
{dynamic_where}
"""
