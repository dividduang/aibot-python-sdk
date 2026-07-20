"""
媒体上传示例

演示 upload_media / reply_media / send_media_message：
1. 认证后上传本地文件
2. 可选：主动发送给目标用户（WECOM_TARGET_USERID）
3. 收到文本消息时被动回复该媒体

使用方法：
1. 配置 .env：WECOM_BOT_ID / WECOM_BOT_SECRET，可选 WECOM_TARGET_USERID
2. 准备测试文件（默认读取项目根目录 testfile.xlsx，也可改 LOCAL_FILE）
3. 运行: uv run python examples/example_upload_media.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from wecom_aibot import WSClient, UploadError
from wecom_aibot.types import UploadMediaOptions, WSClientOptions

load_dotenv()

# 相对 SDK 根目录的测试文件；也可改为绝对路径
ROOT = Path(__file__).resolve().parents[1]
LOCAL_FILE = ROOT / "testfile.xlsx"
MEDIA_TYPE = "file"  # file / image / voice / video


async def main() -> None:
    bot_id = os.getenv("WECOM_BOT_ID")
    secret = os.getenv("WECOM_BOT_SECRET")
    target_userid = os.getenv("WECOM_TARGET_USERID")

    if not bot_id or not secret:
        print("[ERROR] 请在 .env 文件中设置 WECOM_BOT_ID 和 WECOM_BOT_SECRET")
        return

    if not LOCAL_FILE.exists():
        print(f"[ERROR] 测试文件不存在: {LOCAL_FILE}")
        print("请放置文件，或修改 LOCAL_FILE 路径")
        return

    file_bytes = LOCAL_FILE.read_bytes()
    filename = LOCAL_FILE.name
    print(f"[FILE] {filename} ({len(file_bytes)} bytes)")
    print(f"[CONFIG] Target User: {target_userid or '未配置（收到文本时被动回复）'}")

    client = WSClient(WSClientOptions(bot_id=bot_id, secret=secret))
    upload_result = None

    @client.on("connected")
    def on_connected() -> None:
        print("[WS] 已连接")

    @client.on("authenticated")
    async def on_authenticated() -> None:
        nonlocal upload_result
        print("[WS] 认证成功，开始上传...")
        try:
            upload_result = await client.upload_media(
                file_bytes,
                UploadMediaOptions(type=MEDIA_TYPE, filename=filename),
            )
            print(
                f"[UPLOAD] OK media_id={upload_result.media_id} "
                f"type={upload_result.type} created_at={upload_result.created_at}"
            )

            if target_userid:
                print(f"[SEND] 主动发送给: {target_userid}")
                await client.send_media_message(target_userid, MEDIA_TYPE, upload_result.media_id)
                print("[SEND] OK")
            else:
                print("[INFO] 未配置 WECOM_TARGET_USERID，发送任意文本给机器人即可被动回复该文件")
        except UploadError as exc:
            print(f"[ERROR] 上传失败: {exc}")
        except Exception as exc:
            print(f"[ERROR] {type(exc).__name__}: {exc}")

    @client.on("message.text")
    async def on_text_message(frame) -> None:
        nonlocal upload_result
        print(f"[MSG] 收到文本: {frame.body.text.content}")

        if not upload_result:
            print("[UPLOAD] 尚未上传，开始上传...")
            upload_result = await client.upload_media(
                file_bytes,
                UploadMediaOptions(type=MEDIA_TYPE, filename=filename),
            )
            print(f"[UPLOAD] OK media_id={upload_result.media_id}")

        print("[REPLY] 被动回复媒体...")
        await client.reply_media(frame, MEDIA_TYPE, upload_result.media_id)
        print("[REPLY] OK")

    @client.on("error")
    def on_error(error: Exception) -> None:
        print(f"[ERROR] {error}")

    @client.on("disconnected")
    def on_disconnected(reason: str) -> None:
        print(f"[WS] 断开连接: {reason}")

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
