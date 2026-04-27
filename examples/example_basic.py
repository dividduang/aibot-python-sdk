"""
企业微信智能机器人 Python SDK 示例

使用方法：
1. 复制 .env.example 为 .env
2. 在 .env 中填写 bot_id 和 secret
3. 运行: uv run python example_basic.py
"""

import asyncio
from dotenv import load_dotenv
from wecom_aibot import WSClient, WSClientOptions
from wecom_aibot.types import (
    TemplateCard,
    TemplateCardMainTitle,
    StreamReplyBody,
    WelcomeTextReplyBody,
)

# 加载 .env 文件
load_dotenv()


def get_config():
    """从 .env 文件读取配置"""
    import os

    bot_id = os.getenv("WECOM_BOT_ID")
    secret = os.getenv("WECOM_BOT_SECRET")

    if not bot_id or not secret:
        raise ValueError("请在 .env 文件中设置 WECOM_BOT_ID 和 WECOM_BOT_SECRET")

    return bot_id, secret


async def main():
    # 从 .env 读取配置
    bot_id, secret = get_config()

    # 创建客户端
    options = WSClientOptions(
        bot_id=bot_id,
        secret=secret,
        heartbeat_interval=30000,  # 30秒
        max_reconnect_attempts=10,
    )

    client = WSClient(options)

    # 注册事件处理
    @client.on("connected")
    def on_connected():
        print("[OK] WebSocket 已连接")

    @client.on("authenticated")
    def on_authenticated():
        print("[OK] 认证成功")

    @client.on("disconnected")
    def on_disconnected(reason: str):
        print(f"[DISCONNECTED] 连接断开: {reason}")

    @client.on("reconnecting")
    def on_reconnecting(attempt: int):
        print(f"[RECONNECT] 正在重连，第 {attempt} 次")

    @client.on("error")
    def on_error(error: Exception):
        print(f"[ERROR] 发生错误: {error}")

    # 处理文本消息
    @client.on("message.text")
    async def on_text_message(frame):
        print(f"[TEXT] 收到文本消息: {frame.body.text.content}")

        # 流式回复示例
        stream_id = "stream_001"

        # 发送流式消息（不结束）
        await client.reply_stream(frame, stream_id, "正在处理您的请求...", finish=False)

        # 模拟处理
        await asyncio.sleep(1)

        # 发送最终回复
        await client.reply_stream(
            frame,
            stream_id,
            f"您发送的是：**{frame.body.text.content}**",
            finish=True,
        )

    # 处理图片消息
    @client.on("message.image")
    async def on_image_message(frame):
        print(f"[IMAGE] 收到图片消息: {frame.body.image.url}")

        # 下载并解密图片
        if frame.body.image.aeskey:
            buffer, filename = await client.download_file(
                frame.body.image.url,
                frame.body.image.aeskey,
            )
            print(f"   图片大小: {len(buffer)} 字节")

        # 回复
        await client.reply_stream(
            frame,
            "stream_img",
            "收到您的图片！",
            finish=True,
        )

    # 处理进入会话事件
    @client.on("event.enter_chat")
    async def on_enter_chat(frame):
        print(f"[ENTER] 用户进入会话: {frame.body.from_.userid}")

        # 发送欢迎语
        welcome = WelcomeTextReplyBody.create("您好！我是智能助手，有什么可以帮您的？")
        await client.reply_welcome(frame, welcome)

    # 处理模板卡片事件
    @client.on("event.template_card_event")
    async def on_template_card_event(frame):
        print(f"[CARD] 模板卡片事件: {frame.body.event.event_key}")

        # 更新卡片
        card = TemplateCard(
            card_type="text_notice",
            main_title=TemplateCardMainTitle(
                title="已处理",
                desc="您的请求已处理完成",
            ),
            task_id=frame.body.event.task_id,
        )
        await client.update_template_card(frame, card)

    # 连接
    print("[START] 正在连接...")
    client.connect()

    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOP] 正在断开...")
        await client.disconnect()
        print("[BYE] 已断开连接")


if __name__ == "__main__":
    asyncio.run(main())
