"""
频道（话题）监听示例

对应能力：
- 频道消息识别：compat_info.source == "channel"（chattype 仍为 group）
- topic_at_bot: 频道中 @机器人，携带 topic_id 与 post_id
- topic_event: 频道事件（平台未公开结构，原始数据在 event.data）

使用方法：
1. 配置 .env
2. 在企业微信「频道/话题」中 @机器人
3. 运行: uv run python examples/example_channel.py
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from wecom_aibot import WSClient, generate_req_id
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
    def on_topic_at_bot(frame) -> None:
        msg = frame.body
        if isinstance(msg.event, TopicAtBotEvent):
            print(f"[AT_BOT] 频道={msg.topic_id} 帖子={msg.event.post_id}")

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
        print(f"[TEXT] channel={msg.is_channel} chattype={msg.chattype} content={msg.text.content}")
        if msg.is_channel:
            await client.reply_stream(
                frame, generate_req_id("stream"), "收到频道消息", finish=True
            )

    client.connect()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await client.disconnect()
        print("[BYE] 已断开连接")


if __name__ == "__main__":
    asyncio.run(main())
