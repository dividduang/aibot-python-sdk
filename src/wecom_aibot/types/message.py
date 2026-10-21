"""消息相关类型定义"""

from __future__ import annotations
import re
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


class MessageSource(StrEnum):
    """消息来源（compat_info.source）

    注意：频道消息的 chattype 仍为 group，判定频道必须看 compat_info.source
    """

    CHANNEL = "channel"


@dataclass
class CompatInfo:
    """兼容信息结构体"""

    source: MessageSource | str | None = None
    # 原始数据
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)


def is_channel_source(compat_info: CompatInfo | None) -> bool:
    """判断 compat_info 是否表示消息来自「频道」"""
    return compat_info is not None and compat_info.source == MessageSource.CHANNEL


# 正文中的 @提及，形如 "@某人 内容"
_AT_PATTERN = re.compile(r"@([^\s@]+)")
_MENTION_PREFIX = re.compile(r"\s*@\S+")


def parse_at_list(text_contents: list[str]) -> list[str]:
    """提取文本片段中的 @提及名称

    实测企微把 @前缀原样放在正文里（如 "@邓景仁的机器人 hello"），
    因此提及名以空白为界。
    """
    at_list: list[str] = []
    for content in text_contents:
        at_list.extend(_AT_PATTERN.findall(content))
    return at_list


def is_mention_text(text_contents: list[str]) -> bool:
    """判断消息是否以 @ 开头（是否在呼叫机器人）"""
    for content in text_contents:
        if content.strip():
            return bool(_MENTION_PREFIX.match(content))
    return False


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
    compat_info: CompatInfo | None = None
    # 频道（话题）ID：消息体通常不携带，事件体才有
    topic_id: str | None = None
    # 正文中的 @提及（保留原始提及名，便于调用方自行判定）
    at_list: list[str] = field(default_factory=list)
    # 正文是否以 @ 开头，即是否在呼叫机器人
    is_mention: bool = False
    # 原始数据
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        # 存储原始数据
        if not self._raw:
            self._raw = {}

    @property
    def is_channel(self) -> bool:
        """消息是否来自「频道」（chattype 仍为 group，需看 compat_info.source）"""
        return is_channel_source(self.compat_info)

    @property
    def topic_key(self) -> str | None:
        """标识所属话题的唯一键：优先 topic_id，回退 chatid

        实测频道消息体只有 chatid，而 topic_at_bot 事件体只有 topic_id，
        两者 id 前缀空间不同，不能互相当作同一个 key。
        """
        return self.topic_id or self.chatid


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
