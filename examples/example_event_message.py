"""
事件消息监听示例

对应能力：
- enter_chat: 用户进入会话
- template_card_event: 模板卡片交互
- feedback_event: 用户反馈

使用方法：
1. 配置 .env
2. 可选设置 WECOM_TARGET_CHATID，启动时向该会话发送测试交互卡片
3. 运行: uv run python examples/example_event_message.py
"""

from __future__ import annotations

import asyncio
import os
import time

from dotenv import load_dotenv

from wecom_aibot import WSClient, DefaultLogger
from wecom_aibot.types import (
    WelcomeTextReplyBody,
    TemplateCard,
    TemplateCardSource,
    TemplateCardMainTitle,
    TemplateCardAction,
    TemplateCardButton,
    SendTemplateCardMsgBody,
    WSClientOptions,
)

load_dotenv()

TARGET_CHATID = os.getenv("WECOM_TARGET_CHATID", "")


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
            logger=DefaultLogger(),
            heartbeat_interval=30000,
            max_reconnect_attempts=10,
        )
    )

    @client.on("connected")
    def on_connected() -> None:
        print("[EVENT] WebSocket 已连接")

    @client.on("disconnected")
    def on_disconnected(reason: str) -> None:
        print(f"[EVENT] 连接断开: {reason}")

    @client.on("reconnecting")
    def on_reconnecting(attempt: int) -> None:
        print(f"[EVENT] 正在重连，第 {attempt} 次")

    @client.on("error")
    def on_error(error: Exception) -> None:
        print(f"[EVENT] 发生错误: {error}")

    @client.on("event.enter_chat")
    async def on_enter_chat(frame) -> None:
        print("\n" + "=" * 50)
        print("[EVENT] enter_chat - 用户进入会话")
        print("=" * 50)
        print(f"  用户 ID: {frame.body.from_.userid}")
        print(f"  企业 ID: {frame.body.from_.corpid}")
        print(f"  会话类型: {frame.body.chattype}")
        print(f"  消息 ID: {frame.body.msgid}")

        try:
            welcome = WelcomeTextReplyBody.create(
                "您好！我是智能助手！\n\n"
                "我可以帮您：\n"
                "- 回答问题\n"
                "- 处理任务\n"
                "- 提供信息查询\n\n"
                "请随时向我提问！\n"
                "发送 `test` 可测试交互卡片。"
            )
            await client.reply_welcome(frame, welcome)
            print("  [OK] 欢迎语已发送")
        except Exception as exc:
            print(f"  [FAIL] 发送欢迎语失败: {exc}")

    @client.on("event.template_card_event")
    async def on_template_card_event(frame) -> None:
        print("\n" + "=" * 50)
        print("[EVENT] template_card_event - 模板卡片交互")
        print("=" * 50)
        print(f"  用户 ID: {frame.body.from_.userid}")
        print(f"  事件 Key: {frame.body.event.event_key}")
        print(f"  任务 ID: {frame.body.event.task_id}")
        print(f"  会话 ID: {frame.body.chatid}")

        event_key = frame.body.event.event_key
        task_id = frame.body.event.task_id

        try:
            if event_key == "confirm":
                title, desc = "[OK] Confirmed!", "Task started successfully"
            elif event_key == "cancel":
                title, desc = "[X] Cancelled", "Task cancelled"
            else:
                print(f"  [INFO] Unknown event_key: {event_key}")
                return

            updated_card = TemplateCard(
                card_type="text_notice",
                source=TemplateCardSource(desc="Event Test"),
                main_title=TemplateCardMainTitle(title=title, desc=desc),
                task_id=task_id,
                card_action=TemplateCardAction(type=1, url="https://work.weixin.qq.com"),
            )
            await client.update_template_card(frame, updated_card)
            print("  [OK] Card updated!")
        except Exception as exc:
            print(f"  [FAIL] Update failed: {exc}")

    @client.on("event.feedback_event")
    async def on_feedback_event(frame) -> None:
        print("\n" + "=" * 50)
        print("[EVENT] feedback_event - 用户反馈")
        print("=" * 50)
        print(f"  用户 ID: {frame.body.from_.userid}")
        print(f"  会话类型: {frame.body.chattype}")
        print(f"  消息 ID: {frame.body.msgid}")

    @client.on("message.text")
    async def on_text_message(frame) -> None:
        text_content = frame.body.text.content
        user_id = frame.body.from_.userid
        chat_type = frame.body.chattype
        chat_id = frame.body.chatid

        print(f"\n[MESSAGE] 收到文本消息: {text_content}")
        print(f"  用户 ID: {user_id}")
        print(f"  会话类型: {chat_type}")
        if chat_id:
            print(f"  群聊 ID: {chat_id}")

        if text_content.strip().lower() == "test":
            stream_id = f"stream_{int(time.time() * 1000)}"
            unique_task_id = f"task_{int(time.time() * 1000)}"
            interactive_card = TemplateCard(
                card_type="button_interaction",
                source=TemplateCardSource(desc="测试卡片", desc_color=1),
                main_title=TemplateCardMainTitle(
                    title="请选择操作",
                    desc="点击下方按钮进行测试",
                ),
                task_id=unique_task_id,
                button_list=[
                    TemplateCardButton(text="确认", key="confirm", style=1),
                    TemplateCardButton(text="取消", key="cancel", style=2),
                ],
            )
            await client.reply_stream_with_card(
                frame,
                stream_id,
                "这是一个测试卡片，请点击按钮：",
                finish=True,
                template_card=interactive_card,
            )
            print(f"  [OK] 已发送交互卡片，task_id={unique_task_id}")
        else:
            stream_id = f"stream_{int(time.time() * 1000)}"
            await client.reply_stream(
                frame,
                stream_id,
                f"收到您的消息：**{text_content}**\n\n发送 `test` 可以测试交互卡片功能。",
                finish=True,
            )

    print("=" * 50)
    print("企业微信智能机器人 - 事件消息监听示例")
    print("=" * 50)
    print("\n支持的事件类型：")
    print("  - enter_chat          - 用户进入会话")
    print("  - template_card_event - 模板卡片交互")
    print("  - feedback_event      - 用户反馈")
    print("\n测试方法：")
    print("  1. 配置 WECOM_TARGET_CHATID 时，启动后会向该会话发送测试卡片")
    print("  2. 点击卡片按钮触发 template_card_event")
    print("  3. 打开机器人单聊窗口触发 enter_chat")
    print("  4. 发送 test 也可触发交互卡片\n")

    auth_event = asyncio.Event()

    @client.on("authenticated")
    def on_authenticated() -> None:
        print("[EVENT] 认证成功")
        auth_event.set()

    print("[START] 正在连接...")
    client.connect()

    try:
        await asyncio.wait_for(auth_event.wait(), timeout=10)
        print("[OK] 认证成功！")
    except asyncio.TimeoutError:
        print("[FAIL] 认证超时")
        await client.disconnect()
        return

    await asyncio.sleep(1)

    if TARGET_CHATID:
        task_id = f"task_{int(time.time() * 1000)}"
        interactive_card = TemplateCard(
            card_type="button_interaction",
            source=TemplateCardSource(desc="Event Test", desc_color=1),
            main_title=TemplateCardMainTitle(
                title="Test Interactive Card",
                desc="Click a button to trigger template_card_event",
            ),
            task_id=task_id,
            button_list=[
                TemplateCardButton(text="Confirm", key="confirm", style=1),
                TemplateCardButton(text="Cancel", key="cancel", style=2),
            ],
        )
        print(f"\n[SEND] 发送交互卡片到: {TARGET_CHATID} (task_id={task_id})")
        try:
            result = await client.send_message(
                TARGET_CHATID,
                SendTemplateCardMsgBody(template_card=interactive_card),
            )
            if result.errcode == 0:
                print("       [OK] 卡片发送成功！")
            else:
                print(f"       [FAIL] 卡片发送失败: errcode={result.errcode}")
        except Exception as exc:
            print(f"       [FAIL] 发送异常: {exc}")
    else:
        print("\n[INFO] 未设置 WECOM_TARGET_CHATID，跳过启动时主动发卡片")

    print("\n[LISTEN] 正在监听事件... (Ctrl+C 退出)\n")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n[STOP] 正在断开...")
        await client.disconnect()
        print("[BYE] 已断开连接")


if __name__ == "__main__":
    asyncio.run(main())
