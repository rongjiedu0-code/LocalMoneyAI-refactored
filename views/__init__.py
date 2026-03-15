"""
页面包初始化：导出所有页面类。
"""
from .base import BasePage
from .quick_entry import QuickEntryPage
from .importer import ImporterPage
from .query import QueryPage
from .report import ReportPage
from .list import ListPage
from .debug import DebugPage

__all__ = [
    "BasePage",
    "QuickEntryPage",
    "ImporterPage",
    "QueryPage",
    "ReportPage",
    "ListPage",
    "DebugPage"
]
