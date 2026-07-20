---
name: aibot-onboard
description: 环境与机器人接入（凭证、.env、长连接启动）。当用户问"怎么跑 aibot-python-sdk / 怎么接入 / 配置 .env / 连接失败"时使用。
---

# aibot-onboard

把 `aibot-python-sdk` 跑起来的最少步骤。

## 1. 安装

```bash
pip install wecom-aibot
# 或
uv add wecom-aibot
```

Python >= 3.11。

## 2. 凭证

企业微信后台 → 智能机器人 → 获取 `bot_id` 和 `secret`。  
**绝不要** 把真凭证写进代码或 git。`.env` 必须加入 `.gitignore`。

```env
WECOM_BOT_ID=aibKxxxxxxxx
WECOM_BOT_SECRET=xxxxxxxx
WECOM_TARGET_USERID=对方userid      # 主动发单聊用（可选）
WECOM_TARGET_CHATID=wrigAJxxxxxx     # 主动发群聊用（可选）
```

## 3. 连接

```python
import asyncio, os
from dotenv import load_dotenv
from wecom_aibot import WSClient
from wecom_aibot.types import WSClientOptions

load_dotenv()

async def main():
    client = WSClient(WSClientOptions(
        bot_id=os.getenv("WECOM_BOT_ID"),
        secret=os.getenv("WECOM_BOT_SECRET"),
    ))

    @client.on("authenticated")
    def on_auth():
        print("已认证")

    client.connect()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await client.disconnect()

asyncio.run(main())
```

## 4. 验证三条路径

| 检查 | 通过标准 |
|------|---------|
| `WS connected` | ws 建连成功 |
| `认证成功` | bot_id/secret 正确 |
| 心跳 pong | 每 30 秒一次，debug 日志可见 |

## 5. 常见坑（2026-07 真实踩过）

- **Windows GBK 控制台**：打印 `✓`/`✗` 会崩溃 `UnicodeEncodeError`。`DefaultLogger` 已加 `errors="replace"` 兜底，但脚本里自定义 print 仍要避免非 ASCII 符号。
- **同 bot 多连接**：同一 `bot_id` 只允许一条有效 WS，否则推送会被服务端断开。启动前 `wmic process where "CommandLine like '%example_basic%' or CommandLine like '%_listen_capture%'" get ProcessId` 排查。
- **认证通过 ≠ 收到消息**：必须实际在企业微信向该机器人发消息，群聊要 `@机器人` 才会推送。
- **首次 `enter_chat`**：用户当天首次点开单聊才会触发，欢迎语须在 5 秒内发送。