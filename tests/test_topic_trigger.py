"""
频道（话题）触发策略与消息/事件配对测试

覆盖频道触发策略与配对逻辑：
- 默认只回应被 @ 的频道消息（channel_trigger="mention"）
- channel_trigger="all" 时回应话题内的全部消息
- 频道消息与 topic_at_bot 事件能配上，同一次 @ 只回答一次
"""

from __future__ import annotations

from typing import Any

import pytest

from wecom_aibot import WSClient
from wecom_aibot.message_handler import MessageHandler
from wecom_aibot.topic_tracker import TopicMentionTracker
from wecom_aibot.types import (
    EventType,
    TopicAtBotEvent,
    WSClientOptions,
    WsFrame,
)

CHANNEL_MENTION_BODY: dict[str, Any] = {
    "msgid": "c16d6bcd3bc32a1f99f93182545c6beb",
    "aibotid": "aibZooVzynU_ykSAnc2KcA-8yn41CnfHIrs",
    "chatid": "opigAJEAAAWzyCngYUB6P-bVF7N1ptjg",
    "chattype": "group",
    "from": {"userid": "woigAJEAAAGaQL29QDqRfJazFgdpzXDA"},
    "msgtype": "text",
    "create_time": 1791957433,
    "text": {"content": "@邓景仁的机器人 hello"},
    "compat_info": {"source": "channel"},
}

CHANNEL_PLAIN_BODY: dict[str, Any] = {
    **CHANNEL_MENTION_BODY,
    "msgid": "plain0000000000000000000000000000000",
    "text": {"content": "今天天气不错"},
}

TOPIC_AT_BOT_BODY: dict[str, Any] = {
    "msgid": "51e76040fb5a4afe1967daf09995d54d",
    "aibotid": "aibZooVzynU_ykSAnc2KcA-8yn41CnfHIrs",
    "from": {"userid": "woigAJEAAAGaQL29QDqRfJazFgdpzXDA"},
    "msgtype": "event",
    "create_time": 1791957433,
    "event": {
        "eventtype": "topic_at_bot",
        "topic_at_bot": {"post_id": "CiDNHswKN6Jf6gOBA3zpNeNkcEspZhE2IBdBcVUgrdJYshAB"},
    },
    "topic_id": "CiBPl9RgdxBW0+mcOGiVUgYcBjfbYncj9f9WVMqFtZ59HRAB",
}


class Recorder:
    """记录 emit 的事件名与消息体（handler 统一以 WsFrame 发出）"""

    def __init__(self) -> None:
        self.emitted: list[tuple[str, Any]] = []

    def emit(self, event: str, frame: Any = None) -> None:
        self.emitted.append((event, frame.body if frame is not None else None))

    def bodies(self, event: str) -> list[Any]:
        return [body for name, body in self.emitted if name == event]


def make_client(tracker: TopicMentionTracker | None = None, **options: Any) -> WSClient:
    opts = WSClientOptions(bot_id="bot", secret="secret", **options)
    return WSClient(opts, tracker=tracker)


def dispatch(
    body: dict[str, Any],
    cmd: str = "aibot_msg_callback",
    tracker: TopicMentionTracker | None = None,
) -> Recorder:
    emitter = Recorder()
    handler = MessageHandler(tracker=tracker)
    handler.handle_frame(WsFrame(cmd=cmd, headers={"req_id": "r1"}, body=body), emitter)  # type: ignore[arg-type]
    return emitter


class TestChannelTriggerPolicy:
    """触发策略：默认只回应被 @ 的频道消息"""

    def test_mention_message_should_be_replied(self):
        client = make_client()
        msg = dispatch(CHANNEL_MENTION_BODY).bodies("message.text")[0]
        assert client.should_reply(msg) is True

    def test_plain_channel_message_should_not_be_replied(self):
        client = make_client()
        msg = dispatch(CHANNEL_PLAIN_BODY).bodies("message.text")[0]
        assert client.should_reply(msg) is False

    def test_all_trigger_replies_every_channel_message(self):
        client = make_client(channel_trigger="all")
        msg = dispatch(CHANNEL_PLAIN_BODY).bodies("message.text")[0]
        assert client.should_reply(msg) is True

    def test_non_channel_message_unaffected_by_policy(self):
        client = make_client()
        body = {**CHANNEL_PLAIN_BODY}
        body.pop("compat_info")
        msg = dispatch(body).bodies("message.text")[0]
        assert client.should_reply(msg) is True

    def test_default_trigger_is_mention(self):
        assert make_client().options.channel_trigger == "mention"


class TestTopicMentionTracker:
    """频道消息与 topic_at_bot 事件的配对"""

    def test_message_then_event_pairs(self):
        tracker = TopicMentionTracker()
        dispatch(CHANNEL_MENTION_BODY, tracker=tracker)
        emitter = dispatch(TOPIC_AT_BOT_BODY, cmd="aibot_event_callback", tracker=tracker)
        event = emitter.bodies("event.topic_at_bot")[0]
        assert isinstance(event.event, TopicAtBotEvent)
        paired = tracker.pending_for(event)
        assert paired is not None
        assert paired.text.content == "@邓景仁的机器人 hello"

    def test_event_then_message_pairs(self):
        tracker = TopicMentionTracker()
        emitter = dispatch(TOPIC_AT_BOT_BODY, cmd="aibot_event_callback", tracker=tracker)
        event = emitter.bodies("event.topic_at_bot")[0]
        dispatch(CHANNEL_MENTION_BODY, tracker=tracker)
        paired = tracker.pending_for(event)
        assert paired is not None
        assert paired.text.content == "@邓景仁的机器人 hello"

    def test_event_releases_the_channel_message(self):
        """平台确认被 @ 后，该消息不再受 mention 策略限制"""
        tracker = TopicMentionTracker()
        plain = dispatch(CHANNEL_PLAIN_BODY, tracker=tracker).bodies("message.text")[0]
        assert tracker.is_released(plain) is False
        dispatch(TOPIC_AT_BOT_BODY, cmd="aibot_event_callback", tracker=tracker)
        assert tracker.is_released(plain) is True

    def test_different_user_not_paired(self):
        tracker = TopicMentionTracker()
        dispatch(CHANNEL_MENTION_BODY, tracker=tracker)
        other = {**TOPIC_AT_BOT_BODY, "from": {"userid": "someone-else"}}
        emitter = dispatch(other, cmd="aibot_event_callback", tracker=tracker)
        event = emitter.bodies("event.topic_at_bot")[0]
        assert tracker.pending_for(event) is None

    def test_answered_message_is_not_answered_twice(self):
        tracker = TopicMentionTracker()
        msg = dispatch(CHANNEL_MENTION_BODY, tracker=tracker).bodies("message.text")[0]
        assert tracker.already_answered(msg) is False
        tracker.mark_answered(msg)
        assert tracker.already_answered(msg) is True

    def test_similar_message_answered_via_text_key(self):
        """同一次 @ 以两条不同消息到达时，按「用户 + 归一化正文」兜底去重"""
        tracker = TopicMentionTracker()
        msg = dispatch(CHANNEL_MENTION_BODY, tracker=tracker).bodies("message.text")[0]
        tracker.mark_answered(msg)
        duplicate = dispatch(
            {**CHANNEL_MENTION_BODY, "msgid": "other-msgid-0000000000000000000000000"},
            tracker=tracker,
        ).bodies("message.text")[0]
        assert tracker.already_answered(duplicate) is False
        assert tracker.already_answered_similar(duplicate) is True

    def test_frame_is_kept_for_replying(self):
        tracker = TopicMentionTracker()
        msg = dispatch(CHANNEL_MENTION_BODY, tracker=tracker).bodies("message.text")[0]
        frame = tracker.frame_for(msg)
        assert frame is not None
        assert frame.headers.get("req_id") == "r1"

    @pytest.mark.asyncio
    async def test_wait_for_message_resolves_when_message_arrives_later(self):
        tracker = TopicMentionTracker()
        emitter = dispatch(TOPIC_AT_BOT_BODY, cmd="aibot_event_callback", tracker=tracker)
        event = emitter.bodies("event.topic_at_bot")[0]

        import asyncio

        async def deliver():
            await asyncio.sleep(0.01)
            dispatch(CHANNEL_MENTION_BODY, tracker=tracker)

        task = asyncio.create_task(deliver())
        paired = await tracker.wait_for_message(event, timeout=2.0)
        await task
        assert paired is not None
        assert paired.text.content == "@邓景仁的机器人 hello"


class TestReplyTopic:
    """reply_topic：按策略回应，且同一次 @ 只回应一次"""

    @pytest.mark.asyncio
    async def test_plain_channel_message_is_skipped(self, monkeypatch):
        client = make_client()
        sent: list[Any] = []

        async def fake_reply_stream(frame, stream_id, content, finish=False, **kwargs):
            sent.append((frame, content))
            return WsFrame(headers={}, cmd="aibot_respond_msg", body={})

        monkeypatch.setattr(client, "reply_stream", fake_reply_stream)
        msg = dispatch(CHANNEL_PLAIN_BODY).bodies("message.text")[0]
        result = await client.reply_topic(None, msg, "收到")
        assert result is None
        assert sent == []

    @pytest.mark.asyncio
    async def test_mention_message_is_replied_once(self, monkeypatch):
        tracker = TopicMentionTracker()
        client = make_client(tracker=tracker)
        sent: list[Any] = []

        async def fake_reply_stream(frame, stream_id, content, finish=False, **kwargs):
            sent.append((frame, content))
            return WsFrame(headers={}, cmd="aibot_respond_msg", body={})

        monkeypatch.setattr(client, "reply_stream", fake_reply_stream)

        msg = dispatch(CHANNEL_MENTION_BODY, tracker=tracker).bodies("message.text")[0]
        first = await client.reply_topic(None, msg, "收到")
        second = await client.reply_topic(None, msg, "收到")
        assert first is not None
        assert second is None
        assert len(sent) == 1

    @pytest.mark.asyncio
    async def test_message_and_event_paths_reply_only_once(self, monkeypatch):
        """同一次 @ 走「消息 + 事件」两条通路，只应回答一次"""
        tracker = TopicMentionTracker()
        client = make_client(tracker=tracker)
        sent: list[Any] = []

        async def fake_reply_stream(frame, stream_id, content, finish=False, **kwargs):
            sent.append((frame, content))
            return WsFrame(headers={}, cmd="aibot_respond_msg", body={})

        monkeypatch.setattr(client, "reply_stream", fake_reply_stream)

        msg = dispatch(CHANNEL_MENTION_BODY, tracker=tracker).bodies("message.text")[0]
        await client.reply_topic(None, msg, "收到")

        emitter = dispatch(TOPIC_AT_BOT_BODY, cmd="aibot_event_callback", tracker=tracker)
        event = emitter.bodies("event.topic_at_bot")[0]
        result = await client.reply_topic_at_bot(event, "收到")

        assert result is None
        assert len(sent) == 1

    @pytest.mark.asyncio
    async def test_event_path_replies_when_message_not_answered_yet(self, monkeypatch):
        tracker = TopicMentionTracker()
        client = make_client(tracker=tracker)
        sent: list[Any] = []

        async def fake_reply_stream(frame, stream_id, content, finish=False, **kwargs):
            sent.append((frame, content))
            return WsFrame(headers={}, cmd="aibot_respond_msg", body={})

        monkeypatch.setattr(client, "reply_stream", fake_reply_stream)

        dispatch(CHANNEL_MENTION_BODY, tracker=tracker)
        emitter = dispatch(TOPIC_AT_BOT_BODY, cmd="aibot_event_callback", tracker=tracker)
        event = emitter.bodies("event.topic_at_bot")[0]
        result = await client.reply_topic_at_bot(event, "收到")

        assert result is not None
        assert len(sent) == 1
