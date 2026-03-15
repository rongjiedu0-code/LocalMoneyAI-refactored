"""
智能查询页面：自然语言问答。
"""
import streamlit as st
from datetime import datetime
from utils.i18n import get_text

class QueryPage:
    def __init__(self, tx_service):
        self.tx_service = tx_service
    
    def render(self):
        st.header(get_text("query_header"))
        st.caption(get_text("query_caption"))
        
        # 示例问题
        examples = [
            get_text("ex_1"),
            get_text("ex_2"),
            get_text("ex_3"),
            get_text("ex_4"),
        ]
        
        # 快速示例按钮
        cols = st.columns(len(examples))
        selected_example = None
        for idx, ex in enumerate(examples):
            with cols[idx]:
                if st.button(ex, key=f"ex_{idx}"):
                    selected_example = ex
        
        # 输入框
        question = st.text_input(
            get_text("query_label"),
            value=selected_example or "",
            placeholder=get_text("query_placeholder"),
            key="query_input"
        )
        
        # 时间范围选择（可选）
        with st.expander(get_text("optional_range")):
            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input(get_text("start_date"), value=None, key="q_start")
            with col2:
                end = st.date_input(get_text("end_date"), value=None, key="q_end")
        
        if st.button(get_text("query_btn"), type="primary", disabled=not question.strip()):
            with st.spinner(get_text("loading")):
                try:
                    start_str = start.strftime("%Y-%m-%d") if start else None
                    end_str = end.strftime("%Y-%m-%d") if end else None
                    
                    result = self.tx_service.query(
                        question=question,
                        start_date=start_str,
                        end_date=end_str
                    )
                    
                    st.success(get_text("query_result"))
                    st.write(result["answer"])
                    
                    with st.expander(get_text("query_stats")):
                        st.json(result["stats"])
                        
                except Exception as e:
                    st.error(f"{get_text('query_fail')}: {e}")
