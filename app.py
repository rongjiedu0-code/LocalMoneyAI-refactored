import streamlit as st
import json
import os
from datetime import datetime
from config_loader import config_manager, config
from logging_config import logger
from services.transaction.service import TransactionService
from services.backup import BackupService
import plotly.express as px
import pandas as pd
from utils.i18n import get_text

# 1. 官方配置：隐藏开发者工具栏（包含 Deploy 按钮）
st.set_option("client.toolbarMode", "viewer")

st.set_page_config(
    page_title=f"Local Money AI ({config.ENV if hasattr(config, 'ENV') else 'dev'})",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 注入统一的样式：隐藏所有不需要的 UI 元素并美化
st.markdown("""
    <style>
        /* 彻底隐藏 Deploy 按钮 (适配 1.40+) */
        .stAppDeployButton, [data-testid="stAppDeployButton"], 
        .stDeployButton, [data-testid="stDeployButton"] {
            display: none !important;
        }

        /* 隐藏顶部导航栏背景和右侧菜单/页脚 */
        header[data-testid="stHeader"] { 
            background-color: rgba(0,0,0,0) !important; 
            border: none !important;
            box-shadow: none !important;
        }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        
        /* 布局微调：主内容区域顶部填充减小 */
        .block-container { padding-top: 2rem !important; }
        
        /* 交互动效与圆角美化 */
        .stButton > button { transition: transform 0.1s ease, box-shadow 0.1s ease; }
        .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        div[data-testid="stDataEditor"] { border-radius: 10px; overflow: hidden; }
        div[data-testid="stAlert"] { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# 初始化语言状态
if "language" not in st.session_state:
    st.session_state.language = getattr(config, "DEFAULT_LANGUAGE", "zh")

# 侧边栏：状态与控制
st.sidebar.title(get_text("sidebar_title"))

# 语言切换
lang_options = {"中文": "zh", "English": "en"}
current_lang_name = "中文" if st.session_state.language == "zh" else "English"
new_lang_name = st.sidebar.selectbox("🌐 Language", options=list(lang_options.keys()), index=list(lang_options.keys()).index(current_lang_name))
if lang_options[new_lang_name] != st.session_state.language:
    st.session_state.language = lang_options[new_lang_name]
    st.rerun()

# 配置重载按钮
if st.sidebar.button(get_text("reload_config")):
    st.cache_resource.clear()
    config_manager.reload()
    st.rerun()

with st.sidebar.expander(f"ℹ️ {get_text('guide_header')}", expanded=False):
    st.markdown(f"""
    - {get_text('guide_ollama')}
    - {get_text('guide_models')}
    - {get_text('guide_desktop')}
    
    ---
    *{get_text('guide_contact')}*
    """)

st.sidebar.info(f"""
**{get_text('env')}**: {os.getenv('APP_ENV', 'dev')} | **Ollama**: {config.OLLAMA_HOST}  
**{get_text('model')}**: {config.TEXT_MODEL}  
**{get_text('fallback')}**: {get_text('enabled') if config.ENABLE_FALLBACK else get_text('disabled')}
""")

# 每日自动备份（只运行一次）
if "backup_done" not in st.session_state:
    try:
        backup_svc = BackupService(db_path=config.DB_PATH)
        bak = backup_svc.backup()
        st.session_state.backup_done = True
        if bak:
            st.sidebar.toast(get_text("auto_backup_success"), icon="✅")
    except Exception as e:
        logger.warning(f"自动备份失败（非致命）: {e}")
        st.session_state.backup_done = True  # 避免反复尝试

# 初始化服务（带异常处理，使用依赖注入）
@st.cache_resource
def get_services():
    try:
        from services.ai import create_extractor, OllamaClient, prompt_manager
        from services.ai.answerer import AIAnswerer
        from config_loader import config
        from database.connection import init_pool
        from database.schema import init_schema
        # 初始化数据库连接池
        init_pool(config.DB_PATH)
        # 初始化数据库模式（如创建 transactions 表等）
        init_schema()
        client = OllamaClient()
        ai_extractor = create_extractor(
            client=client,
            config=config,
            prompt_manager=prompt_manager,
            fallback_enabled=config.ENABLE_FALLBACK
        )
        ai_answerer = AIAnswerer(client=client, model=config.TEXT_MODEL)
        
        tx_service = TransactionService(
            ai_extractor=ai_extractor,
            answerer=ai_answerer
        )
        
        return ai_extractor, ai_answerer, tx_service
    except Exception as e:
        logger.error(f"服务初始化失败: {e}", exc_info=True)
        st.error(f"服务初始化失败: {e}")
        st.stop()

try:
    ai_extractor, ai_answerer, tx_service = get_services()
except:
    st.stop()

# 页面路由
pages = {
    get_text("nav_entry"): "entry",
    get_text("nav_importer"): "importer",
    get_text("nav_query"): "query",
    get_text("nav_report"): "report",
    get_text("nav_list"): "list",
    get_text("nav_debug"): "debug"
}

page_label = st.sidebar.radio(
    get_text("nav_label"),
    list(pages.keys()),
    label_visibility="collapsed"
)

page_key = pages[page_label]

if page_key == "entry":
    from views.quick_entry import QuickEntryPage
    QuickEntryPage(tx_service).render()

elif page_key == "importer":
    from views.importer import ImporterPage
    ImporterPage(tx_service).render()
    
elif page_key == "query":
    from views.query import QueryPage
    QueryPage(tx_service).render()
    
elif page_key == "report":
    from views.report import ReportPage
    ReportPage(tx_service).render()
    
elif page_key == "list":
    from views.list import ListPage
    ListPage(tx_service).render()
    
elif page_key == "debug":
    from views.debug import DebugPage
    DebugPage(ai_extractor, ai_answerer, tx_service).render()

st.sidebar.markdown("---")
st.sidebar.caption(get_text("version_info"))
