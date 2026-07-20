---
name: aibot-send-media
description: 分片上传临时素材 + 主动发送媒体（file/image/voice/video）。当用户说"发文件 / 发图片 / 上传素材 / uploadMedia / sendMediaMessage" 时使用。
---

# aibot-send-media

通过 WebSocket 通道三步分片上传临时素材，再用 `send_media_message` 主动发或 `reply_media` 被动回复。

> 注意：上传走 WebSocket 长连接（不是 HTTP），需要 `WSClient` 已经认证。

## 1. 上传文件并主动发送

```python
import asyncio, os
from dotenv import load_dotenv
from wecom_aibot import WSClient
from wecom_aibot.types import WSClientOptions, UploadMediaOptions

load_dotenv()

async def main():
    client = WSClient(WSClientOptions(
        bot_id=os.getenv("WECOM_BOT_ID"),
        secret=os.getenv("WECOM_BOT_SECRET"),
    ))

    auth = asyncio.Event()
    @client.on("authenticated")
    def on_auth(): auth.set()
    client.connect()
    await asyncio.wait_for(auth.wait(), timeout=10)
    await asyncio.sleep(1)

    file_bytes = open("testfile.xlsx", "rb").read()

    # Step 1+2+3：init → chunk → finish，全部在 SDK 内完成
    result = await client.upload_media(
        file_bytes,
        UploadMediaOptions(type="file", filename="testfile.xlsx"),
    )
    print(f"media_id={result.media_id}")  # 3 天内有效

    # 主动发送
    target = os.getenv("WECOM_TARGET_USERID") or os.getenv("WECOM_TARGET_CHATID")
    await client.send_media_message(target, "file", result.media_id)
    await client.disconnect()

asyncio.run(main())
```

## 2. 媒体类型

```python
UploadMediaOptions(type="file", ...)   # 文件
UploadMediaOptions(type="image", ...)  # 图片
UploadMediaOptions(type="voice", ...)  # 语音
UploadMediaOptions(type="video", ..., video_options=VideoOptions(
    title="标题",
    description="描述",
))
```

`video` 额外需要 `title` / `description`，由 `VideoOptions` 传入。

## 3. 接收消息时被动回复（关键路径）

```python
@client.on("message.text")
async def on_text(frame):
    # 一次上传，多次复用 media_id
    result = await client.upload_media(
        open("report.pdf", "rb").read(),
        UploadMediaOptions(type="file", filename="report.pdf"),
    )
    await client.reply_media(frame, "file", result.media_id)
```

## 4. 限制

- 单分片 **≤ 512 KB**（Base64 编码前）
- 最多 **100 个分片**（约 50 MB）
- 并发：1–4 分片全并发；5–10 分片并发 3；> 10 分片并发 2
- 单分片失败最多重试 2 次

## 5. 踩过的坑

| 症状 | 原因 |
|------|------|
| `Upload init failed: no upload_id` | 服务端临时错误，重试 |
| `ChunkUploadError attempts=3` | 网络不稳，client 已重试仍失败 |
| `media_id expired` | media_id 有效期 3 天，需重新上传 |
| 上传后 send 报 `40007 invalid media_id` | 类型不匹配，例如 `image` 的 id 发成 `file` |