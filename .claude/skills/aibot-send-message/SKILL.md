---
name: aibot-send-message
description: 主动发送 Markdown 消息（无需用户先发消息）。当用户说"主动推送 / 主动发 / 定时通知 / sendMessage / Markdown" 时使用。
---

# aibot-send-message

主动向指定会话推送 Markdown 文本。  
目标：`userid`（单聊） 或 `chatid`（群聊）。

## 最小可用

```python
import asyncio, os
from dotenv import load_dotenv
from wecom_aibot import WSClient
from wecom_aibot.types import WSClientOptions, SendMarkdownMsgBody

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
    await asyncio.sleep(1)  # 等连接稳定

    chatid = os.getenv("WECOM_TARGET_CHATID")  # 或 userid
    body = SendMarkdownMsgBody.create(
        "## 标题\n\n**加粗**、- 列表、`代码` 都支持。"
    )
    result = await client.send_message(chatid, body)
    print(f"errcode={result.errcode}")
    await client.disconnect()

asyncio.run(main())
```

## Markdown 支持

| 语法 | 支持 |
|------|------|
| `# / ## / ###` 标题 | ✅ |
| `**粗体**`、`*斜体*` | ✅ |
| `-` / `1.` 列表 | ✅ |
| `` `code` ``、```` ```block``` ```` | ✅ |
| `[link](url)` | 部分支持（企业微信） |
| `<font color="info">` | 颜色标签 |

限制：最长 **20480 字节**。超出需截断或改用流式回复。

## 一次性发多条

```python
for delay, text in [(0, "第一条"), (2, "第二条")]:
    await asyncio.sleep(delay)
    await client.send_message(chatid, SendMarkdownMsgBody.create(text))
```

## 回执解读

```python
# WsFrame 字段：
#   errcode: 0 = 成功；93006 = invalid chatid；93000 系列 = 参数错
#   errmsg: 人类可读
```

## 陷阱

- 同一进程里 WS 长连接只能有一条，发完主动消息后**不要立刻 `disconnect`**，否则下一次还得重连认证。
- 如果连接刚建立就立刻 `send_message`，偶尔会因服务端鉴权未就绪失败，等 1 秒更稳。