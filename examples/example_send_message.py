"""
主动发送消息示例

企业微信智能机器人支持主动向指定会话推送消息，无需等待用户先发送消息。

使用方法：
1. 配置 .env（WECOM_BOT_ID / WECOM_BOT_SECRET）
2. 修改 TARGET_CHATID 为目标会话 ID（单聊填 userid，群聊填 chatid）
3. 运行: uv run python examples/example_send_message.py
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from wecom_aibot import WSClient, DefaultLogger
from wecom_aibot.types import (
    SendMarkdownMsgBody,
    SendTemplateCardMsgBody,
    TemplateCard,
    TemplateCardSource,
    TemplateCardMainTitle,
    TemplateCardEmphasisContent,
    TemplateCardAction,
    TemplateCardButton,
    WSClientOptions,
)

load_dotenv()

# 目标会话 ID（单聊填 userid，群聊填 chatid）
TARGET_CHATID = os.getenv("WECOM_TARGET_CHATID", "user123")


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
        )
    )

    auth_event = asyncio.Event()

    @client.on("authenticated")
    def on_authenticated() -> None:
        print("[OK] 认证成功")
        auth_event.set()

    @client.on("error")
    def on_error(error: Exception) -> None:
        print(f"[ERROR] {error}")

    print("[START] 正在连接...")
    client.connect()

    try:
        await asyncio.wait_for(auth_event.wait(), timeout=10)
    except asyncio.TimeoutError:
        print("[FAIL] 认证超时")
        await client.disconnect()
        return

    await asyncio.sleep(1)
    print(f"\n[SEND] 正在向 {TARGET_CHATID} 发送消息...\n")

    # 1. Markdown
    print("[1] 发送 Markdown 消息...")
    try:
        markdown_msg = SendMarkdownMsgBody.create(
            "## 主动推送消息\n\n"
            "这是一条**主动推送**的消息，无需用户先发送消息。\n\n"
            "- 支持 Markdown 格式\n"
            "- 可以发送给单聊或群聊\n"
            "- 适合定时推送、通知提醒等场景\n\n"
            "> Powered by wecom-aibot Python SDK"
        )
        result = await client.send_message(TARGET_CHATID, markdown_msg)
        print(f"   [OK] 发送成功: errcode={result.errcode}")
    except Exception as exc:
        print(f"   [FAIL] 发送失败: {exc}")

    await asyncio.sleep(1)

    # 2. 文本通知卡片
    print("\n[2] 发送模板卡片消息...")
    try:
        card = TemplateCard(
            card_type="text_notice",
            source=TemplateCardSource(desc="Python SDK", desc_color=1),
            main_title=TemplateCardMainTitle(
                title="系统通知",
                desc="这是一条模板卡片消息",
            ),
            emphasis_content=TemplateCardEmphasisContent(title="状态", desc="运行正常"),
            sub_title_text="wecom-aibot Python SDK",
            card_action=TemplateCardAction(type=1, url="https://github.com"),
        )
        result = await client.send_message(TARGET_CHATID, SendTemplateCardMsgBody(template_card=card))
        print(f"   [OK] 发送成功: errcode={result.errcode}")
    except Exception as exc:
        print(f"   [FAIL] 发送失败: {exc}")

    await asyncio.sleep(1)

    # 3. 交互按钮卡片
    print("\n[3] 发送交互按钮卡片...")
    try:
        interactive_card = TemplateCard(
            card_type="button_interaction",
            source=TemplateCardSource(desc="Python SDK", desc_color=1),
            main_title=TemplateCardMainTitle(
                title="任务确认",
                desc="请确认是否执行以下操作",
            ),
            task_id="task_001",
            button_list=[
                TemplateCardButton(text="确认执行", key="confirm", style=1),
                TemplateCardButton(text="取消", key="cancel", style=2),
            ],
        )
        result = await client.send_message(
            TARGET_CHATID,
            SendTemplateCardMsgBody(template_card=interactive_card),
        )
        print(f"   [OK] 发送成功: errcode={result.errcode}")
    except Exception as exc:
        print(f"   [FAIL] 发送失败: {exc}")

    print("\n[DONE] 所有消息发送完成")
    await client.disconnect()
    print("[BYE] 已断开连接")


if __name__ == "__main__":
    print("=" * 50)
    print("企业微信智能机器人 - 主动发送消息示例")
    print("=" * 50)
    print(f"\n目标会话 TARGET_CHATID / WECOM_TARGET_CHATID = {TARGET_CHATID}\n")
    asyncio.run(main())
