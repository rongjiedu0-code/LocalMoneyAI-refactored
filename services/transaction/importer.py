from __future__ import annotations

from io import BytesIO
from typing import Dict, Tuple
from pathlib import Path
import pandas as pd
from database.connection import get_connection
from logging_config import logger
from .validators import validate_amount


class CSVTransactionImporter:
    REQUIRED_FIELDS = ("amount", "date", "merchant", "category")

    def __init__(self, tx_service):
        self.tx_service = tx_service

    def list_columns(
        self,
        file_bytes: bytes,
        file_name: str,
        encoding: str = "utf-8-sig"
    ):
        file_type = self._detect_file_type(file_name)
        if file_type == "csv":
            probe_df = pd.read_csv(BytesIO(file_bytes), nrows=50, encoding=encoding)
        else:
            probe_df = pd.read_excel(BytesIO(file_bytes), nrows=50)
        return [str(col) for col in probe_df.columns]

    def build_preview(
        self,
        file_bytes: bytes,
        file_name: str,
        column_mapping: Dict[str, str],
        preview_rows: int = 200,
        encoding: str = "utf-8-sig",
    ) -> Tuple[pd.DataFrame, Dict[str, int]]:
        self._validate_mapping(column_mapping)
        file_type = self._detect_file_type(file_name)
        usecols = [column_mapping[key] for key in self.REQUIRED_FIELDS]
        if file_type == "csv":
            preview_df = pd.read_csv(
                BytesIO(file_bytes),
                usecols=usecols,
                nrows=preview_rows,
                encoding=encoding,
            )
        else:
            preview_df = pd.read_excel(
                BytesIO(file_bytes),
                usecols=usecols,
                nrows=preview_rows,
            )
        cleaned_df, dropped_rows = self._clean_dataframe(preview_df, column_mapping)
        stats = {
            "preview_total": len(preview_df),
            "preview_valid": len(cleaned_df),
            "preview_dropped": dropped_rows,
        }
        return cleaned_df, stats

    def import_csv(
        self,
        file_bytes: bytes,
        file_name: str,
        column_mapping: Dict[str, str],
        chunk_size: int = 500,
        encoding: str = "utf-8-sig",
    ) -> Dict[str, int]:
        self._validate_mapping(column_mapping)
        file_type = self._detect_file_type(file_name)
        imported_count = 0
        total_rows = 0
        dropped_rows = 0
        usecols = [column_mapping[key] for key in self.REQUIRED_FIELDS]
        try:
            with get_connection() as conn:
                if file_type == "csv":
                    chunk_iter = pd.read_csv(
                        BytesIO(file_bytes),
                        usecols=usecols,
                        chunksize=chunk_size,
                        encoding=encoding,
                    )
                else:
                    chunk_iter = self._iter_excel_chunks(
                        file_bytes=file_bytes,
                        usecols=usecols,
                        chunk_size=chunk_size,
                    )
                for chunk_df in chunk_iter:
                    total_rows += len(chunk_df)
                    cleaned_df, chunk_dropped = self._clean_dataframe(chunk_df, column_mapping)
                    dropped_rows += chunk_dropped
                    if cleaned_df.empty:
                        continue
                    tx_records = cleaned_df.to_dict("records")
                    imported_count += self.tx_service.save_transactions(tx_records, conn=conn)
        except Exception as exc:
            logger.error(f"CSV导入失败: {exc}", exc_info=True)
            raise
        return {
            "total_rows": total_rows,
            "imported_rows": imported_count,
            "dropped_rows": dropped_rows,
        }

    def _validate_mapping(self, column_mapping: Dict[str, str]):
        missing = [key for key in self.REQUIRED_FIELDS if not column_mapping.get(key)]
        if missing:
            raise ValueError(f"缺少必要映射字段: {', '.join(missing)}")

    def _detect_file_type(self, file_name: str) -> str:
        suffix = Path(file_name).suffix.lower()
        if suffix == ".csv":
            return "csv"
        if suffix in {".xlsx", ".xls"}:
            return "excel"
        raise ValueError("仅支持 CSV / XLSX / XLS 文件")

    def _iter_excel_chunks(self, file_bytes: bytes, usecols, chunk_size: int):
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        offset = 0
        while True:
            chunk_df = pd.read_excel(
                BytesIO(file_bytes),
                usecols=usecols,
                skiprows=range(1, offset + 1),
                nrows=chunk_size,
            )
            if chunk_df.empty:
                break
            yield chunk_df
            offset += len(chunk_df)

    def _clean_dataframe(self, df: pd.DataFrame, column_mapping: Dict[str, str]):
        working_df = df.rename(
            columns={
                column_mapping["amount"]: "amount",
                column_mapping["date"]: "date",
                column_mapping["merchant"]: "merchant",
                column_mapping["category"]: "category",
            }
        ).copy()

        working_df["amount"] = (
            working_df["amount"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("¥", "", regex=False)
            .str.replace("￥", "", regex=False)
            .str.strip()
        )
        working_df["amount"] = pd.to_numeric(working_df["amount"], errors="coerce")

        parsed_date = pd.to_datetime(working_df["date"], errors="coerce")
        working_df["date"] = parsed_date.dt.strftime("%Y-%m-%d")

        working_df["merchant"] = working_df["merchant"].astype(str).str.strip()
        working_df["category"] = working_df["category"].astype(str).str.strip()
        working_df["description"] = ""

        valid_mask = (
            working_df["amount"].notna()
            & working_df["date"].notna()
            & working_df["merchant"].ne("")
            & working_df["category"].ne("")
            & working_df["amount"].apply(lambda value: validate_amount(value) if pd.notna(value) else False)
        )
        cleaned_df = working_df.loc[valid_mask, ["date", "merchant", "amount", "category", "description"]]
        dropped_rows = len(working_df) - len(cleaned_df)
        return cleaned_df, dropped_rows
