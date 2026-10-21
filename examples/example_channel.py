"""
频道（话题）监听示例

对应能力：
- 频道消息识别：compat_info.source == "channel"（chattype 仍为 group）
- 触发策略：默认只回应正文以 @机器人 开头的频道消息（channel_trigger="mention"）
- topic_at_bot: 频道中 @机器人，携带 topic_id 与 post_id
- topic_event: 频道事件（平台未公开结构，原始数据在 event.data）
- 配对去重：同一次 @ 走「消息 + 事件」两条通路，只回答一次

注意：频道消息是**全量推送**的——话题里没有 @机器人 的普通消息同样会到达，
与「群聊只有被 @ 才推送」不同，示例中会打印 [SKIP] 而不回复。

使用方法：
1. 配置 .env
2. 在企业微信「频道/话题」中 @机器人（或发一条不带 @ 的消息观察 SKIP）
3. 运行: uv run python examples/example_channel.py
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from wecom_aibot import WSClient
from wecom_aibot.types import TopicAtBotEvent, TopicEvent, WSClientOptions

load_dotenv()


async def main() -> None:
    bot_id = os.getenv("WECOM_BOT_ID")
    secret = os.getenv("WECOM_BOT_SECRET")

    if not bot_id or not secret:
        print("[ERROR] 请在 .env 文件中配置 WECOM_BOT_ID 和 WECOM_BOT_SECRET")
        return

    client = WSClient(
        WSClientOptions(bot_id=bot_id, secret=secret, logger=None)
    )

    @client.on("authenticated")
    def on_auth() -> None:
        print("[READY] 已连接，请在频道中 @机器人")

    @client.on("event.topic_at_bot")
    async def on_topic_at_bot(frame) -> None:
        msg = frame.body
        if isinstance(msg.event, TopicAtBotEvent):
            print(f"[AT_BOT] 频道={msg.topic_id} 帖子={msg.event.post_id}")
            # 事件体没有正文也没有 chatid：tracker 会把它与被 @ 的那条频道消息配对，
            # 等待该消息到达后即可还原「用户说了什么」并回答（自动去重，不会重复回两次）
            paired = client.topic_tracker.pending_for(msg)
            if paired is not None:
                print(f"[AT_BOT] 配对到的消息: {paired.text.content}")

    @client.on("event.topic")
    def on_topic(frame) -> None:
        msg = frame.body
        print(f"[TOPIC] type={msg.event.eventtype} channel={msg.is_channel}")

    @client.on("event.topic_event")
    def on_topic_event(frame) -> None:
        msg = frame.body
        if isinstance(msg.event, TopicEvent):
            print(f"[TOPIC_EVENT] raw={msg.event.data}")

    @client.on("message.text")
    async def on_text(frame) -> None:
        msg = frame.body
        print(
            f"[TEXT] channel={msg.is_channel} chattype={msg.chattype} "
            f"mention={msg.is_mention} at={msg.at_list} content={msg.text.content}"
        )
        if not msg.is_channel:
            return

        # 触发策略：默认只回应被 @ 的频道消息
        if not client.should_reply(msg):
            print(f"[SKIP] 话题里的普通消息，未 @ 机器人: {msg.text.content}")
            return

        # reply_topic 内部做去重：同一次 @ 不会回答两次
        await client.reply_topic(frame, msg, "收到频道消息", finish=True)

    client.connect()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await client.disconnect()
        print("[BYE] 已断开连接")


if __name__ == "__main__":
    asyncio.run(main())
