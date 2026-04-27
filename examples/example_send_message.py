"""
主动发送消息示例

企业微信智能机器人支持主动向指定会话推送消息，无需等待用户先发送消息。

使用方法：
1. 配置 .env 文件（复制 .env.example 并填写 bot_id 和 secret）
2. 修改 TARGET_CHATID 为目标会话 ID（单聊填 userid，群聊填 chatid）
3. 运行: uv run python example_send_message.py
"""

import asyncio
import os
from dotenv import load_dotenv
from wecom_aibot import WSClient, WSClientOptions, DefaultLogger
from wecom_aibot.types import (
    SendMarkdownMsgBody,
    SendTemplateCardMsgBody,
    TemplateCard,
    TemplateCardSource,
    TemplateCardMainTitle,
    TemplateCardEmphasisContent,
    TemplateCardAction,
    TemplateCardButton,
)

# 加载环境变量
load_dotenv()

# 目标会话 ID（单聊填 userid，群聊填 chatid）
# TODO: 修改为实际的目标会话 ID
TARGET_CHATID = "user123"  # 替换为实际的 userid 或 chatid


async def main():
    bot_id = os.getenv("WECOM_BOT_ID")
    secret = os.getenv("WECOM_BOT_SECRET")

    if not bot_id or not secret:
        print("[ERROR] 请在 .env 文件中配置 WECOM_BOT_ID 和 WECOM_BOT_SECRET")
        return

    # 创建客户端
    options = WSClientOptions(
        bot_id=bot_id,
        secret=secret,
        logger=DefaultLogger(),
    )

    client = WSClient(options)

    # 认证成功事件
    auth_event = asyncio.Event()

    @client.on("authenticated")
    def on_authenticated():
        print("[OK] 认证成功")
        auth_event.set()

    @client.on("error")
    def on_error(error: Exception):
        print(f"[ERROR] {error}")

    print("[START] 正在连接...")
    client.connect()

    # 等待认证
    try:
        await asyncio.wait_for(auth_event.wait(), timeout=10)
    except asyncio.TimeoutError:
        print("[FAIL] 认证超时")
        await client.disconnect()
        return

    # 等待一秒确保连接稳定
    await asyncio.sleep(1)

    print(f"\n[SEND] 正在向 {TARGET_CHATID} 发送消息...\n")

    # ========== 示例 1: 发送 Markdown 消息 ==========
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
    except Exception as e:
        print(f"   [FAIL] 发送失败: {e}")

    await asyncio.sleep(1)

    # ========== 示例 2: 发送模板卡片消息 ==========
    print("\n[2] 发送模板卡片消息...")
    try:
        card = TemplateCard(
            card_type="text_notice",
            source=TemplateCardSource(
                desc="Python SDK",
                desc_color=1,
            ),
            main_title=TemplateCardMainTitle(
                title="系统通知",
                desc="这是一条模板卡片消息",
            ),
            emphasis_content=TemplateCardEmphasisContent(
                title="状态",
                desc="运行正常",
            ),
            sub_title_text="wecom-aibot Python SDK",
            card_action=TemplateCardAction(
                type=1,
                url="https://github.com",
            ),
        )
        card_msg = SendTemplateCardMsgBody(template_card=card)
        result = await client.send_message(TARGET_CHATID, card_msg)
        print(f"   [OK] 发送成功: errcode={result.errcode}")
    except Exception as e:
        print(f"   [FAIL] 发送失败: {e}")

    await asyncio.sleep(1)

    # ========== 示例 3: 发送带按钮的交互卡片 ==========
    print("\n[3] 发送交互按钮卡片...")
    try:
        interactive_card = TemplateCard(
            card_type="button_interaction",
            source=TemplateCardSource(
                desc="Python SDK",
                desc_color=1,
            ),
            main_title=TemplateCardMainTitle(
                title="任务确认",
                desc="请确认是否执行以下操作",
            ),
            task_id="task_001",  # 用于后续更新卡片
            button_list=[
                TemplateCardButton(text="确认执行", key="confirm", style=1),
                TemplateCardButton(text="取消", key="cancel", style=2),
            ],
        )
        card_msg = SendTemplateCardMsgBody(template_card=interactive_card)
        result = await client.send_message(TARGET_CHATID, card_msg)
        print(f"   [OK] 发送成功: errcode={result.errcode}")
    except Exception as e:
        print(f"   [FAIL] 发送失败: {e}")

    print("\n[DONE] 所有消息发送完成")

    # 断开连接
    await client.disconnect()
    print("[BYE] 已断开连接")


if __name__ == "__main__":
    print("=" * 50)
    print("企业微信智能机器人 - 主动发送消息示例")
    print("=" * 50)
    print(f"\n注意: 请先修改 TARGET_CHATID 为实际的目标会话 ID\n")
    asyncio.run(main())
