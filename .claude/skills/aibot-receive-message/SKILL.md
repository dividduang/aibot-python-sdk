---
name: aibot-receive-message
description: 接收并处理来自企业微信的消息（text/image/file/video/voice/mixed）与事件（enter_chat/template_card/feedback）。当用户说"接收消息 / 监听机器人 / 收到消息 / 事件回调 / reply / reply_stream" 时使用。
---

# aibot-receive-message

收消息 + 事件 + 被动回复。

## 事件总览

| 事件名 | 何时触发 | `frame.body` 类型 |
|--------|---------|------------------|
| `message.text` | 文本 | `TextMessage` |
| `message.image` | 图片 | `ImageMessage` |
| `message.file` | 文件 | `FileMessage` |
| `message.video` | 视频 | `VideoMessage` |
| `message.voice` | 语音（已转文本） | `VoiceMessage` |
| `message.mixed` | 图文混排 | `MixedMessage` |
| `message` | 所有消息 | `BaseMessage` |
| `event.enter_chat` | 用户当天首次点开单聊 | `EventMessage` |
| `event.template_card_event` | 点击按钮卡片 | `EventMessage` |
| `event.feedback_event` | 点赞/点踩 | `EventMessage` |

## 流式回复（最常用）

```python
from wecom_aibot import generate_req_id

@client.on("message.text")
async def on_text(frame):
    content = frame.body.text.content
    user = frame.body.from_.userid
    chatid = frame.body.chatid           # 群聊时存在
    chattype = frame.body.chattype       # "single" | "group"

    stream_id = generate_req_id("stream")

    # 中间过程
    await client.reply_stream(frame, stream_id, "正在思考...", finish=False)
    await asyncio.sleep(1)

    # 最终结果
    await client.reply_stream(
        frame, stream_id,
        f"你好 {user}，你说的是: **{content}**",
        finish=True,
    )
```

> `stream_id` 用 `generate_req_id("stream")`，必须全局唯一（每次会话换一个）。

## 图片/文件下载解密

每条图片/文件消息自带独立 `aeskey`，URL 5 分钟内有效：

```python
@client.on("message.image")
async def on_image(frame):
    img = frame.body.image
    buf, filename = await client.download_file(img.url, img.aeskey)
    # buf 是解密后的 bytes，filename 来自响应头或 URL
    save_path = f"downloads/{filename or 'image.png'}"
    Path(save_path).write_bytes(buf)
```

## 进会话欢迎语（5 秒窗口）

```python
@client.on("event.enter_chat")
async def on_enter(frame):
    user = frame.body.from_.userid
    await client.reply_welcome(
        frame,
        WelcomeTextReplyBody.create(f"您好 {user}！我是智能助手。"),
    )
```

## 模板卡片点击 → 更新

参见 `aibot-send-button-card`。

## 反馈事件

```python
@client.on("event.feedback_event")
async def on_feedback(frame):
    # 业务：写入 DB，用于改进回复质量
    print(f"user={frame.body.from_.userid} feedback={frame.body.event}")
```

## 真实抓包日志（2026-07-20）

```
[14:03:35] CAPTURE message.text userid=15577726720 chattype=group
            chatid=wrigAJEAAAm8vuxbYMQ1Bviptxh62_2A  text="@小益ZOOM 1"
[14:03:46] CAPTURE event.enter_chat userid=15577726720 chattype=single
[14:03:50] CAPTURE message.text userid=15577726720 chattype=single  text="你好"
```

> **要点**：单聊 `chatid` 为空，必须用 `from_.userid` 唯一定位用户；群聊 `chatid` 有值。

## 反向定位

拿到 `userid` / `chatid` 后可在 `.env` 里设为 `WECOM_TARGET_USERID` / `WECOM_TARGET_CHATID`，供主动推送 demo 使用。