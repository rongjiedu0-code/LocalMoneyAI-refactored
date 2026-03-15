import streamlit as st
import os
from datetime import datetime
from logging_config import logger
from config_loader import config
from utils.i18n import get_text

class QuickEntryPage:
    def __init__(self, tx_service):
        self.tx_service = tx_service
    
    def render(self):
        st.header(get_text("entry_header"))
        
        # 初始化暂存区状态
        if "staging_txs" not in st.session_state:
            st.session_state.staging_txs = []
            
        # 输入区
        col1, col2 = st.columns(2)
        with col1:
            self._render_image_upload()
        with col2:
            self._render_text_input()
        
        self._render_voice_input()
        self._render_staging_area()
    
    def _render_image_upload(self):
        st.subheader(get_text("image_header"))
        img = st.file_uploader(get_text("upload_receipt"), type=["jpg","png","jpeg"], key="img_upload")
        if img:
            st.image(img, use_column_width=True)
            if st.button(get_text("identify_save"), type="primary", key="img_btn"):
                self._handle_image(img)
    
    def _handle_image(self, img_file):
        tmp_path = f"tmp_{datetime.now().timestamp()}.jpg"
        try:
            with open(tmp_path, "wb") as f:
                f.write(img_file.getbuffer())
                
            with st.spinner(get_text("ai_extracting")):
                result = self.tx_service.extract_from_image(tmp_path)
                
            if result:
                st.session_state.staging_txs.extend(result)
                st.success(get_text("img_extract_success", count=len(result)))
            else:
                st.warning(get_text("not_record_warning"))
        except Exception as e:
            logger.error(f"图片处理失败: {e}", exc_info=True)
            st.error(f"{get_text('extract_fail')}: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def _render_text_input(self):
        st.subheader(get_text("text_header"))
        text = st.text_area(
            get_text("text_placeholder"),
            height=100,
            key="text_input",
            placeholder=get_text("text_placeholder")
        )
        if st.button(get_text("ai_refining"), type="primary", key="text_btn") and text.strip():
            try:
                with st.spinner(get_text("ai_analyzing")):
                    result = self.tx_service.extract_from_text(text)
                if result:
                    st.session_state.staging_txs.extend(result)
                    st.success(get_text("text_extract_success", count=len(result)))
                else:
                    st.warning(get_text("not_record_warning"))
            except Exception as e:
                logger.error(f"文本处理失败: {e}", exc_info=True)
                st.error(f"{get_text('extract_fail')}: {e}")

    def _render_voice_input(self):
        """语音输入区（仅在 Whisper 可用时展示）"""
        from services.audio.whisper_service import WhisperService
        if not WhisperService.is_available():
            return
        
        st.divider()
        st.subheader(get_text("voice_header"))
        
        try:
            from audio_recorder_streamlit import audio_recorder
            audio_bytes = audio_recorder(
                text=get_text("press_record"),
                recording_color="#e74c3c",
                neutral_color="#3498db",
                icon_name="microphone",
                icon_size="2x"
            )
        except ImportError:
            st.info(f"💡 {get_text('install_audio_hint')}: `pip install audio-recorder-streamlit`")
            return
        
        if audio_bytes:
            try:
                import tempfile, os
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(audio_bytes)
                    tmp_path = tmp.name
                
                with st.spinner(get_text("whisper_transcribing")):
                    whisper = WhisperService(model_size="small", device="cpu")
                    text = whisper.transcribe(tmp_path)
                    os.unlink(tmp_path)
                
                st.info(f'{get_text("transcribe_result")}："{text}"')
                
                if text.strip():
                    with st.spinner(get_text("ai_analyzing")):
                        result = self.tx_service.extract_from_text(text)
                    if result:
                        st.session_state.staging_txs.extend(result)
                        st.success(get_text("text_extract_success", count=len(result)))
                        st.rerun()
                    else:
                        st.warning(get_text("not_record_warning"))
            except Exception as e:
                logger.error(f"语音记账失败: {e}", exc_info=True)
                st.error(f"❌ 语音处理失败: {e}")

    def _render_staging_area(self):
        """渲染核对和入库的暂存区UI"""
        if not st.session_state.staging_txs:
            return
            
        st.divider()
        st.subheader(get_text("staging_header"))
        st.info(get_text("staging_info"))
        
        import pandas as pd
        from datetime import date as date_type
        
        # 将暂存数据转为 DataFrame 显示
        df = pd.DataFrame(st.session_state.staging_txs)
        
        # 配置列展示
        column_config = {
            "date": st.column_config.TextColumn(f"{get_text('field_date')} (YYYY-MM-DD)", help="e.g. 2024-01-30", required=True),
            "merchant": st.column_config.TextColumn(get_text('field_merchant'), required=True),
            "amount": st.column_config.NumberColumn(get_text('field_amount'), required=True),
            "category": st.column_config.SelectboxColumn(
                get_text('field_category'),
                options=config.EXPENSE_CATEGORIES,
                required=True,
            ),
            "description": st.column_config.TextColumn(get_text('field_description')),
            "confidence": None,
            "items": None
        }
        
        edited_df = st.data_editor(
            df,
            column_config=column_config,
            num_rows="dynamic",
            use_container_width=True,
            key="staging_editor",
            hide_index=True
        )
        
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button(get_text("confirm_save"), type="primary", use_container_width=True):
                try:
                    # 获取编辑后的数据重新构造列表
                    final_txs = edited_df.to_dict('records')
                    # 将 date 转回字符串，清洗 NaN
                    for tx in final_txs:
                        d = tx.get('date')
                        if d is not None and not (isinstance(d, float)):
                            tx['date'] = str(d)
                        if pd.isna(tx.get('description')): tx['description'] = ''
                    
                    count = self.tx_service.save_transactions(final_txs)
                    st.toast(get_text("save_success", count=count))
                    st.session_state.staging_txs = []
                    st.rerun()
                except Exception as e:
                    st.error(f"入库失败: {e}")
        with col2:
            if st.button(get_text("clear_staging"), use_container_width=False):
                st.session_state.staging_txs = []
                st.rerun()
