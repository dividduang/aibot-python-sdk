"""
企业微信智能机器人 Python SDK

提供 WebSocket 长连接通道，支持消息收发、事件回调、流式回复等功能。
支持单机器人和多机器人模式。
"""

from wecom_aibot.client import WSClient
from wecom_aibot.bot_manager import BotManager
from wecom_aibot.logger import DefaultLogger
from wecom_aibot.types import (
    MessageType,
    EventType,
    TemplateCardType,
    WSClientOptions,
    WsFrame,
    Logger,
    BotConfig,
    BotStatus,
    # 媒体上传类型
    WeComMediaType,
    VideoOptions,
    UploadMediaOptions,
    UploadMediaFinishResult,
)
from wecom_aibot.crypto import (
    WecomCrypto,
    decrypt_file,
    decode_encoding_aes_key,
    pkcs7_pad,
    pkcs7_unpad,
)
from wecom_aibot.exceptions import (
    UploadError,
    UploadInitError,
    UploadFinishError,
    ChunkUploadError,
)

__version__ = "0.1.0"

__all__ = [
    # Main client
    "WSClient",
    # Multi-bot manager
    "BotManager",
    # Logger
    "DefaultLogger",
    # Enums
    "MessageType",
    "EventType",
    "TemplateCardType",
    # Types
    "WSClientOptions",
    "WsFrame",
    "Logger",
    "BotConfig",
    "BotStatus",
    # Media upload types
    "WeComMediaType",
    "VideoOptions",
    "UploadMediaOptions",
    "UploadMediaFinishResult",
    # Crypto
    "WecomCrypto",
    "decrypt_file",
    "decode_encoding_aes_key",
    "pkcs7_pad",
    "pkcs7_unpad",
    # Exceptions
    "UploadError",
    "UploadInitError",
    "UploadFinishError",
    "ChunkUploadError",
]
