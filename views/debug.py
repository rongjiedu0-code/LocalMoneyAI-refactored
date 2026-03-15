"""
调试页面：系统状态监控、日志查看、手动测试。
"""
import streamlit as st
import subprocess
import requests
from datetime import datetime
from logging_config import logger
from config_loader import config
from services.ai.extractor import AIExtractor
from services.ai.answerer import AIAnswerer
from utils.i18n import get_text

class DebugPage:
    def __init__(self, ai_extractor: AIExtractor, ai_answerer: AIAnswerer, tx_service):
        self.ai_extractor = ai_extractor
        self.ai_answerer = ai_answerer
        self.tx = tx_service
    
    def render(self):
        st.header(get_text("debug_header"))
        st.caption(get_text("debug_caption"))
        
        tab1, tab2, tab3, tab4 = st.tabs([
            get_text("tab_status"), get_text("tab_ai"), get_text("tab_logs"), get_text("tab_db")
        ])
        
        with tab1:
            self._render_system_status()
        with tab2:
            self._render_ai_test()
        with tab3:
            self._render_logs()
        with tab4:
            self._render_database()
    
    def _render_system_status(self):
        st.subheader(get_text("sys_status"))
        
        # Ollama状态
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**{get_text('ollama_status')}**")
            try:
                resp = requests.get(config.OLLAMA_HOST, timeout=2)
                if resp.status_code == 200:
                    st.success(f"✅ {get_text('enabled')}")
                    st.write(f"{get_text('ollama_host')}: `{config.OLLAMA_HOST}`")
                else:
                    st.warning("⚠️ 响应异常")
            except:
                st.error("❌ 连接失败")
        
        with col2:
            st.write(f"**{get_text('models_downloaded')}**")
            try:
                result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
                if result.returncode == 0:
                    models = [line.split()[0] for line in result.stdout.strip().split('\n')[1:]]
                    for m in models:
                        st.code(m)
                else:
                    st.error("无法获取模型列表")
            except:
                st.error("ollama命令未找到")
        
        st.write("---")
        st.write(f"**{get_text('config_info')}**")
        st.json(config.to_dict())
        
        st.write(f"**{get_text('service_status')}**")
        st.write(f"- {get_text('entry_header')}: {'✅' if self.ai_extractor else '❌'}")
        st.write(f"- {get_text('nav_query')}: {'✅' if self.ai_answerer else '❌'}")
        st.write(f"- {get_text('nav_list')}: {'✅' if self.tx else '❌'}")
        
        st.write(f"**{get_text('session_state')}**")
        st.json({k: str(v) for k, v in st.session_state.items()})
    
    def _render_ai_test(self):
        st.subheader(get_text("ai_test_header"))
        
        test_type = st.radio(get_text("test_type"), [get_text("test_parse"), get_text("test_ocr"), get_text("test_query")])
        
        if test_type == get_text("test_parse"):
            text = st.text_area(get_text("text_placeholder"), "Lunch 35, Taxi 20")
            if st.button(get_text("test_parse"), type="primary"):
                with st.spinner("AI思考中..."):
                    try:
                        result = self.ai_extractor.from_text(text)
                        st.success(get_text("extract_success", count=len(result)))
                        for tx in result:
                            with st.expander(f"{get_text('field_merchant')}: {tx.merchant}"):
                                st.json(tx.dict())
                    except Exception as e:
                        st.error(f"失败: {e}")
        
        elif test_type == get_text("test_ocr"):
            img = st.file_uploader(get_text("upload_receipt"), type=["jpg","png"])
            if img and st.button(get_text("test_ocr"), type="primary"):
                tmp_path = f"tmp_test_{datetime.now().timestamp()}.jpg"
                try:
                    with open(tmp_path, "wb") as f:
                        f.write(img.getbuffer())
                    result = self.ai_extractor.from_image(tmp_path)
                    st.success(get_text("extract_success", count=len(result)))
                    for tx in result:
                        st.json(tx.dict())
                except Exception as e:
                    st.error(f"失败: {e}")
                finally:
                    import os
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
        
        else:  # 查询回答
            question = st.text_input(get_text("query_label"), get_text("ex_1"))
            stats = self.tx.get_stats()
            if st.button(get_text("test_query"), type="primary"):
                with st.spinner("生成回答..."):
                    try:
                        answer = self.ai_answerer.answer(question, stats)
                        st.success(get_text("query_result"))
                        st.write(answer)
                        with st.expander(get_text("query_stats")):
                            st.json(stats)
                    except Exception as e:
                        st.error(f"失败: {e}")
    
    def _render_logs(self):
        st.subheader(get_text("app_logs"))
        
        log_file = "app.log"
        if st.button(get_text("refresh_logs")):
            st.rerun()
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # 显示最近100行
            recent = lines[-100:]
            
            # 过滤选项
            level_filter = st.multiselect(
                get_text("log_level"),
                ["DEBUG", "INFO", "WARNING", "ERROR"],
                default=["INFO", "WARNING", "ERROR"]
            )
            
            filtered = [line for line in recent if any(level in line for level in level_filter)]
            
            st.code("".join(filtered), language="log")
            
            if st.button(get_text("clear_logs")):
                open(log_file, "w").close()
                st.success(get_text("success"))
                st.rerun()
        except FileNotFoundError:
            st.warning("日志文件不存在")
    
    def _render_database(self):
        st.subheader(get_text("db_status"))
        
        try:
            from database.connection import get_connection
            import sqlite3
            
            with get_connection() as conn:
                # 表信息
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                st.write(f"**{get_text('db_tables')}**")
                for table in tables:
                    st.code(table)
                    # 记录数
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    st.write(f"  {get_text('record_count')}: {count}")
                
                # 最近10笔交易
                if "transactions" in tables:
                    st.write(f"**{get_text('recent_txs')}**")
                    cursor = conn.execute(
                        "SELECT date, merchant, amount, category FROM transactions ORDER BY date DESC LIMIT 10"
                    )
                    rows = cursor.fetchall()
                    st.table([
                        {
                            get_text("field_date"): r[0], 
                            get_text("field_merchant"): r[1], 
                            get_text("field_amount"): r[2], 
                            get_text("field_category"): r[3]
                        }
                        for r in rows
                    ])
        except Exception as e:
            st.error(f"数据库错误: {e}")
