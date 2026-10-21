"""
频道（话题）解析测试

载荷取自 2026-10-14 实测长连接推送：
- 频道文本消息 compat_info.source = "channel"，chattype 仍为 group
- 频道 @机器人 事件 eventtype = "topic_at_bot"，topic_id 位于 body 顶层

2026-10-21 复核实测结论：
- 频道消息是全量推送的：话题里没有 @机器人 的普通消息同样会到达
  （与「群聊只有被 @ 才推送」不同），故 SDK 默认触发策略为 mention
- 频道消息体只有 chatid，topic_at_bot 事件体只有 topic_id，两者 id 空间不同
"""

from typing import Any

from wecom_aibot.message_handler import MessageHandler
from wecom_aibot.types import (
    CompatInfo,
    EventType,
    MessageSource,
    TopicAtBotEvent,
    TopicEvent,
    UnknownEvent,
    WsFrame,
)

CHANNEL_MSG_BODY: dict[str, Any] = {
    "msgid": "c16d6bcd3bc32a1f99f93182545c6beb",
    "aibotid": "aibZooVzynU_ykSAnc2KcA-8yn41CnfHIrs",
    "chatid": "opigAJEAAAWzyCngYUB6P-bVF7N1ptjg",
    "chattype": "group",
    "from": {"userid": "woigAJEAAAGaQL29QDqRfJazFgdpzXDA"},
    "msgtype": "text",
    "response_url": "https://qyapi.weixin.qq.com/cgi-bin/aibot/response?response_code=x",
    "text": {"content": "@邓景仁的机器人 hello"},
    "compat_info": {"source": "channel"},
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


def dispatch(body: dict[str, Any], cmd: str = "aibot_msg_callback") -> Recorder:
    emitter = Recorder()
    MessageHandler().handle_frame(WsFrame(cmd=cmd, headers={"req_id": "r1"}, body=body), emitter)  # type: ignore[arg-type]
    return emitter


class TestChannelMessage:
    """频道来源消息解析"""

    def test_text_message_from_channel(self):
        msg = dispatch(CHANNEL_MSG_BODY).bodies("message.text")[0]
        assert msg.text.content == "@邓景仁的机器人 hello"
        assert msg.chatid == "opigAJEAAAWzyCngYUB6P-bVF7N1ptjg"

    def test_channel_flag_from_compat_info(self):
        msg = dispatch(CHANNEL_MSG_BODY).bodies("message.text")[0]
        assert isinstance(msg.compat_info, CompatInfo)
        assert msg.compat_info.source == MessageSource.CHANNEL
        assert msg.compat_info._raw == {"source": "channel"}
        assert msg.is_channel is True

    def test_chattype_stays_group_for_channel(self):
        """频道消息复用群聊语义，不能靠 chattype 判定"""
        msg = dispatch(CHANNEL_MSG_BODY).bodies("message.text")[0]
        assert msg.chattype == "group"

    def test_group_message_is_not_channel(self):
        body = {**CHANNEL_MSG_BODY}
        body.pop("compat_info")
        msg = dispatch(body).bodies("message.text")[0]
        assert msg.compat_info is None
        assert msg.is_channel is False

    def test_malformed_compat_info_ignored(self):
        body = {**CHANNEL_MSG_BODY, "compat_info": "channel"}
        msg = dispatch(body).bodies("message.text")[0]
        assert msg.compat_info is None
        assert msg.is_channel is False

    def test_unknown_compat_source_not_channel(self):
        body = {**CHANNEL_MSG_BODY, "compat_info": {"source": "future_source"}}
        msg = dispatch(body).bodies("message.text")[0]
        assert msg.is_channel is False


class TestTopicAtBotEvent:
    """频道 @机器人 事件解析"""

    def test_event_type_and_post_id(self):
        msg = dispatch(TOPIC_AT_BOT_BODY, cmd="aibot_event_callback").bodies("event.topic_at_bot")[0]
        assert isinstance(msg.event, TopicAtBotEvent)
        assert msg.event.eventtype == EventType.TOPIC_AT_BOT
        assert msg.event.post_id == "CiDNHswKN6Jf6gOBA3zpNeNkcEspZhE2IBdBcVUgrdJYshAB"

    def test_topic_id_from_body_top_level(self):
        msg = dispatch(TOPIC_AT_BOT_BODY, cmd="aibot_event_callback").bodies("event.topic_at_bot")[0]
        assert msg.topic_id == "CiBPl9RgdxBW0+mcOGiVUgYcBjfbYncj9f9WVMqFtZ59HRAB"
        assert msg.is_channel is True

    def test_emits_generic_topic_event(self):
        emitter = dispatch(TOPIC_AT_BOT_BODY, cmd="aibot_event_callback")
        assert len(emitter.bodies("event.topic")) == 1
        assert len(emitter.bodies("event")) == 1

    def test_at_bot_without_post_id(self):
        body = {**TOPIC_AT_BOT_BODY, "event": {"eventtype": "topic_at_bot", "topic_at_bot": {}}}
        msg = dispatch(body, cmd="aibot_event_callback").bodies("event.topic_at_bot")[0]
        assert msg.event.post_id is None

    def test_at_bot_without_nested_object(self):
        body = {**TOPIC_AT_BOT_BODY, "event": {"eventtype": "topic_at_bot"}}
        msg = dispatch(body, cmd="aibot_event_callback").bodies("event.topic_at_bot")[0]
        assert msg.event.post_id is None


class TestTopicEvent:
    """频道事件解析（载荷取自实测推送）"""

    TOPIC_EVENT_BODY: dict[str, Any] = {
        **TOPIC_AT_BOT_BODY,
        "msgid": "0e353ee324f9f059a5236c46206a8084",
        "create_time": 1791958860,
        "event": {
            "eventtype": "topic_event",
            "topic_event": {"type": 1, "post_id": "CiA9HKOq9RH4YNXYDSEJg2pBhys0NdubSvfgsqQSMhiOVBAB"},
        },
    }

    def test_type_and_post_id(self):
        msg = dispatch(self.TOPIC_EVENT_BODY, cmd="aibot_event_callback").bodies("event.topic_event")[0]
        assert isinstance(msg.event, TopicEvent)
        assert msg.event.eventtype == EventType.TOPIC_EVENT
        assert msg.event.type == 1
        assert msg.event.post_id == "CiA9HKOq9RH4YNXYDSEJg2pBhys0NdubSvfgsqQSMhiOVBAB"

    def test_topic_id_shared_with_at_bot(self):
        msg = dispatch(self.TOPIC_EVENT_BODY, cmd="aibot_event_callback").bodies("event.topic_event")[0]
        assert msg.topic_id == TOPIC_AT_BOT_BODY["topic_id"]
        assert msg.is_channel is True

    def test_raw_payload_preserved(self):
        body = {**TOPIC_AT_BOT_BODY, "event": {"eventtype": "topic_event", "extra": {"k": "v"}}}
        emitter = dispatch(body, cmd="aibot_event_callback")
        msg = emitter.bodies("event.topic_event")[0]
        assert msg.event.data["extra"] == {"k": "v"}
        assert msg.event.type is None
        assert len(emitter.bodies("event.topic")) == 1

    def test_missing_nested_object(self):
        body = {**TOPIC_AT_BOT_BODY, "event": {"eventtype": "topic_event"}}
        msg = dispatch(body, cmd="aibot_event_callback").bodies("event.topic_event")[0]
        assert msg.event.type is None
        assert msg.event.post_id is None


class TestUnknownEvent:
    """未知事件不再被静默丢弃"""

    def test_unknown_event_keeps_raw_data(self):
        body = {**TOPIC_AT_BOT_BODY, "event": {"eventtype": "brand_new_event", "payload": [1, 2]}}
        msg = dispatch(body, cmd="aibot_event_callback").bodies("event")[0]
        assert isinstance(msg.event, UnknownEvent)
        assert msg.event.eventtype == "brand_new_event"
        assert msg.event.data["payload"] == [1, 2]

    def test_event_message_keeps_body(self):
        body = {**TOPIC_AT_BOT_BODY, "event": {"eventtype": "brand_new_event"}}
        msg = dispatch(body, cmd="aibot_event_callback").bodies("event")[0]
        assert msg._raw["msgid"] == TOPIC_AT_BOT_BODY["msgid"]

    def test_non_topic_unknown_event_not_emitted_as_topic(self):
        body = {**TOPIC_AT_BOT_BODY, "event": {"eventtype": "brand_new_event"}}
        emitter = dispatch(body, cmd="aibot_event_callback")
        assert emitter.bodies("event.topic") == []


class TestChannelMention:
    """正文里的 @提及解析（频道消息全量推送，需区分是否在呼叫机器人）"""

    def test_channel_message_with_mention(self):
        msg = dispatch(CHANNEL_MSG_BODY).bodies("message.text")[0]
        assert msg.is_mention is True
        assert msg.at_list == ["邓景仁的机器人"]

    def test_plain_topic_message_is_not_a_mention(self):
        body = {**CHANNEL_MSG_BODY, "text": {"content": "今天天气不错"}}
        msg = dispatch(body).bodies("message.text")[0]
        assert msg.is_mention is False
        assert msg.at_list == []

    def test_mention_not_at_start_is_not_a_mention(self):
        body = {**CHANNEL_MSG_BODY, "text": {"content": "你好 @邓景仁的机器人"}}
        msg = dispatch(body).bodies("message.text")[0]
        assert msg.is_mention is False
        assert msg.at_list == ["邓景仁的机器人"]

    def test_mixed_message_mentions_extracted(self):
        body = {
            **CHANNEL_MSG_BODY,
            "msgtype": "mixed",
            "text": None,
            "mixed": {
                "msg_item": [
                    {"msgtype": "text", "text": {"content": "@邓景仁的机器人 hi"}},
                ]
            },
        }
        body.pop("text")
        msg = dispatch(body).bodies("message.mixed")[0]
        assert msg.is_mention is True
        assert msg.at_list == ["邓景仁的机器人"]


class TestTopicKey:
    """话题标识：消息体只有 chatid，事件体只有 topic_id，id 空间不同"""

    def test_topic_key_falls_back_to_chatid(self):
        msg = dispatch(CHANNEL_MSG_BODY).bodies("message.text")[0]
        assert msg.topic_id is None
        assert msg.topic_key == "opigAJEAAAWzyCngYUB6P-bVF7N1ptjg"

    def test_event_topic_key_is_the_topic_id(self):
        msg = dispatch(TOPIC_AT_BOT_BODY, cmd="aibot_event_callback").bodies("event.topic_at_bot")[0]
        assert msg.topic_key == "CiBPl9RgdxBW0+mcOGiVUgYcBjfbYncj9f9WVMqFtZ59HRAB"

    def test_message_and_event_keys_are_not_interchangeable(self):
        """两个 id 前缀空间不同，不能当成同一个 key"""
        msg = dispatch(CHANNEL_MSG_BODY).bodies("message.text")[0]
        event = dispatch(TOPIC_AT_BOT_BODY, cmd="aibot_event_callback").bodies("event.topic_at_bot")[0]
        assert msg.topic_key != event.topic_key
