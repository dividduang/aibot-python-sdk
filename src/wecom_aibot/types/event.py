"""事件相关类型定义"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal
from enum import StrEnum

from wecom_aibot.types.message import CompatInfo, is_channel_source


class EventType(StrEnum):
    """事件类型枚举"""

    ENTER_CHAT = "enter_chat"
    TEMPLATE_CARD_EVENT = "template_card_event"
    FEEDBACK_EVENT = "feedback_event"
    # 频道（话题）相关
    TOPIC_AT_BOT = "topic_at_bot"
    TOPIC_EVENT = "topic_event"


@dataclass
class EventFrom:
    """事件发送者信息（比 MessageFrom 多了 corpid 字段）"""

    userid: str
    corpid: str | None = None


@dataclass
class EnterChatEvent:
    """进入会话事件"""

    eventtype: Literal[EventType.ENTER_CHAT] = EventType.ENTER_CHAT


@dataclass
class TemplateCardEventData:
    """模板卡片事件"""

    eventtype: Literal[EventType.TEMPLATE_CARD_EVENT] = EventType.TEMPLATE_CARD_EVENT
    event_key: str | None = None
    task_id: str | None = None


@dataclass
class FeedbackEventData:
    """用户反馈事件"""

    eventtype: Literal[EventType.FEEDBACK_EVENT] = EventType.FEEDBACK_EVENT


@dataclass
class TopicAtBotEvent:
    """频道（话题）中 @机器人 事件"""

    eventtype: Literal[EventType.TOPIC_AT_BOT] = EventType.TOPIC_AT_BOT
    # 被 @ 的帖子 ID
    post_id: str | None = None


@dataclass
class TopicEvent:
    """频道（话题）事件

    实测载荷：{"eventtype": "topic_event", "topic_event": {"type": 1, "post_id": "..."}}
    type 的具体语义未公开，data 保留完整原始事件供后续扩展
    """

    eventtype: Literal[EventType.TOPIC_EVENT] = EventType.TOPIC_EVENT
    type: int | None = None
    post_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class UnknownEvent:
    """未识别的事件类型，保留原始数据避免信息丢失"""

    eventtype: str
    data: dict[str, Any] = field(default_factory=dict)


EventContent = (
    EnterChatEvent
    | TemplateCardEventData
    | FeedbackEventData
    | TopicAtBotEvent
    | TopicEvent
    | UnknownEvent
)


@dataclass
class EventMessage:
    """事件回调消息结构"""

    msgid: str
    create_time: int
    aibotid: str
    from_: EventFrom
    msgtype: Literal["event"]
    event: EventContent
    chatid: str | None = None
    chattype: Literal["single", "group"] | None = None
    # 频道（话题）ID，位于事件回调 body 顶层
    topic_id: str | None = None
    compat_info: CompatInfo | None = None
    # 原始数据
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if not self._raw:
            self._raw = {}

    @property
    def is_channel(self) -> bool:
        """事件是否来自「频道」（chattype 可能缺失，需看 compat_info.source 或 topic_id）"""
        return is_channel_source(self.compat_info) or bool(self.topic_id)

    @property
    def topic_key(self) -> str | None:
        """标识所属话题的唯一键：优先 topic_id，回退 chatid

        实测 topic_at_bot 事件体只有 topic_id，与消息体的 chatid 前缀空间不同。
        """
        return self.topic_id or self.chatid
