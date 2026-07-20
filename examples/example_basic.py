"""
企业微信智能机器人 Python SDK - 基本使用示例

对应 Node SDK: examples/basic.ts

覆盖能力：
- 连接 / 认证 / 断线重连事件
- 文本消息流式回复
- 图片 / 文件下载解密
- 图文混排、语音、视频消息
- 进入会话欢迎语
- 模板卡片 / 用户反馈事件

使用方法：
1. 复制 .env.example 为 .env，填写 WECOM_BOT_ID / WECOM_BOT_SECRET
2. 安装依赖: uv sync --extra dev
3. 运行: uv run python examples/example_basic.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from wecom_aibot import WSClient, generate_req_id
from wecom_aibot.types import (
    TemplateCard,
    TemplateCardMainTitle,
    TemplateCardSource,
    TemplateCardSubmitButton,
    TemplateCardSelectionItem,
    WelcomeTextReplyBody,
    WSClientOptions,
)

load_dotenv()

# 示例用交互卡片（多项选择）
TEMPLATE_CARD = TemplateCard(
    card_type="multiple_interaction",
    source=TemplateCardSource(
        icon_url="https://wework.qpic.cn/wwpic/252813_jOfDHtcISzuodLa_1629280209/0",
        desc="企业微信",
    ),
    main_title=TemplateCardMainTitle(
        title="欢迎使用企业微信",
        desc="您的好友正在邀请您加入企业微信",
    ),
    select_list=[
        TemplateCardSelectionItem(
            question_key="question_key_one",
            title="选择标签1",
            selected_id="id_one",
            option_list=[
                {"id": "id_one", "text": "选择器选项1"},
                {"id": "id_two", "text": "选择器选项2"},
            ],
        ),
        TemplateCardSelectionItem(
            question_key="question_key_two",
            title="选择标签2",
            selected_id="id_three",
            option_list=[
                {"id": "id_three", "text": "选择器选项3"},
                {"id": "id_four", "text": "选择器选项4"},
            ],
        ),
    ],
    submit_button=TemplateCardSubmitButton(text="提交", key="submit_key"),
    task_id=f"task_id_{generate_req_id('task')}",
)

DOWNLOAD_DIR = Path(__file__).resolve().parent / "downloads"


def get_config() -> tuple[str, str]:
    bot_id = os.getenv("WECOM_BOT_ID")
    secret = os.getenv("WECOM_BOT_SECRET")
    if not bot_id or not secret:
        raise ValueError("请在 .env 文件中设置 WECOM_BOT_ID 和 WECOM_BOT_SECRET")
    return bot_id, secret


async def save_downloaded(buffer: bytes, filename: str | None, fallback_prefix: str) -> Path:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = filename or f"{fallback_prefix}_{generate_req_id('file')}"
    path = DOWNLOAD_DIR / name
    path.write_bytes(buffer)
    return path


async def main() -> None:
    bot_id, secret = get_config()

    client = WSClient(
        WSClientOptions(
            bot_id=bot_id,
            secret=secret,
            heartbeat_interval=30000,
            max_reconnect_attempts=10,
        )
    )

    # ── 连接事件 ──────────────────────────────────────────

    @client.on("connected")
    def on_connected() -> None:
        print("[OK] WebSocket 已连接")

    @client.on("authenticated")
    def on_authenticated() -> None:
        print("[OK] 认证成功")

    @client.on("disconnected")
    def on_disconnected(reason: str) -> None:
        print(f"[DISCONNECTED] 连接断开: {reason}")

    @client.on("reconnecting")
    def on_reconnecting(attempt: int) -> None:
        print(f"[RECONNECT] 正在进行第 {attempt} 次重连...")

    @client.on("error")
    def on_error(error: Exception) -> None:
        print(f"[ERROR] 发生错误: {error}")

    # ── 所有消息（调试） ──────────────────────────────────

    @client.on("message")
    def on_message(frame) -> None:
        body = frame.body
        preview = str(getattr(body, "_raw", body))[:200]
        print(f"[MSG] 收到消息: {preview}")

    # ── 文本消息 + 流式回复 ───────────────────────────────

    @client.on("message.text")
    async def on_text_message(frame) -> None:
        content = frame.body.text.content
        print(f"[TEXT] 收到文本消息: {content}")

        stream_id = generate_req_id("stream")

        # 流式中间内容
        await client.reply_stream(frame, stream_id, "正在处理您的请求...", finish=False)
        await asyncio.sleep(1)
        # 最终结果
        await client.reply_stream(
            frame,
            stream_id,
            f"你好！你说的是: **{content}**",
            finish=True,
        )

        # 可选：模板卡片 / 流式+卡片 / 主动推送
        # await client.reply_template_card(frame, TEMPLATE_CARD)
        # await client.reply_stream_with_card(
        #     frame, stream_id, "hi", finish=False, template_card=TEMPLATE_CARD
        # )
        # from wecom_aibot.types import SendMarkdownMsgBody
        # await client.send_message(
        #     frame.body.from_.userid,
        #     SendMarkdownMsgBody.create("这是一条**主动推送**的消息"),
        # )

    # ── 图片消息：下载并解密 ──────────────────────────────

    @client.on("message.image")
    async def on_image_message(frame) -> None:
        image = frame.body.image
        print(f"[IMAGE] 收到图片消息: {image.url}")
        if not image.url:
            return
        try:
            buffer, filename = await client.download_file(image.url, image.aeskey)
            path = await save_downloaded(buffer, filename, "image")
            print(f"[IMAGE] 下载成功，大小: {len(buffer)} bytes，已保存: {path}")
        except Exception as exc:
            print(f"[IMAGE] 下载失败: {exc}")

    # ── 图文混排 ──────────────────────────────────────────

    @client.on("message.mixed")
    def on_mixed_message(frame) -> None:
        items = frame.body.mixed.msg_item or []
        print(f"[MIXED] 收到图文混排消息，包含 {len(items)} 个子项")
        for index, item in enumerate(items):
            if item.msgtype == "text":
                print(f"  [{index}] 文本: {item.text.content if item.text else ''}")
            elif item.msgtype == "image":
                print(f"  [{index}] 图片: {item.image.url if item.image else ''}")

    # ── 语音（转文本） ────────────────────────────────────

    @client.on("message.voice")
    def on_voice_message(frame) -> None:
        print(f"[VOICE] 收到语音消息（转文本）: {frame.body.voice.content}")

    # ── 视频消息 ──────────────────────────────────────────

    @client.on("message.video")
    async def on_video_message(frame) -> None:
        video = frame.body.video
        print(f"[VIDEO] 收到视频消息: {video.url}")
        if not video.url:
            return
        try:
            buffer, filename = await client.download_file(video.url, video.aeskey)
            path = await save_downloaded(buffer, filename, "video")
            print(f"[VIDEO] 下载成功，大小: {len(buffer)} bytes，已保存: {path}")
        except Exception as exc:
            print(f"[VIDEO] 下载失败: {exc}")

    # ── 文件消息：下载并解密 ──────────────────────────────

    @client.on("message.file")
    async def on_file_message(frame) -> None:
        file = frame.body.file
        print(f"[FILE] 收到文件消息: {file.url}")
        if not file.url:
            return
        try:
            buffer, filename = await client.download_file(file.url, file.aeskey)
            path = await save_downloaded(buffer, filename, "file")
            print(f"[FILE] 下载成功，大小: {len(buffer)} bytes，已保存: {path}")
        except Exception as exc:
            print(f"[FILE] 下载失败: {exc}")

    # ── 进入会话：欢迎语（需 5s 内） ──────────────────────

    @client.on("event.enter_chat")
    async def on_enter_chat(frame) -> None:
        print("[ENTER] 用户进入会话")
        await client.reply_welcome(
            frame,
            WelcomeTextReplyBody.create("您好！我是智能助手，有什么可以帮您的吗？"),
        )

    # ── 模板卡片事件 ──────────────────────────────────────

    @client.on("event.template_card_event")
    def on_template_card_event(frame) -> None:
        event_key = frame.body.event.event_key
        print(f"[CARD] 收到模板卡片事件: {event_key}")

    # ── 用户反馈事件 ──────────────────────────────────────

    @client.on("event.feedback_event")
    def on_feedback_event(frame) -> None:
        print(f"[FEEDBACK] 收到用户反馈事件: {frame.body.event}")

    # ── 启动 ──────────────────────────────────────────────

    print("[START] 正在连接...")
    client.connect()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOP] 正在断开...")
        await client.disconnect()
        print("[BYE] 已断开连接")


if __name__ == "__main__":
    asyncio.run(main())
