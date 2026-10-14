"""
消息处理器
负责解析 WebSocket 帧并分发为具体的消息事件和事件回调
"""

from __future__ import annotations
from dataclasses import fields
from typing import TYPE_CHECKING, Any, TypeVar

from wecom_aibot.types import Logger, WsFrame
from wecom_aibot.types.message import (
    MessageType,
    BaseMessage,
    TextMessage,
    ImageMessage,
    MixedMessage,
    VoiceMessage,
    FileMessage,
    VideoMessage,
    TextContent,
    ImageContent,
    VoiceContent,
    FileContent,
    VideoContent,
    MixedContent,
    MixedMsgItem,
    MessageFrom,
    QuoteContent,
    CompatInfo,
)
from wecom_aibot.types.event import (
    EventType,
    EventMessage,
    EventFrom,
    EnterChatEvent,
    TemplateCardEventData,
    FeedbackEventData,
    TopicAtBotEvent,
    TopicEvent,
    UnknownEvent,
)
from wecom_aibot.types.api import WsCmd
from wecom_aibot.logger import DefaultLogger

if TYPE_CHECKING:
    from wecom_aibot.client import WSClient

_MsgT = TypeVar("_MsgT", bound=BaseMessage)


class MessageHandler:
    """
    消息处理器

    负责：
    - 解析 WebSocket 帧
    - 将消息分发为具体的事件类型
    """

    def __init__(self, logger: Logger | None = None):
        self.logger = logger or DefaultLogger()

    def handle_frame(self, frame: WsFrame, emitter: "WSClient") -> None:
        """
        处理收到的 WebSocket 帧，解析并触发对应的消息/事件

        WebSocket 推送帧结构：
        - 消息推送：{ cmd: "aibot_msg_callback", headers: { req_id: "xxx" }, body: { msgid, msgtype, ... } }
        - 事件推送：{ cmd: "aibot_event_callback", headers: { req_id: "xxx" }, body: { msgid, msgtype: "event", event: { ... } } }

        Args:
            frame: WebSocket 接收帧
            emitter: WSClient 实例，用于触发事件
        """
        if frame.cmd == WsCmd.CALLBACK:
            self._handle_message_callback(frame, emitter)
        elif frame.cmd == WsCmd.EVENT_CALLBACK:
            self._handle_event_callback(frame, emitter)
        else:
            self.logger.warn(f"未知的命令类型: {frame.cmd}")

    def _handle_message_callback(self, frame: WsFrame, emitter: "WSClient") -> None:
        """处理消息推送回调 (aibot_msg_callback)"""
        body = frame.body
        if not body:
            return

        msgtype = body.get("msgtype", "")
        if not msgtype:
            self.logger.warn("消息缺少 msgtype 字段")
            return

        # 解析基础消息
        base_msg = self._parse_base_message(body)

        # 触发通用消息事件
        emitter.emit("message", frame)

        # 根据消息类型触发特定事件
        if msgtype == MessageType.TEXT:
            message = self._parse_text_message(body, base_msg)
            emitter.emit("message.text", WsFrame(headers=frame.headers, cmd=frame.cmd, body=message))
        elif msgtype == MessageType.IMAGE:
            message = self._parse_image_message(body, base_msg)
            emitter.emit("message.image", WsFrame(headers=frame.headers, cmd=frame.cmd, body=message))
        elif msgtype == MessageType.MIXED:
            message = self._parse_mixed_message(body, base_msg)
            emitter.emit("message.mixed", WsFrame(headers=frame.headers, cmd=frame.cmd, body=message))
        elif msgtype == MessageType.VOICE:
            message = self._parse_voice_message(body, base_msg)
            emitter.emit("message.voice", WsFrame(headers=frame.headers, cmd=frame.cmd, body=message))
        elif msgtype == MessageType.FILE:
            message = self._parse_file_message(body, base_msg)
            emitter.emit("message.file", WsFrame(headers=frame.headers, cmd=frame.cmd, body=message))
        elif msgtype == MessageType.VIDEO:
            message = self._parse_video_message(body, base_msg)
            emitter.emit("message.video", WsFrame(headers=frame.headers, cmd=frame.cmd, body=message))
        else:
            self.logger.debug(f"未处理的消息类型: {msgtype}")

    def _handle_event_callback(self, frame: WsFrame, emitter: "WSClient") -> None:
        """处理事件推送回调 (aibot_event_callback)"""
        body = frame.body
        if not body:
            return

        event_data = body.get("event", {})
        if not event_data:
            self.logger.warn("事件回调缺少 event 字段")
            return

        event_type = event_data.get("eventtype", "")

        # 解析事件消息
        event_msg = self._parse_event_message(body, event_data)

        # 触发通用事件
        emitter.emit("event", WsFrame(headers=frame.headers, cmd=frame.cmd, body=event_msg))

        # 根据事件类型触发特定事件
        if event_type == EventType.ENTER_CHAT:
            emitter.emit("event.enter_chat", WsFrame(headers=frame.headers, cmd=frame.cmd, body=event_msg))
        elif event_type == EventType.TEMPLATE_CARD_EVENT:
            emitter.emit("event.template_card_event", WsFrame(headers=frame.headers, cmd=frame.cmd, body=event_msg))
        elif event_type == EventType.FEEDBACK_EVENT:
            emitter.emit("event.feedback_event", WsFrame(headers=frame.headers, cmd=frame.cmd, body=event_msg))
        elif event_type == EventType.TOPIC_AT_BOT:
            emitter.emit("event.topic_at_bot", WsFrame(headers=frame.headers, cmd=frame.cmd, body=event_msg))
        elif event_type == EventType.TOPIC_EVENT:
            emitter.emit("event.topic_event", WsFrame(headers=frame.headers, cmd=frame.cmd, body=event_msg))

        # 所有频道（话题）事件统一走 event.topic
        if isinstance(event_type, str) and event_type.startswith("topic"):
            emitter.emit("event.topic", WsFrame(headers=frame.headers, cmd=frame.cmd, body=event_msg))

    def _parse_base_message(self, body: dict[str, Any]) -> BaseMessage:
        """解析基础消息字段"""
        from_data = body.get("from", {})

        # 解析引用内容
        quote = None
        if "quote" in body:
            quote = self._parse_quote_content(body["quote"])

        return BaseMessage(
            msgid=body.get("msgid", ""),
            aibotid=body.get("aibotid", ""),
            chattype=body.get("chattype", "single"),
            from_=MessageFrom(userid=from_data.get("userid", "")),
            msgtype=body.get("msgtype", ""),
            chatid=body.get("chatid"),
            create_time=body.get("create_time"),
            response_url=body.get("response_url"),
            quote=quote,
            compat_info=self._parse_compat_info(body.get("compat_info")),
            _raw=body,
        )

    def _parse_compat_info(self, data: Any) -> CompatInfo | None:
        """解析兼容信息（频道消息的 source=channel 由此判定）"""
        if not isinstance(data, dict):
            return None
        return CompatInfo(source=data.get("source"), _raw=data)

    def _build_message(self, payload_cls: type[_MsgT], base: BaseMessage, **extra: Any) -> _MsgT:
        """在 BaseMessage 之上构造具体消息类型，基础字段（含 compat_info）自动继承"""
        return payload_cls(**{f.name: getattr(base, f.name) for f in fields(base)}, **extra)

    def _parse_text_message(self, body: dict[str, Any], base: BaseMessage) -> TextMessage:
        """解析文本消息"""
        text_data = body.get("text", {})
        return self._build_message(
            TextMessage,
            base,
            text=TextContent(content=text_data.get("content", "")),
        )

    def _parse_image_message(self, body: dict[str, Any], base: BaseMessage) -> ImageMessage:
        """解析图片消息"""
        image_data = body.get("image", {})
        return self._build_message(
            ImageMessage,
            base,
            image=ImageContent(
                url=image_data.get("url", ""),
                aeskey=image_data.get("aeskey"),
            ),
        )

    def _parse_mixed_message(self, body: dict[str, Any], base: BaseMessage) -> MixedMessage:
        """解析图文混排消息"""
        mixed_data = body.get("mixed", {})
        msg_items = []
        for item in mixed_data.get("msg_item", []):
            msgtype = item.get("msgtype", "text")
            text = None
            image = None
            if msgtype == "text":
                text = TextContent(content=item.get("text", {}).get("content", ""))
            elif msgtype == "image":
                img_data = item.get("image", {})
                image = ImageContent(url=img_data.get("url", ""), aeskey=img_data.get("aeskey"))
            msg_items.append(MixedMsgItem(msgtype=msgtype, text=text, image=image))

        return self._build_message(
            MixedMessage,
            base,
            mixed=MixedContent(msg_item=msg_items),
        )

    def _parse_voice_message(self, body: dict[str, Any], base: BaseMessage) -> VoiceMessage:
        """解析语音消息"""
        voice_data = body.get("voice", {})
        return self._build_message(
            VoiceMessage,
            base,
            voice=VoiceContent(content=voice_data.get("content", "")),
        )

    def _parse_file_message(self, body: dict[str, Any], base: BaseMessage) -> FileMessage:
        """解析文件消息"""
        file_data = body.get("file", {})
        return self._build_message(
            FileMessage,
            base,
            file=FileContent(
                url=file_data.get("url", ""),
                aeskey=file_data.get("aeskey"),
            ),
        )

    def _parse_video_message(self, body: dict[str, Any], base: BaseMessage) -> VideoMessage:
        """解析视频消息"""
        video_data = body.get("video", {})
        return self._build_message(
            VideoMessage,
            base,
            video=VideoContent(
                url=video_data.get("url", ""),
                aeskey=video_data.get("aeskey"),
            ),
        )

    def _parse_quote_content(self, quote_data: dict[str, Any]) -> QuoteContent:
        """解析引用内容"""
        msgtype = quote_data.get("msgtype", "text")
        quote = QuoteContent(msgtype=msgtype)

        if msgtype == "text":
            text_data = quote_data.get("text", {})
            quote.text = TextContent(content=text_data.get("content", ""))
        elif msgtype == "image":
            img_data = quote_data.get("image", {})
            quote.image = ImageContent(url=img_data.get("url", ""), aeskey=img_data.get("aeskey"))
        elif msgtype == "file":
            file_data = quote_data.get("file", {})
            quote.file = FileContent(url=file_data.get("url", ""), aeskey=file_data.get("aeskey"))
        elif msgtype == "video":
            video_data = quote_data.get("video", {})
            quote.video = VideoContent(url=video_data.get("url", ""), aeskey=video_data.get("aeskey"))
        elif msgtype == "voice":
            voice_data = quote_data.get("voice", {})
            quote.voice = VoiceContent(content=voice_data.get("content", ""))
        elif msgtype == "mixed":
            mixed_data = quote_data.get("mixed", {})
            msg_items = []
            for item in mixed_data.get("msg_item", []):
                item_type = item.get("msgtype", "text")
                text = None
                image = None
                if item_type == "text":
                    text = TextContent(content=item.get("text", {}).get("content", ""))
                elif item_type == "image":
                    img_data = item.get("image", {})
                    image = ImageContent(url=img_data.get("url", ""), aeskey=img_data.get("aeskey"))
                msg_items.append(MixedMsgItem(msgtype=item_type, text=text, image=image))
            quote.mixed = MixedContent(msg_item=msg_items)

        return quote

    def _parse_event_message(self, body: dict[str, Any], event_data: dict[str, Any]) -> EventMessage:
        """解析事件消息"""
        from_data = body.get("from", {})
        event_type = event_data.get("eventtype", "")

        # 解析事件内容
        event_content: (
            EnterChatEvent
            | TemplateCardEventData
            | FeedbackEventData
            | TopicAtBotEvent
            | TopicEvent
            | UnknownEvent
        )
        if event_type == EventType.ENTER_CHAT:
            event_content = EnterChatEvent()
        elif event_type == EventType.TEMPLATE_CARD_EVENT:
            event_content = TemplateCardEventData(
                event_key=event_data.get("event_key"),
                task_id=event_data.get("task_id"),
            )
        elif event_type == EventType.FEEDBACK_EVENT:
            event_content = FeedbackEventData()
        elif event_type == EventType.TOPIC_AT_BOT:
            event_content = TopicAtBotEvent(post_id=(event_data.get("topic_at_bot") or {}).get("post_id"))
        elif event_type == EventType.TOPIC_EVENT:
            topic_event = event_data.get("topic_event") or {}
            event_content = TopicEvent(
                type=topic_event.get("type"),
                post_id=topic_event.get("post_id"),
                data=dict(event_data),
            )
        else:
            # 未知事件类型，保留原始数据避免信息丢失
            self.logger.debug(f"未处理的事件类型: {event_type}")
            event_content = UnknownEvent(eventtype=event_type, data=dict(event_data))

        return EventMessage(
            msgid=body.get("msgid", ""),
            create_time=body.get("create_time", 0),
            aibotid=body.get("aibotid", ""),
            from_=EventFrom(
                userid=from_data.get("userid", ""),
                corpid=from_data.get("corpid"),
            ),
            msgtype="event",
            event=event_content,
            chatid=body.get("chatid"),
            chattype=body.get("chattype"),
            topic_id=body.get("topic_id"),
            compat_info=self._parse_compat_info(body.get("compat_info")),
            _raw=body,
        )
