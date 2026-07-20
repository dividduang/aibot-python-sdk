"""消息相关类型定义"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Any
from enum import StrEnum


class MessageType(StrEnum):
    """消息类型枚举"""

    TEXT = "text"
    IMAGE = "image"
    MIXED = "mixed"
    VOICE = "voice"
    FILE = "file"
    VIDEO = "video"


@dataclass
class TextContent:
    """文本结构体"""

    content: str


@dataclass
class ImageContent:
    """图片结构体"""

    url: str
    aeskey: str | None = None


@dataclass
class VoiceContent:
    """语音结构体"""

    content: str


@dataclass
class FileContent:
    """文件结构体"""

    url: str
    aeskey: str | None = None


@dataclass
class VideoContent:
    """视频结构体"""

    url: str
    aeskey: str | None = None


@dataclass
class MixedMsgItem:
    """图文混排子项"""

    msgtype: Literal["text", "image"]
    text: TextContent | None = None
    image: ImageContent | None = None


@dataclass
class MixedContent:
    """图文混排结构体"""

    msg_item: list[MixedMsgItem]


@dataclass
class QuoteContent:
    """引用结构体"""

    msgtype: Literal["text", "image", "mixed", "voice", "file", "video"]
    text: TextContent | None = None
    image: ImageContent | None = None
    mixed: MixedContent | None = None
    voice: VoiceContent | None = None
    file: FileContent | None = None
    video: VideoContent | None = None


@dataclass
class MessageFrom:
    """消息发送者信息"""

    userid: str


@dataclass
class BaseMessage:
    """基础消息结构"""

    msgid: str
    aibotid: str
    chattype: Literal["single", "group"]
    from_: MessageFrom
    msgtype: MessageType | str
    chatid: str | None = None
    create_time: int | None = None
    response_url: str | None = None
    quote: QuoteContent | None = None
    # 原始数据
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        # 存储原始数据
        if not self._raw:
            self._raw = {}


@dataclass
class TextMessage(BaseMessage):
    """文本消息"""

    msgtype: Literal[MessageType.TEXT] = MessageType.TEXT
    text: TextContent = field(default_factory=lambda: TextContent(""))


@dataclass
class ImageMessage(BaseMessage):
    """图片消息"""

    msgtype: Literal[MessageType.IMAGE] = MessageType.IMAGE
    image: ImageContent = field(default_factory=lambda: ImageContent(""))


@dataclass
class MixedMessage(BaseMessage):
    """图文混排消息"""

    msgtype: Literal[MessageType.MIXED] = MessageType.MIXED
    mixed: MixedContent = field(default_factory=lambda: MixedContent([]))


@dataclass
class VoiceMessage(BaseMessage):
    """语音消息"""

    msgtype: Literal[MessageType.VOICE] = MessageType.VOICE
    voice: VoiceContent = field(default_factory=lambda: VoiceContent(""))


@dataclass
class FileMessage(BaseMessage):
    """文件消息"""

    msgtype: Literal[MessageType.FILE] = MessageType.FILE
    file: FileContent = field(default_factory=lambda: FileContent(""))


@dataclass
class VideoMessage(BaseMessage):
    """视频消息"""

    msgtype: Literal[MessageType.VIDEO] = MessageType.VIDEO
    video: VideoContent = field(default_factory=lambda: VideoContent(""))
