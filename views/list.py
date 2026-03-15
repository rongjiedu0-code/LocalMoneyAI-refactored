"""
交易明细页面：分页展示、筛选、导出。
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional
from utils.i18n import get_text

class ListPage:
    def __init__(self, tx_service):
        self.tx_service = tx_service
    
    def render(self):
        st.header(get_text("list_header"))
        st.caption(get_text("list_caption"))
        
        # 筛选栏
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            start_date = st.date_input(get_text("start_date"), value=None)
        with col2:
            end_date = st.date_input(get_text("end_date"), value=None)
        with col3:
            from config_loader import config
            expense_cats = config.EXPENSE_CATEGORIES if hasattr(config, 'EXPENSE_CATEGORIES') else []
            categories = [get_text("all")] + expense_cats
            selected_cat = st.selectbox(get_text("field_category"), categories)
        with col4:
            page_size = st.selectbox(get_text("page_size"), [20, 50, 100], index=0)
        
        # 分页
        if "list_page" not in st.session_state:
            st.session_state.list_page = 1
        
        col_prev, col_next, col_page, col_total = st.columns(4)
        with col_prev:
            if st.button(get_text("prev_page"), disabled=st.session_state.list_page <= 1):
                st.session_state.list_page -= 1
                st.rerun()
        with col_next:
            if st.button(get_text("next_page")):
                st.session_state.list_page += 1
                st.rerun()
        with col_page:
            st.write(get_text("page_info", page=st.session_state.list_page))
        with col_total:
            st.write(f"{get_text('page_size')}: {page_size}")
        
        # 查询数据
        start_str = start_date.strftime("%Y-%m-%d") if start_date else None
        end_str = end_date.strftime("%Y-%m-%d") if end_date else None
        
        try:
            result = self.tx_service.list_transactions(
                page=st.session_state.list_page,
                page_size=page_size
            )
            
            data = result["data"]
            pagination = result["pagination"]
            
            # 应用筛选
            if selected_cat != get_text("all"):
                data = [d for d in data if d["category"] == selected_cat]
            
            if start_str:
                data = [d for d in data if d["date"] >= start_str]
            if end_str:
                data = [d for d in data if d["date"] <= end_str]
            
            if not data:
                st.info(get_text("no_data"))
                return
            
            # 格式化显示
            df = pd.DataFrame(data)
            df["amount"] = df["amount"].apply(lambda x: f"¥{x:,.2f}")
            df["date"] = pd.to_datetime(df["date"])
            df = df[["date", "merchant", "amount", "category", "description"]]
            df.columns = [
                get_text("field_date"), 
                get_text("field_merchant"), 
                get_text("field_amount"), 
                get_text("field_category"), 
                get_text("field_description")
            ]
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    get_text("field_date"): st.column_config.DateColumn(get_text("field_date"), format="YYYY-MM-DD"),
                    get_text("field_amount"): st.column_config.TextColumn(get_text("field_amount")),
                }
            )
            
            # 导出按钮
            csv = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label=get_text("export_csv"),
                data=csv,
                file_name=f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # 分页信息
            st.caption(get_text("total_records", total=pagination['total'], count=len(data)))
            
        except Exception as e:
            st.error(f"{get_text('error')}: {e}")
