"""
语音服务：使用本地 Whisper 模型将语音转换为文字。
支持 faster-whisper（推荐）和 openai-whisper 两种后端。
"""
from logging_config import logger


class WhisperService:
    """
    本地 Whisper 语音转文字服务。
    
    推荐安装 faster-whisper：
        pip install faster-whisper
    
    备用 openai-whisper：
        pip install openai-whisper
    """
    
    def __init__(self, model_size: str = "small", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self._model = None
        self._backend = None
    
    def _load_model(self):
        """延迟加载模型（首次调用时加载）"""
        if self._model is not None:
            return
        
        # 优先尝试 faster-whisper（性能更好）
        try:
            from faster_whisper import WhisperModel
            logger.info(f"加载 faster-whisper 模型：{self.model_size}（{self.device}）")
            self._model = WhisperModel(self.model_size, device=self.device, compute_type="int8")
            self._backend = "faster-whisper"
            logger.info("✅ faster-whisper 模型加载成功")
            return
        except ImportError:
            logger.debug("faster-whisper 不可用，尝试 openai-whisper...")
        
        # 降级到 openai-whisper
        try:
            import whisper
            logger.info(f"加载 openai-whisper 模型：{self.model_size}")
            self._model = whisper.load_model(self.model_size)
            self._backend = "openai-whisper"
            logger.info("✅ openai-whisper 模型加载成功")
            return
        except ImportError:
            raise ImportError(
                "未找到 Whisper 依赖。请安装：\n"
                "  pip install faster-whisper  （推荐）\n"
                "  或 pip install openai-whisper"
            )
    
    def transcribe(self, audio_path: str, language: str = "zh") -> str:
        """
        将音频文件转换为文字。
        
        Args:
            audio_path: 音频文件路径（WAV/MP3/M4A 等格式）
            language: 语言代码，默认 "zh"（中文）
        
        Returns:
            转录文本字符串
        """
        self._load_model()
        
        logger.info(f"🎤 开始转录：{audio_path}（语言：{language}）")
        
        if self._backend == "faster-whisper":
            segments, info = self._model.transcribe(
                audio_path,
                language=language,
                beam_size=5
            )
            text = " ".join(seg.text.strip() for seg in segments)
        else:
            result = self._model.transcribe(audio_path, language=language)
            text = result["text"].strip()
        
        logger.info(f"✅ 转录完成：{text[:80]}...")
        return text
    
    @staticmethod
    def is_available() -> bool:
        """检测 Whisper 是否可用"""
        try:
            import faster_whisper
            return True
        except ImportError:
            pass
        try:
            import whisper
            return True
        except ImportError:
            return False
