"""
频道（话题）消息与 @机器人 事件的配对 / 去重

背景（2026-10-21 实测）：
- 频道消息体只有 `chatid`，`topic_at_bot` 事件体只有 `topic_id`，两者 id 前缀空间不同；
- 事件体既没有正文也没有 `chatid`，无法直接还原「被 @ 时到底说了什么」；
- 同一次 @ 会带来「频道消息」和「topic_at_bot 事件」两条通路，两边各回一次会重复回答。

因此这里以「用户 + 时间窗」配对，以「消息身份」去重。
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any

from wecom_aibot.types.api import WsFrame
from wecom_aibot.types.event import EventMessage
from wecom_aibot.types.message import BaseMessage

# 归一化正文：去掉 @提及、压缩空白、忽略大小写
_AT_TOKEN = re.compile(r"@[^\s@]+")
_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str | None) -> str:
    """归一化正文，用于等价比较"""
    if not text:
        return ""
    return _WHITESPACE.sub(" ", _AT_TOKEN.sub(" ", text)).strip().lower()


def message_text(message: BaseMessage) -> str:
    """取消息正文（文本消息取 text.content，图文混排取首个文本项）"""
    text = getattr(message, "text", None)
    if text is not None and getattr(text, "content", None):
        return text.content

    mixed = getattr(message, "mixed", None)
    if mixed is not None:
        for item in getattr(mixed, "msg_item", None) or []:
            item_text = getattr(item, "text", None)
            if item_text is not None and getattr(item_text, "content", None):
                return item_text.content
    return ""


@dataclass
class _MessageEntry:
    """一条被追踪的频道消息"""

    message: BaseMessage
    frame: WsFrame | None = None
    userid: str = ""
    normalized: str = ""
    arrived_at: float = 0.0
    answered: bool = False
    # 平台已通过 topic_at_bot 事件确认这条消息是被 @ 的
    released: bool = False
    # 与之配对的 @机器人 事件
    event: Any = None


@dataclass
class _EventEntry:
    """一条被追踪的 topic_at_bot 事件"""

    event: EventMessage
    userid: str = ""
    arrived_at: float = 0.0
    # 与之配对的频道消息
    message: BaseMessage | None = None
    # 等待配对消息的等待者
    waiter: asyncio.Future | None = None


@dataclass
class TopicMentionTracker:
    """
    把频道消息与 topic_at_bot 事件对上，并避免同一次 @ 回答两次。

    - 配对键是「用户 + 时间窗」：事件与消息的 id 空间不同，无法按 id 关联；
    - 去重按消息身份（msgid）判定，辅以「用户 + 归一化正文」兜底，
      避免同一次 @ 以两条不同消息到达时重复回答。
    """

    # 配对时间窗（秒）
    window: float = 30.0
    # 追踪的最大消息 / 事件条数，超出后淘汰最旧的记录
    max_entries: int = 200
    _messages: list[_MessageEntry] = field(default_factory=list)
    _events: list[_EventEntry] = field(default_factory=list)
    # 已回答的（用户 + 归一化正文）及其时间，用于兜底去重
    _answered_texts: list[tuple[str, str, float]] = field(default_factory=list)

    # ── 记录 ──────────────────────────────────────────────

    def remember_message(self, message: BaseMessage, frame: WsFrame | None = None) -> BaseMessage | None:
        """记录一条频道消息

        Returns:
            若这条消息与此前收到的 @机器人 事件配上了，返回该消息，否则 None
        """
        entry = _MessageEntry(
            message=message,
            frame=frame,
            userid=message.from_.userid if message.from_ else "",
            normalized=normalize_text(message_text(message)),
            arrived_at=time.monotonic(),
        )
        self._messages.append(entry)
        self._evict()

        # 事件先到、消息后到的情况：用新到的消息去认领待配对事件
        for event_entry in self._claimable_events(entry):
            self._pair(event_entry, entry)
            return message
        return None

    def remember_event(self, event: EventMessage) -> BaseMessage | None:
        """记录一条 topic_at_bot 事件

        Returns:
            若事件与某条频道消息配上了，返回该消息，否则 None
        """
        entry = _EventEntry(
            event=event,
            userid=event.from_.userid if event.from_ else "",
            arrived_at=time.monotonic(),
        )
        self._events.append(entry)
        self._evict()

        # 消息先到、事件后到的情况：用事件去认领待配对消息
        candidate = self._pick_message(entry.userid, entry.arrived_at)
        if candidate is not None:
            self._pair(entry, candidate)
            return candidate.message
        return None

    # ── 查询 ──────────────────────────────────────────────

    def pending_for(self, event: EventMessage) -> BaseMessage | None:
        """取出与该 @机器人 事件配对的频道消息（尚未配对时返回 None）"""
        entry = self._find_event(event)
        if entry is None:
            return None
        return entry.message

    async def wait_for_message(self, event: EventMessage, timeout: float | None = None) -> BaseMessage | None:
        """等待与该 @机器人 事件配对的频道消息

        事件与消息的到达顺序不固定：事件先到时，这里会挂起直到对应消息到达。

        Args:
            event: topic_at_bot 事件
            timeout: 等待超时秒数，默认取 tracker 的 window

        Returns:
            配对到的频道消息；超时返回 None
        """
        entry = self._find_event(event)
        if entry is None:
            entry = _EventEntry(
                event=event,
                userid=event.from_.userid if event.from_ else "",
                arrived_at=time.monotonic(),
            )
            self._events.append(entry)
            self._evict()

        if entry.message is not None:
            return entry.message

        wait_timeout = self.window if timeout is None else timeout
        loop = asyncio.get_running_loop()
        if entry.waiter is None:
            entry.waiter = loop.create_future()

        try:
            return await asyncio.wait_for(asyncio.shield(entry.waiter), timeout=wait_timeout)
        except asyncio.TimeoutError:
            return None

    def already_answered(self, message: BaseMessage) -> bool:
        """该消息是否已经回答过（按消息身份判定）"""
        for entry in self._messages:
            if self._same_message(entry.message, message):
                return entry.answered
        return False

    def already_answered_similar(self, message: BaseMessage) -> bool:
        """该消息或同用户同正文的等价消息是否已经回答过

        事件与消息的 id 空间不同，同一次 @ 可能以两条不同消息到达，
        此时用「用户 + 归一化正文」兜底去重。

        文本兜底只作用于「被 @」相关的消息（正文以 @ 开头或已被事件确认），
        避免话题内重复的普通消息被误判为已回答。
        """
        if self.already_answered(message):
            return True
        if not (message.is_mention or self.is_released(message)):
            return False
        return self._answered_text_hit(message)

    def is_released(self, message: BaseMessage) -> bool:
        """平台是否已通过 topic_at_bot 事件确认该消息是被 @ 的"""
        for entry in self._messages:
            if self._same_message(entry.message, message):
                return entry.released
        return False

    def frame_for(self, message: BaseMessage) -> WsFrame | None:
        """取回该消息对应的回调帧（回复时需要透传 req_id）"""
        for entry in self._messages:
            if self._same_message(entry.message, message):
                return entry.frame
        return None

    # ── 状态变更 ──────────────────────────────────────────

    def mark_answered(self, message: BaseMessage) -> None:
        """标记该消息已回答"""
        for entry in self._messages:
            if self._same_message(entry.message, message):
                entry.answered = True
                break
        self._answered_texts.append(
            (
                message.from_.userid if message.from_ else "",
                normalize_text(message_text(message)),
                time.monotonic(),
            )
        )

    def unmark_answered(self, message: BaseMessage) -> None:
        """取消该消息的已回答标记（发送失败时回滚）"""
        for entry in self._messages:
            if self._same_message(entry.message, message):
                entry.answered = False
                break
        userid = message.from_.userid if message.from_ else ""
        normalized = normalize_text(message_text(message))
        for index in range(len(self._answered_texts) - 1, -1, -1):
            user, text, _ = self._answered_texts[index]
            if user == userid and text == normalized:
                del self._answered_texts[index]
                break

    def clear(self) -> None:
        """清空追踪记录"""
        for entry in self._events:
            if entry.waiter is not None and not entry.waiter.done():
                entry.waiter.cancel()
        self._messages.clear()
        self._events.clear()
        self._answered_texts.clear()

    # ── 内部实现 ──────────────────────────────────────────

    @staticmethod
    def _same_message(left: BaseMessage, right: BaseMessage) -> bool:
        if left is right:
            return True
        if left.msgid and right.msgid:
            return left.msgid == right.msgid
        return False

    def _answered_text_hit(self, message: BaseMessage) -> bool:
        """「用户 + 归一化正文」是否在时间窗内已回答过"""
        userid = message.from_.userid if message.from_ else ""
        normalized = normalize_text(message_text(message))
        if not normalized:
            return False
        now = time.monotonic()
        self._answered_texts = [item for item in self._answered_texts if now - item[2] <= self.window]
        return any(user == userid and text == normalized for user, text, _ in self._answered_texts)

    def _find_event(self, event: EventMessage) -> _EventEntry | None:
        for entry in reversed(self._events):
            if entry.event is event:
                return entry
            if entry.event.msgid and entry.event.msgid == event.msgid:
                return entry
        return None

    def _claimable_events(self, message_entry: _MessageEntry) -> list[_EventEntry]:
        """找出可以被这条消息认领的 @机器人 事件

        仅同用户、时间窗内、尚未配对的事件可被认领；
        同一用户短时间内连续发多条时，取最近的一条，避免张冠李戴。
        """
        now = message_entry.arrived_at
        candidates = [
            entry
            for entry in self._events
            if entry.message is None
            and entry.userid == message_entry.userid
            and now - entry.arrived_at <= self.window
        ]
        return candidates[:1]

    def _pick_message(self, userid: str, now: float) -> _MessageEntry | None:
        """挑一条可与 @机器人 事件配对的频道消息

        优先「正文以 @ 开头」的那条；没有时才回退到时间窗内最近的一条。
        """
        candidates = [
            entry
            for entry in self._messages
            if not entry.released
            and entry.userid == userid
            and now - entry.arrived_at <= self.window
        ]
        if not candidates:
            return None
        mentioned = [entry for entry in candidates if entry.message.is_mention]
        pool = mentioned or candidates
        return max(pool, key=lambda entry: entry.arrived_at)

    @staticmethod
    def _pair(event_entry: _EventEntry, message_entry: _MessageEntry) -> None:
        event_entry.message = message_entry.message
        message_entry.released = True
        message_entry.event = event_entry.event
        if event_entry.waiter is not None and not event_entry.waiter.done():
            event_entry.waiter.set_result(message_entry.message)

    def _evict(self) -> None:
        if len(self._messages) > self.max_entries:
            del self._messages[: len(self._messages) - self.max_entries]
        if len(self._events) > self.max_entries:
            del self._events[: len(self._events) - self.max_entries]
