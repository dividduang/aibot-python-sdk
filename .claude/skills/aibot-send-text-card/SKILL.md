---
name: aibot-send-text-card
description: 发送"文本通知"模板卡片（`text_notice`）。当用户说"发个通知 / 卡片 / 系统公告 / text_notice / notification card" 时使用。
---

# aibot-send-text-card

`text_notice` 模板卡片：单行主标题 + 可选重点数据 + 可选跳转。

## 最小可用

```python
import asyncio, os
from dotenv import load_dotenv
from wecom_aibot import WSClient
from wecom_aibot.types import (
    WSClientOptions, SendTemplateCardMsgBody,
    TemplateCard, TemplateCardSource, TemplateCardMainTitle,
    TemplateCardEmphasisContent, TemplateCardAction,
)

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

    card = TemplateCard(
        card_type="text_notice",
        source=TemplateCardSource(desc="系统通知", desc_color=1),
        main_title=TemplateCardMainTitle(
            title="服务发布完成",
            desc="v1.2.0 已上线",
        ),
        emphasis_content=TemplateCardEmphasisContent(
            title="状态",
            desc="全部正常",
        ),
        card_action=TemplateCardAction(
            type=1,                       # 1=跳转 URL
            url="https://work.weixin.qq.com",
        ),
    )

    chatid = os.getenv("WECOM_TARGET_CHATID")
    result = await client.send_message(
        chatid,
        SendTemplateCardMsgBody(template_card=card),
    )
    print(f"errcode={result.errcode}")
    await client.disconnect()

asyncio.run(main())
```

## 字段说明

| 字段 | 必须 | 说明 |
|------|------|------|
| `card_type` | ✅ | 固定 `text_notice` |
| `source.desc` |   | 来源描述（卡片左上角小字） |
| `source.desc_color` |   | 0=灰 1=蓝 2=绿 3=红 |
| `main_title.title` | ✅ | 主标题（黑色加粗） |
| `main_title.desc` |   | 副标题（灰色） |
| `emphasis_content` |   | 关键数据样式（中部大字） |
| `sub_title_text` |   | 二级文本 |
| `card_action.type=1` |   | 整体点击跳转（需 `url`） |
| `card_action.type=2` |   | 跳转小程序（需 `appid` + `pagepath`） |

## 配色

`desc_color`: 0=灰(默认)、1=蓝、2=绿、3=红。  
慎用红色，避免被识别为告警噪音。

## 配合流式

收到消息时也可以流式 + 卡片组合回复：

```python
await client.reply_stream_with_card(
    frame, stream_id, "处理完成，详见卡片：",
    finish=True, template_card=card,
)
```