"""API 相关类型定义"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Any, Callable, Union, TypeAlias
from enum import StrEnum

from wecom_aibot.types.message import BaseMessage, TextMessage, ImageMessage, MixedMessage, VoiceMessage, FileMessage
from wecom_aibot.types.event import EventMessage, EnterChatEvent, TemplateCardEventData, FeedbackEventData
from wecom_aibot.types.template_card import TemplateCard


class WsCmd(StrEnum):
    """WebSocket 命令类型常量"""

    SUBSCRIBE = "aibot_subscribe"
    HEARTBEAT = "ping"
    RESPONSE = "aibot_respond_msg"
    RESPONSE_WELCOME = "aibot_respond_welcome_msg"
    RESPONSE_UPDATE = "aibot_respond_update_msg"
    SEND_MSG = "aibot_send_msg"
    CALLBACK = "aibot_msg_callback"
    EVENT_CALLBACK = "aibot_event_callback"
    # 上传相关命令
    UPLOAD_MEDIA_INIT = "aibot_upload_media_init"
    UPLOAD_MEDIA_CHUNK = "aibot_upload_media_chunk"
    UPLOAD_MEDIA_FINISH = "aibot_upload_media_finish"


@dataclass
class WsFrame:
    """
    WebSocket 帧结构

    发送和接收统一使用 { cmd, headers, body } 格式：
    - 认证发送：{ cmd: "aibot_subscribe", headers: { req_id }, body: { secret, bot_id } }
    - 消息推送：{ cmd: "aibot_msg_callback", headers: { req_id }, body: { msgid, msgtype, ... } }
    - 事件推送：{ cmd: "aibot_event_callback", headers: { req_id }, body: { event_type, ... } }
    - 回复消息：{ cmd: "aibot_respond_msg", headers: { req_id }, body: { msgtype, stream: { ... } } }
    - 回复欢迎语：{ cmd: "aibot_respond_welcome_msg", headers: { req_id }, body: { ... } }
    - 更新模板卡片：{ cmd: "aibot_respond_update_msg", headers: { req_id }, body: { ... } }
    - 心跳发送：{ cmd: "ping", headers: { req_id } }
    - 认证/心跳响应：{ headers: { req_id }, errcode: 0, errmsg: "ok" }
    """

    headers: dict[str, Any]
    cmd: str | None = None
    body: Any = None
    errcode: int | None = None
    errmsg: str | None = None


WsFrameHeaders = WsFrame  # 简化类型，仅包含 headers 的帧


@dataclass
class ReplyFeedback:
    """回复消息中的反馈信息"""

    id: str


@dataclass
class ReplyMsgItem:
    """回复消息中的图文混排子项"""

    msgtype: Literal["image"]
    image: dict[str, str]  # { base64: str, md5: str }


@dataclass
class StreamReplyBody:
    """流式回复消息体"""

    msgtype: Literal["stream"] = "stream"
    stream: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        stream_id: str,
        content: str | None = None,
        finish: bool = False,
        msg_item: list[ReplyMsgItem] | None = None,
        feedback: ReplyFeedback | None = None,
    ) -> "StreamReplyBody":
        """创建流式回复消息体"""
        stream: dict[str, Any] = {"id": stream_id}
        if content is not None:
            stream["content"] = content
        if finish:
            stream["finish"] = True
        if msg_item:
            # 调试：打印 msg_item 内容
            for i, item in enumerate(msg_item):
                print(f"[DEBUG] msg_item[{i}]: msgtype={item.msgtype}, image.keys={list(item.image.keys()) if item.image else 'None'}")
                if item.image and "base64" in item.image:
                    print(f"[DEBUG]   base64长度: {len(item.image['base64'])}, md5: {item.image.get('md5', 'N/A')[:16]}...")
            stream["msg_item"] = [{"msgtype": item.msgtype, "image": item.image} for item in msg_item]
        if feedback:
            stream["feedback"] = {"id": feedback.id}
        return cls(stream=stream)


@dataclass
class WelcomeTextReplyBody:
    """欢迎语回复消息体（文本类型）"""

    msgtype: Literal["text"] = "text"
    text: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(cls, content: str) -> "WelcomeTextReplyBody":
        return cls(text={"content": content})


@dataclass
class WelcomeTemplateCardReplyBody:
    """欢迎语回复消息体（模板卡片类型）"""

    msgtype: Literal["template_card"] = "template_card"
    template_card: TemplateCard = field(default_factory=TemplateCard)


@dataclass
class SendMarkdownMsgBody:
    """主动发送 Markdown 消息体"""

    msgtype: Literal["markdown"] = "markdown"
    markdown: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(cls, content: str) -> "SendMarkdownMsgBody":
        return cls(markdown={"content": content})


@dataclass
class SendTemplateCardMsgBody:
    """主动发送模板卡片消息体"""

    msgtype: Literal["template_card"] = "template_card"
    template_card: TemplateCard = field(default_factory=TemplateCard)


# 事件回调类型
MessageCallback: TypeAlias = Callable[[WsFrame], None]
EventCallback: TypeAlias = Callable[[WsFrame], None]
VoidCallback: TypeAlias = Callable[[], None]
ErrorCallback: TypeAlias = Callable[[Exception], None]
ReconnectingCallback: TypeAlias = Callable[[int], None]
DisconnectedCallback: TypeAlias = Callable[[str], None]


@dataclass
class WSClientEventMap:
    """WSClient 事件映射类型（用于类型提示）"""

    # 消息事件
    message: MessageCallback | None = None
    message_text: MessageCallback | None = None
    message_image: MessageCallback | None = None
    message_mixed: MessageCallback | None = None
    message_voice: MessageCallback | None = None
    message_file: MessageCallback | None = None
    # 事件回调
    event: EventCallback | None = None
    event_enter_chat: EventCallback | None = None
    event_template_card_event: EventCallback | None = None
    event_feedback_event: EventCallback | None = None
    event_topic: EventCallback | None = None
    event_topic_at_bot: EventCallback | None = None
    event_topic_event: EventCallback | None = None
    # 连接事件
    connected: VoidCallback | None = None
    authenticated: VoidCallback | None = None
    disconnected: DisconnectedCallback | None = None
    reconnecting: ReconnectingCallback | None = None
    error: ErrorCallback | None = None


# ========== 媒体消息类型 ==========

WeComMediaType = Literal["file", "image", "voice", "video"]


@dataclass
class VideoOptions:
    """视频消息选项"""
    title: str | None = None
    description: str | None = None


@dataclass
class UploadMediaOptions:
    """上传素材选项"""
    type: WeComMediaType
    filename: str

    def __post_init__(self):
        """验证必填字段"""
        if not self.filename or not self.filename.strip():
            raise ValueError("filename 不能为空")
        valid_types = ("file", "image", "voice", "video")
        if self.type not in valid_types:
            raise ValueError(f"type 必须是 {valid_types} 之一，实际为: {self.type}")


@dataclass
class UploadMediaFinishResult:
    """上传完成结果"""
    type: WeComMediaType
    media_id: str
    created_at: str

    @classmethod
    def from_response(cls, body: dict) -> "UploadMediaFinishResult":
        """从 API 响应创建实例"""
        return cls(
            type=body.get("type"),
            media_id=body.get("media_id"),
            created_at=body.get("created_at"),
        )
