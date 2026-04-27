"""
事件消息监听示例

企业微信智能机器人 SDK 支持自动监听以下事件类型：
- enter_chat: 用户进入会话事件
- template_card_event: 模板卡片交互事件
- feedback_event: 用户反馈事件

使用方法：
1. 配置 .env 文件（复制 .env.example 并填写 bot_id 和 secret）
2. 运行: uv run python example_eventmessage.py
3. 在企业微信中与机器人互动触发各种事件

事件触发条件说明：
========================

1. enter_chat (进入会话事件)
   - 触发条件: 用户在单聊窗口点击机器人头像进入会话
   - 触发时机: 用户首次打开与机器人的聊天窗口
   - 典型用途: 发送欢迎语、显示使用指南
   - 注意事项:
     * 需在 5 秒内调用 reply_welcome() 发送欢迎语
     * 群聊不会触发此事件

2. template_card_event (模板卡片交互事件)
   - 触发条件: 用户点击模板卡片上的按钮
   - 触发时机: 用户点击 button_interaction 类型卡片的按钮
   - 典型用途: 处理用户选择、更新卡片状态
   - 事件数据:
     * event_key: 按钮的 key（在发送卡片时定义）
     * task_id: 卡片的任务 ID（用于更新卡片）
   - 注意事项:
     * 需在 5 秒内调用 update_template_card() 更新卡片
     * 可通过 task_id 追踪具体的交互流程

3. feedback_event (用户反馈事件)
   - 触发条件: 用户对机器人回复进行点赞/点踩
   - 触发时机: 用户点击消息下方的反馈按钮
   - 典型用途: 收集用户满意度、改进机器人回复质量
   - 注意事项:
     * 需在发送消息时设置 feedback.id 才能收到反馈
     * feedback.id 用于关联原始消息

消息类型监听：
========================

SDK 同时支持监听各类消息：
- message: 所有消息（通用）
- message.text: 文本消息
- message.image: 图片消息
- message.mixed: 图文混排消息
- message.voice: 语音消息
- message.file: 文件消息

连接状态监听：
========================

- connected: WebSocket 连接成功
- authenticated: 认证成功
- disconnected: 连接断开
- reconnecting: 正在重连
- error: 发生错误
"""

import asyncio
import os
import time
from dotenv import load_dotenv
from wecom_aibot import WSClient, WSClientOptions, DefaultLogger
from wecom_aibot.types import (
    # 消息回复类型
    StreamReplyBody,
    WelcomeTextReplyBody,
    WelcomeTemplateCardReplyBody,
    # 模板卡片相关
    TemplateCard,
    TemplateCardSource,
    TemplateCardMainTitle,
    TemplateCardAction,
    TemplateCardButton,
    # 主动发送消息
    SendTemplateCardMsgBody,
)

# 加载环境变量
load_dotenv()

# 目标群聊 ID（用于启动时发送测试卡片）
TARGET_CHATID = "wrigAJEAAAm8vuxbYMQ1Bviptxh62_2A"


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
        heartbeat_interval=30000,
        max_reconnect_attempts=10,
    )

    client = WSClient(options)

    # ============================================================
    # 连接状态事件
    # ============================================================

    @client.on("connected")
    def on_connected():
        print("[EVENT] WebSocket 已连接")

    @client.on("authenticated")
    def on_authenticated():
        print("[EVENT] 认证成功，开始监听事件...")

    @client.on("disconnected")
    def on_disconnected(reason: str):
        print(f"[EVENT] 连接断开: {reason}")

    @client.on("reconnecting")
    def on_reconnecting(attempt: int):
        print(f"[EVENT] 正在重连，第 {attempt} 次")

    @client.on("error")
    def on_error(error: Exception):
        print(f"[EVENT] 发生错误: {error}")

    # ============================================================
    # 事件回调 - enter_chat (进入会话)
    # ============================================================

    @client.on("event.enter_chat")
    async def on_enter_chat(frame):
        """
        用户进入会话事件

        触发条件: 用户在单聊窗口点击机器人头像进入会话
        处理时限: 需在 5 秒内调用 reply_welcome()
        """
        print("\n" + "=" * 50)
        print("[EVENT] enter_chat - 用户进入会话")
        print("=" * 50)
        print(f"  用户 ID: {frame.body.from_.userid}")
        print(f"  企业 ID: {frame.body.from_.corpid}")
        print(f"  会话类型: {frame.body.chattype}")
        print(f"  消息 ID: {frame.body.msgid}")

        # 发送欢迎语（需在 5 秒内）
        try:
            # 方式1: 发送文本欢迎语
            welcome = WelcomeTextReplyBody.create(
                "您好！我是智能助手！\n\n"
                "我可以帮您：\n"
                "- 回答问题\n"
                "- 处理任务\n"
                "- 提供信息查询\n\n"
                "请随时向我提问！"
            )
            await client.reply_welcome(frame, welcome)
            print("  [OK] 欢迎语已发送")

            # 方式2: 发送模板卡片欢迎语（可选）
            # card = TemplateCard(
            #     card_type="text_notice",
            #     main_title=TemplateCardMainTitle(
            #         title="欢迎使用智能助手",
            #         desc="有什么可以帮您的？",
            #     ),
            # )
            # welcome_card = WelcomeTemplateCardReplyBody(template_card=card)
            # await client.reply_welcome(frame, welcome_card)

        except Exception as e:
            print(f"  [FAIL] 发送欢迎语失败: {e}")

    # ============================================================
    # 事件回调 - template_card_event (模板卡片交互)
    # ============================================================

    @client.on("event.template_card_event")
    async def on_template_card_event(frame):
        """
        模板卡片交互事件

        触发条件: 用户点击模板卡片上的按钮
        处理时限: 需在 5 秒内调用 update_template_card()
        事件数据:
          - event_key: 按钮的 key（发送卡片时定义）
          - task_id: 卡片的任务 ID
        """
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
            # 根据 event_key 处理不同的按钮点击
            # 注意: 更新卡片时 card_action.type=1 需要提供 url
            if event_key == "confirm":
                updated_card = TemplateCard(
                    card_type="text_notice",
                    source=TemplateCardSource(desc="Event Test"),
                    main_title=TemplateCardMainTitle(
                        title="[OK] Confirmed!",
                        desc="Task started successfully",
                    ),
                    task_id=task_id,
                    card_action=TemplateCardAction(
                        type=1,
                        url="https://work.weixin.qq.com",
                    ),
                )
                await client.update_template_card(frame, updated_card)
                print("  [OK] Card updated!")

            elif event_key == "cancel":
                updated_card = TemplateCard(
                    card_type="text_notice",
                    source=TemplateCardSource(desc="Event Test"),
                    main_title=TemplateCardMainTitle(
                        title="[X] Cancelled",
                        desc="Task cancelled",
                    ),
                    task_id=task_id,
                    card_action=TemplateCardAction(
                        type=1,
                        url="https://work.weixin.qq.com",
                    ),
                )
                await client.update_template_card(frame, updated_card)
                print("  [OK] Card updated!")

            else:
                print(f"  [INFO] Unknown event_key: {event_key}")

        except Exception as e:
            print(f"  [FAIL] Update failed: {e}")

    # ============================================================
    # 事件回调 - feedback_event (用户反馈)
    # ============================================================

    @client.on("event.feedback_event")
    async def on_feedback_event(frame):
        """
        用户反馈事件

        触发条件: 用户对机器人回复进行点赞/点踩
        前置条件: 发送消息时需设置 feedback.id
        """
        print("\n" + "=" * 50)
        print("[EVENT] feedback_event - 用户反馈")
        print("=" * 50)
        print(f"  用户 ID: {frame.body.from_.userid}")
        print(f"  会话类型: {frame.body.chattype}")
        print(f"  消息 ID: {frame.body.msgid}")
        print("  [INFO] 用户对机器人回复进行了反馈")

        # 这里可以记录用户反馈到数据库
        # 用于改进机器人的回复质量

    # ============================================================
    # 消息回调 - 演示如何触发卡片交互
    # ============================================================

    @client.on("message.text")
    async def on_text_message(frame):
        """
        文本消息回调

        这里演示如何发送一个带按钮的模板卡片，
        用户点击按钮后会触发 template_card_event
        """
        text_content = frame.body.text.content
        user_id = frame.body.from_.userid
        chat_type = frame.body.chattype
        chat_id = frame.body.chatid

        print(f"\n[MESSAGE] 收到文本消息: {text_content}")
        print(f"  用户 ID: {user_id}")
        print(f"  会话类型: {chat_type}")
        if chat_id:
            print(f"  群聊 ID: {chat_id}")

        # 如果用户发送 "test"，发送一个交互卡片用于测试
        if text_content.strip().lower() == "test":
            stream_id = f"stream_{int(time.time() * 1000)}"
            unique_task_id = f"task_{int(time.time() * 1000)}"

            # 创建带按钮的交互卡片
            interactive_card = TemplateCard(
                card_type="button_interaction",
                source=TemplateCardSource(
                    desc="测试卡片",
                    desc_color=1,
                ),
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

            # 发送流式消息 + 模板卡片
            await client.reply_stream_with_card(
                frame,
                stream_id,
                "这是一个测试卡片，请点击按钮：",
                finish=True,
                template_card=interactive_card,
            )
            print(f"  [OK] 已发送交互卡片，task_id={unique_task_id}")

        else:
            # 普通回复
            stream_id = f"stream_{int(time.time() * 1000)}"
            await client.reply_stream(
                frame,
                stream_id,
                f"收到您的消息：**{text_content}**\n\n发送 `test` 可以测试交互卡片功能。",
                finish=True,
            )

    # ============================================================
    # 通用事件监听（可选）
    # ============================================================

    @client.on("event")
    def on_any_event(frame):
        """监听所有事件（调试用）"""
        print(f"\n[DEBUG] 收到事件: {frame.body.event.eventtype if hasattr(frame.body, 'event') else 'unknown'}")

    @client.on("message")
    def on_any_message(frame):
        """监听所有消息（调试用）"""
        pass  # 已经在 message.text 中处理

    # ============================================================
    # 启动连接
    # ============================================================

    print("=" * 50)
    print("企业微信智能机器人 - 事件消息监听示例")
    print("=" * 50)
    print("\n支持的事件类型：")
    print("  - enter_chat        - 用户进入会话")
    print("  - template_card_event - 模板卡片交互")
    print("  - feedback_event    - 用户反馈")
    print("\n测试方法：")
    print("  1. 启动后会自动向群里发送测试卡片")
    print("  2. 在群里点击卡片按钮（触发 template_card_event）")
    print("  3. 在企业微信中打开机器人聊天窗口（触发 enter_chat）")
    print("\n[START] 正在连接...\n")

    # 认证成功事件
    auth_event = asyncio.Event()

    @client.on("authenticated")
    def on_authenticated():
        auth_event.set()

    client.connect()

    # 等待认证成功
    try:
        await asyncio.wait_for(auth_event.wait(), timeout=10)
        print("[OK] 认证成功！")
    except asyncio.TimeoutError:
        print("[FAIL] 认证超时")
        await client.disconnect()
        return

    # 等待连接稳定
    await asyncio.sleep(1)

    # ============================================================
    # 启动时自动发送交互卡片到群聊
    # ============================================================
    task_id = f"task_{int(time.time() * 1000)}"

    interactive_card = TemplateCard(
        card_type="button_interaction",
        source=TemplateCardSource(
            desc="Event Test",
            desc_color=1,
        ),
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

    card_msg = SendTemplateCardMsgBody(template_card=interactive_card)

    print(f"\n[SEND] 正在发送交互卡片到群聊...")
    print(f"       Chat ID: {TARGET_CHATID}")
    print(f"       Task ID: {task_id}")

    try:
        result = await client.send_message(TARGET_CHATID, card_msg)
        if result.errcode == 0:
            print(f"       [OK] 卡片发送成功！")
        else:
            print(f"       [FAIL] 卡片发送失败: errcode={result.errcode}")
    except Exception as e:
        print(f"       [FAIL] 发送异常: {e}")

    print("\n[LISTEN] 正在监听事件...")
    print("         请在群里点击卡片按钮测试！\n")

    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n[STOP] 正在断开...")
        await client.disconnect()
        print("[BYE] 已断开连接")


if __name__ == "__main__":
    asyncio.run(main())
