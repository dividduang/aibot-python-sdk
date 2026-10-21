"""
频道（话题）全量触发示例

对应能力：
- channel_trigger="all"：回应话题内的每一条消息（不限于 @机器人）
- 与 examples/example_channel.py 的区别仅在触发策略配置

背景：实测企业微信对「频道」是**全量推送**的——话题里没有 @机器人 的普通消息
同样会到达（与「群聊只有被 @ 才推送」不同）。若沿用群的假设逐条回复就会刷屏，
因此 SDK 默认策略是 mention；确有「话题内每条都要回」的需求时再显式改为 all。

使用方法：
1. 配置 .env
2. 在企业微信「频道/话题」中发消息（带不带 @ 都会回复）
3. 运行: uv run python examples/example_topic_trigger.py
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from wecom_aibot import WSClient
from wecom_aibot.types import WSClientOptions

load_dotenv()


async def main() -> None:
    bot_id = os.getenv("WECOM_BOT_ID")
    secret = os.getenv("WECOM_BOT_SECRET")

    if not bot_id or not secret:
        print("[ERROR] 请在 .env 文件中配置 WECOM_BOT_ID 和 WECOM_BOT_SECRET")
        return

    client = WSClient(
        WSClientOptions(
            bot_id=bot_id,
            secret=secret,
            logger=None,
            # 回应话题内的每一条消息
            channel_trigger="all",
        )
    )

    @client.on("authenticated")
    def on_auth() -> None:
        print("[READY] 已连接（channel_trigger=all，话题内每条消息都会回复）")

    @client.on("message.text")
    async def on_text(frame) -> None:
        msg = frame.body
        if not msg.is_channel:
            return

        print(f"[TEXT] mention={msg.is_mention} content={msg.text.content}")
        await client.reply_topic(frame, msg, f"收到：{msg.text.content}", finish=True)

    client.connect()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await client.disconnect()
        print("[BYE] 已断开连接")


if __name__ == "__main__":
    asyncio.run(main())
