# Examples

企业微信智能机器人 Python SDK 示例集合。能力与 Node SDK `examples/basic.ts` 对齐，并补充 Python 侧多机器人、主动推送、媒体上传等场景。

## 准备

```bash
# 在 SDK 根目录
cp .env.example .env
# 编辑 .env，填写 WECOM_BOT_ID / WECOM_BOT_SECRET

uv sync --extra dev
```

可选环境变量：

| 变量 | 用途 |
|------|------|
| `WECOM_BOT_ID` / `WECOM_BOT_SECRET` | 单机器人凭证 |
| `WECOM_TARGET_USERID` | 主动发送媒体目标用户 |
| `WECOM_TARGET_CHATID` | 主动发送消息 / 测试卡片目标会话 |
| 多机器人变量 / `bots_config.json` | 见 `example_multi_bot.py` |

## 示例一览

| 文件 | 说明 | 对应 Node |
|------|------|-----------|
| `example_basic.py` | 连接、各类消息、流式回复、下载解密、欢迎语、事件 | `examples/basic.ts` |
| `example_send_message.py` | 主动推送 Markdown / 模板卡片 | `sendMessage` API |
| `example_upload_media.py` | 分片上传、被动/主动发媒体 | `uploadMedia` / `replyMedia` / `sendMediaMessage` |
| `example_event_message.py` | enter_chat / template_card / feedback | 事件回调 |
| `example_multi_bot.py` | 多机器人 `BotManager`（Python 增强） | — |

## 运行

```bash
uv run python examples/example_basic.py
uv run python examples/example_send_message.py
uv run python examples/example_upload_media.py
uv run python examples/example_event_message.py
uv run python examples/example_multi_bot.py
uv run python examples/example_multi_bot.py --config bots_config.json
```

下载的文件默认保存在 `examples/downloads/`（运行 `example_basic.py` 时自动创建）。
