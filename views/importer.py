import streamlit as st
from config_loader import config
from logging_config import logger
from services.transaction.importer import CSVTransactionImporter
from utils.i18n import get_text


class ImporterPage:
    def __init__(self, tx_service):
        self.tx_service = tx_service
        self.importer = CSVTransactionImporter(tx_service)

    def render(self):
        st.header(get_text("importer_header"))
        st.caption(get_text("importer_caption"))

        uploaded_file = st.file_uploader(
            get_text("importer_upload"),
            type=["csv", "xlsx", "xls"],
            key="importer_csv_upload",
        )
        if not uploaded_file:
            return

        file_bytes = uploaded_file.getvalue()
        try:
            columns = self.importer.list_columns(
                file_bytes=file_bytes,
                file_name=uploaded_file.name,
            )
        except Exception as exc:
            st.error(get_text("importer_read_fail", error=str(exc)))
            return

        mapping = self._render_mapping(columns)
        if not mapping:
            return

        try:
            preview_df, preview_stats = self.importer.build_preview(
                file_bytes=file_bytes,
                file_name=uploaded_file.name,
                column_mapping=mapping,
                preview_rows=200,
            )
        except Exception as exc:
            logger.error(f"预览构建失败: {exc}", exc_info=True)
            st.error(get_text("importer_preview_fail", error=str(exc)))
            return

        st.info(
            get_text(
                "importer_preview_info",
                total=preview_stats["preview_total"],
                valid=preview_stats["preview_valid"],
                dropped=preview_stats["preview_dropped"],
            )
        )

        if preview_df.empty:
            st.warning(get_text("importer_preview_empty"))
            return

        st.data_editor(
            preview_df,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="importer_preview_editor",
            column_config={
                "date": st.column_config.TextColumn(f"{get_text('field_date')} (YYYY-MM-DD)", required=True),
                "merchant": st.column_config.TextColumn(get_text("field_merchant"), required=True),
                "amount": st.column_config.NumberColumn(get_text("field_amount"), required=True),
                "category": st.column_config.SelectboxColumn(
                    get_text("field_category"),
                    options=config.EXPENSE_CATEGORIES,
                    required=True,
                ),
                "description": st.column_config.TextColumn(get_text("field_description")),
            },
        )
        st.caption(get_text("importer_editor_hint"))

        chunk_size = st.number_input(
            get_text("importer_chunk_size"),
            min_value=100,
            max_value=2000,
            value=500,
            step=100,
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            start_import = st.button(
                get_text("importer_start_btn"),
                type="primary",
                use_container_width=True,
            )
        with col2:
            st.write("")

        if not start_import:
            return

        try:
            with st.spinner(get_text("importer_importing")):
                result = self.importer.import_csv(
                    file_bytes=file_bytes,
                    file_name=uploaded_file.name,
                    column_mapping=mapping,
                    chunk_size=int(chunk_size),
                )
            st.success(
                get_text(
                    "importer_done",
                    imported=result["imported_rows"],
                    total=result["total_rows"],
                    dropped=result["dropped_rows"],
                )
            )
        except Exception as exc:
            logger.error(f"导入失败: {exc}", exc_info=True)
            st.error(get_text("importer_import_fail", error=str(exc)))

    def _render_mapping(self, columns):
        st.subheader(get_text("importer_mapping_header"))
        options = [""] + columns
        mapping_fields = {
            "amount": get_text("field_amount"),
            "date": get_text("field_date"),
            "merchant": get_text("field_merchant"),
            "category": get_text("field_category"),
        }
        aliases = {
            "amount": {"amount", "金额", "money", "value", "price"},
            "date": {"date", "日期", "交易日期", "time"},
            "merchant": {"merchant", "商家", "商户", "对方", "payee"},
            "category": {"category", "类别", "分类", "标签", "type"},
        }
        selected = {}
        for key, label in mapping_fields.items():
            default_idx = self._guess_default_index(columns, aliases[key])
            selected_value = st.selectbox(
                f"{label} ←",
                options=options,
                index=default_idx,
                key=f"import_map_{key}",
            )
            selected[key] = selected_value.strip() if selected_value else ""

        selected_values = [value for value in selected.values() if value]
        if len(selected_values) != len(set(selected_values)):
            st.error(get_text("importer_mapping_duplicate"))
            return None
        if any(not selected[key] for key in mapping_fields):
            st.warning(get_text("importer_mapping_incomplete"))
            return None
        return selected

    def _guess_default_index(self, columns, alias_set):
        normalized_alias = {value.lower() for value in alias_set}
        for idx, column in enumerate(columns, start=1):
            if str(column).strip().lower() in normalized_alias:
                return idx
        return 0
