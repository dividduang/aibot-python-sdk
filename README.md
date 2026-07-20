# wecom-aibot

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

企业微信智能机器人 Python SDK —— 基于 WebSocket 长连接通道。

将 Node.js SDK [`@wecom/aibot-node-sdk`](https://github.com/WecomTeam/aibot-node-sdk) 移植到 Python，提供完整类型提示与异步支持，并额外支持多机器人管理。

## 功能特性

| 能力 | 说明 | Node SDK |
|------|------|----------|
| WebSocket 长连接 | 自动认证、心跳、指数退避重连 | ✅ |
| 消息类型 | text / image / mixed / voice / file / **video** | ✅ |
| 流式回复 | Markdown，支持图文混排 | ✅ |
| 模板卡片 | 回复、流式+卡片、更新卡片 | ✅ |
| 主动推送 | Markdown / 模板卡片 / 媒体 | ✅ |
| 媒体上传 | 分片上传临时素材（file/image/voice/video） | ✅ |
| 文件下载解密 | AES-256-CBC（消息自带 aeskey） | ✅ |
| 事件回调 | enter_chat / template_card_event / feedback_event | ✅ |
| **多机器人** | `BotManager` 统一事件路由 | Python 增强 |
| 类型提示 | 完整 Type Hints + asyncio | — |

## 安装

```bash
pip install wecom-aibot
# 或
uv add wecom-aibot
```

## 快速开始

```bash
cp .env.example .env
# 编辑 .env：WECOM_BOT_ID / WECOM_BOT_SECRET
```

```python
import asyncio
import os
from dotenv import load_dotenv
from wecom_aibot import WSClient, generate_req_id
from wecom_aibot.types import WSClientOptions, WelcomeTextReplyBody

load_dotenv()

async def main():
    client = WSClient(WSClientOptions(
        bot_id=os.getenv("WECOM_BOT_ID"),
        secret=os.getenv("WECOM_BOT_SECRET"),
    ))

    @client.on("authenticated")
    def on_auth():
        print("认证成功")

    @client.on("message.text")
    async def on_text(frame):
        content = frame.body.text.content
        stream_id = generate_req_id("stream")
        await client.reply_stream(frame, stream_id, "正在思考...", finish=False)
        await client.reply_stream(
            frame, stream_id, f"收到: {content}", finish=True
        )

    @client.on("event.enter_chat")
    async def on_enter(frame):
        await client.reply_welcome(
            frame, WelcomeTextReplyBody.create("您好！有什么可以帮您的？")
        )

    client.connect()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await client.disconnect()

asyncio.run(main())
```

完整可运行示例见 [`examples/`](./examples/)。

## 示例

| 文件 | 说明 |
|------|------|
| [`examples/example_basic.py`](./examples/example_basic.py) | 综合示例（对齐 Node `examples/basic.ts`） |
| [`examples/example_send_message.py`](./examples/example_send_message.py) | 主动推送 Markdown / 卡片 |
| [`examples/example_upload_media.py`](./examples/example_upload_media.py) | 上传素材、被动/主动发媒体 |
| [`examples/example_event_message.py`](./examples/example_event_message.py) | 进入会话 / 卡片交互 / 反馈 |
| [`examples/example_multi_bot.py`](./examples/example_multi_bot.py) | 多机器人 `BotManager` |

```bash
uv sync --extra dev
uv run python examples/example_basic.py
uv run python examples/example_multi_bot.py --config bots_config.json
```

## API 文档

### WSClientOptions

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `bot_id` | str | 必填 | 机器人 ID |
| `secret` | str | 必填 | 机器人 Secret |
| `heartbeat_interval` | int | 30000 | 心跳间隔（毫秒） |
| `max_reconnect_attempts` | int | 10 | 最大重连次数，-1 无限 |
| `reconnect_interval` | int | 1000 | 重连基础延迟（毫秒） |
| `request_timeout` | int | 10000 | HTTP 请求超时（毫秒） |
| `ws_url` | str | `wss://openws.work.weixin.qq.com` | WebSocket 地址 |
| `logger` | Logger | None | 自定义日志器 |

### 事件列表

#### 连接事件

| 事件名 | 说明 | 回调参数 |
|--------|------|----------|
| `connected` | 连接建立 | 无 |
| `authenticated` | 认证成功 | 无 |
| `disconnected` | 连接断开 | reason: str |
| `reconnecting` | 正在重连 | attempt: int |
| `error` | 发生错误 | error: Exception |

#### 消息事件

| 事件名 | 说明 |
|--------|------|
| `message` | 所有消息 |
| `message.text` | 文本 |
| `message.image` | 图片 |
| `message.mixed` | 图文混排 |
| `message.voice` | 语音（已转文本） |
| `message.file` | 文件 |
| `message.video` | 视频 |

#### 事件回调

| 事件名 | 说明 |
|--------|------|
| `event` | 所有事件 |
| `event.enter_chat` | 用户进入会话（欢迎语需 5s 内） |
| `event.template_card_event` | 模板卡片按钮（更新需 5s 内） |
| `event.feedback_event` | 用户反馈 |

### 客户端方法

方法命名：Python 风格为 snake_case；媒体相关方法同时提供与 Node 一致的 camelCase 别名。

| 方法 | 说明 |
|------|------|
| `connect()` | 建立连接，返回 self |
| `disconnect()` | 断开连接（async） |
| `reply(frame, body, cmd?)` | 通用回复 |
| `reply_stream(frame, stream_id, content, finish?, ...)` | 流式文本回复 |
| `reply_welcome(frame, body)` | 欢迎语（text / 模板卡片） |
| `reply_template_card(frame, card, feedback?)` | 回复模板卡片 |
| `reply_stream_with_card(frame, stream_id, content, finish?, ...)` | 流式 + 卡片 |
| `update_template_card(frame, card, userids?)` | 更新模板卡片 |
| `send_message(chatid, body)` | 主动发送 Markdown / 卡片 / 媒体 |
| `upload_media` / `uploadMedia` | 分片上传临时素材 |
| `reply_media` / `replyMedia` | 被动回复媒体 |
| `send_media_message` / `sendMediaMessage` | 主动发送媒体 |
| `download_file(url, aes_key?)` | 下载并 AES 解密 |
| `is_connected` | 连接状态 |
| `api` | 底层 HTTP 客户端 |

```python
from wecom_aibot import generate_req_id
from wecom_aibot.types import SendMarkdownMsgBody, UploadMediaOptions

stream_id = generate_req_id("stream")
await client.reply_stream(frame, stream_id, "处理中...", finish=False)
await client.reply_stream(frame, stream_id, "完成", finish=True)

await client.send_message(chatid, SendMarkdownMsgBody.create("主动推送"))

result = await client.upload_media(file_bytes, UploadMediaOptions(type="image", filename="a.png"))
await client.reply_media(frame, "image", result.media_id)

buffer, filename = await client.download_file(url, aes_key)
```

## 多机器人管理

Python SDK 额外提供 `BotManager`（Node SDK 无对应模块）。

### JSON 配置

```json
// bots_config.json（可参考 bots_config.json.example）
{
  "bots": [
    { "name": "客服机器人", "bot_id": "xxx", "secret": "xxx" },
    { "name": "技术支持", "bot_id": "yyy", "secret": "yyy" }
  ]
}
```

```python
from wecom_aibot import BotManager

manager = BotManager()
manager.load_from_json("bots_config.json")

@manager.on("客服机器人.message.text")
async def on_service_text(frame):
    client = manager.get_bot("客服机器人")
    await client.reply_stream(frame, "s1", "客服回复", finish=True)

@manager.on("bot.connected")
def on_any(name: str):
    print(f"已连接: {name}")

manager.connect_all()
```

### 环境变量

```bash
WECOM_BOTS_COUNT=2
WECOM_BOT_1_NAME=客服机器人
WECOM_BOT_1_BOT_ID=xxx
WECOM_BOT_1_BOT_SECRET=xxx
WECOM_BOT_2_NAME=技术支持
WECOM_BOT_2_BOT_ID=yyy
WECOM_BOT_2_BOT_SECRET=yyy
```

单机器人兼容：`WECOM_BOT_ID` + `WECOM_BOT_SECRET`（名称为 `default`）。

## 项目结构

```
aibot-python-sdk/
├── examples/                 # 全部 demo（对照 Node examples/）
│   ├── example_basic.py
│   ├── example_send_message.py
│   ├── example_upload_media.py
│   ├── example_event_message.py
│   ├── example_multi_bot.py
│   └── README.md
├── src/wecom_aibot/
│   ├── __init__.py
│   ├── client.py             # WSClient
│   ├── bot_manager.py        # 多机器人
│   ├── ws_manager.py
│   ├── api_client.py
│   ├── message_handler.py
│   ├── crypto.py
│   ├── logger.py
│   ├── utils.py              # generate_req_id 等
│   ├── exceptions.py
│   └── types/
├── tests/
├── pyproject.toml
└── README.md
```

## 依赖

- Python >= 3.11
- websockets >= 12.0
- httpx >= 0.27.0
- pyee >= 11.0.0
- pycryptodome >= 3.20.0

## 开发

```bash
git clone <repo>
cd aibot-python-sdk
uv sync --extra dev
uv run pytest
uv run python examples/example_basic.py
```

## 相关链接

- [企业微信智能机器人开发文档](https://developer.work.weixin.qq.com/document/path/94838)
- [Node.js SDK 参考](https://github.com/WecomTeam/aibot-node-sdk)

## License

[MIT](LICENSE)
