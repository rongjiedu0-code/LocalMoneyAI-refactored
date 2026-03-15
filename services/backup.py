"""
备份服务：自动将 SQLite 数据库文件备份到指定目录（加时间戳）。
"""
import shutil
import os
from pathlib import Path
from datetime import datetime
from logging_config import logger


class BackupService:
    """
    数据库自动备份服务。
    
    职责：
    - 将当前 SQLite .db 文件复制到 backups/ 目录（或配置的路径）
    - 以时间戳命名，保留最近 N 份
    """
    
    def __init__(self, db_path: str, backup_dir: str = None, keep_last: int = 10):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir) if backup_dir else self.db_path.parent / "backups"
        self.keep_last = keep_last
    
    def backup(self) -> str | None:
        """
        执行一次备份。
        返回备份文件路径，如果 db 不存在则返回 None。
        """
        if not self.db_path.exists():
            logger.warning(f"备份跳过：数据库文件不存在 {self.db_path}")
            return None
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = self.db_path.stem
        suffix = self.db_path.suffix
        dest = self.backup_dir / f"{stem}_{timestamp}{suffix}"
        
        shutil.copy2(self.db_path, dest)
        logger.info(f"✅ 数据库备份成功：{dest}")
        
        self._cleanup_old_backups()
        return str(dest)
    
    def _cleanup_old_backups(self):
        """删除超出 keep_last 份的旧备份"""
        backups = sorted(self.backup_dir.glob(f"{self.db_path.stem}_*.db"))
        if len(backups) > self.keep_last:
            to_delete = backups[:len(backups) - self.keep_last]
            for f in to_delete:
                f.unlink()
                logger.debug(f"清理旧备份：{f}")
    
    def get_latest_backup(self) -> str | None:
        """获取最新的备份文件路径"""
        if not self.backup_dir.exists():
            return None
        backups = sorted(self.backup_dir.glob(f"{self.db_path.stem}_*.db"))
        return str(backups[-1]) if backups else None
    
    def list_backups(self) -> list:
        """列出所有备份文件（最新在前）"""
        if not self.backup_dir.exists():
            return []
        backups = sorted(self.backup_dir.glob(f"{self.db_path.stem}_*.db"), reverse=True)
        return [str(f) for f in backups]
