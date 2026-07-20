"""
企业微信智能机器人 Python SDK - 多机器人示例

使用方法：
方式一：环境变量
  1. 复制 .env.example 为 .env
  2. 在 .env 中配置多个机器人（见下方说明）
  3. 运行: uv run python examples/example_multi_bot.py

方式二：JSON 配置文件
  1. 复制 bots_config.json.example 为 bots_config.json
  2. 填写机器人配置
  3. 运行: uv run python examples/example_multi_bot.py --config bots_config.json
"""

from __future__ import annotations

import argparse
import asyncio

from dotenv import load_dotenv

from wecom_aibot import BotManager
from wecom_aibot.types import (
    TemplateCard,
    TemplateCardMainTitle,
    WelcomeTextReplyBody,
)

load_dotenv()


def create_manager_from_env() -> BotManager:
    """从环境变量创建多机器人管理器"""
    manager = BotManager()
    count = manager.load_from_env()
    print(f"[启动] 从环境变量加载了 {count} 个机器人配置")
    return manager


def create_manager_from_json(config_path: str) -> BotManager:
    """从 JSON 配置文件创建多机器人管理器"""
    manager = BotManager()
    count = manager.load_from_json(config_path)
    print(f"[启动] 从 {config_path} 加载了 {count} 个机器人配置")
    return manager


def register_bot_handlers(manager: BotManager, bot_name: str) -> None:
    """为单个机器人注册事件处理器"""

    @manager.on(f"{bot_name}.authenticated")
    def on_authenticated() -> None:
        print(f"[{bot_name}] 认证成功 [OK]")

    @manager.on(f"{bot_name}.message.text")
    async def on_text_message(frame) -> None:
        content = frame.body.text.content
        user = frame.body.from_.userid
        print(f"[{bot_name}] 收到 {user} 的文本消息: {content}")

        client = manager.get_bot(bot_name)
        if not client:
            return

        stream_id = f"stream_{bot_name}_{frame.headers.get('req_id', '0')}"
        await client.reply_stream(frame, stream_id, "正在思考...", finish=False)
        await asyncio.sleep(0.5)
        await client.reply_stream(
            frame,
            stream_id,
            f"**[{bot_name}]** 收到您的消息：{content}",
            finish=True,
        )

    @manager.on(f"{bot_name}.message.image")
    async def on_image_message(frame) -> None:
        user = frame.body.from_.userid
        print(f"[{bot_name}] 收到 {user} 的图片消息")

        client = manager.get_bot(bot_name)
        if not client:
            return

        await client.reply_stream(frame, f"stream_img_{bot_name}", "收到图片！", finish=True)

    @manager.on(f"{bot_name}.event.enter_chat")
    async def on_enter_chat(frame) -> None:
        user = frame.body.from_.userid
        print(f"[{bot_name}] 用户 {user} 进入会话")

        client = manager.get_bot(bot_name)
        if not client:
            return

        welcome = WelcomeTextReplyBody.create(f"您好！我是 **{bot_name}**，有什么可以帮您的？")
        await client.reply_welcome(frame, welcome)

    @manager.on(f"{bot_name}.event.template_card_event")
    async def on_template_card_event(frame) -> None:
        event_key = frame.body.event.event_key
        print(f"[{bot_name}] 模板卡片事件: {event_key}")

        client = manager.get_bot(bot_name)
        if not client:
            return

        card = TemplateCard(
            card_type="text_notice",
            main_title=TemplateCardMainTitle(
                title="已处理",
                desc=f"[{bot_name}] 您的请求已处理完成",
            ),
            task_id=frame.body.event.task_id,
        )
        await client.update_template_card(frame, card)


async def main() -> None:
    parser = argparse.ArgumentParser(description="企业微信多机器人示例")
    parser.add_argument("--config", type=str, help="JSON 配置文件路径")
    args = parser.parse_args()

    if args.config:
        manager = create_manager_from_json(args.config)
    else:
        manager = create_manager_from_env()

    if manager.bot_count == 0:
        print("[错误] 没有找到任何机器人配置！")
        print("请参考以下方式配置：")
        print("  方式一：设置环境变量 WECOM_BOTS_COUNT=2, WECOM_BOT_1_BOT_ID=..., WECOM_BOT_1_BOT_SECRET=...")
        print("  方式二：使用 --config bots_config.json 指定配置文件")
        return

    @manager.on("bot.connected")
    def on_any_connected(name: str) -> None:
        print(f"[全局] 机器人已连接: {name}")

    @manager.on("bot.disconnected")
    def on_any_disconnected(name: str, reason: str) -> None:
        print(f"[全局] 机器人已断开: {name}, 原因: {reason}")

    @manager.on("bot.error")
    def on_any_error(name: str, error: Exception) -> None:
        print(f"[全局] 机器人错误: {name}, 错误: {error}")

    for bot_name in manager.bot_names:
        register_bot_handlers(manager, bot_name)

    print("[启动] 正在连接所有机器人...")
    manager.connect_all()

    await asyncio.sleep(2)
    manager.print_status()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n[停止] 正在断开所有机器人...")
        await manager.disconnect_all()
        manager.print_status()
        print("[再见] 所有机器人已断开")


if __name__ == "__main__":
    asyncio.run(main())
