---
name: aibot-send-button-card
description: 发送"按钮交互"模板卡片（`button_interaction`），含按钮点击回调与卡片更新。当用户说"按钮卡片 / 确认卡片 / 审批 / 投票 / button_interaction / template_card_event" 时使用。
---

# aibot-send-button-card

`button_interaction`：用户点击按钮触发 `event.template_card_event`，需在 5 秒内 `update_template_card`。

## 1. 发送按钮卡片

```python
import asyncio, os
from dotenv import load_dotenv
from wecom_aibot import WSClient
from wecom_aibot.types import (
    WSClientOptions, SendTemplateCardMsgBody,
    TemplateCard, TemplateCardSource, TemplateCardMainTitle,
    TemplateCardButton,
    generate_req_id,
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

    task_id = f"task_{generate_req_id('card')}"
    card = TemplateCard(
        card_type="button_interaction",
        source=TemplateCardSource(desc="任务审批", desc_color=1),
        main_title=TemplateCardMainTitle(
            title="是否发布 v1.2.0？",
            desc="点击下方按钮选择",
        ),
        task_id=task_id,
        button_list=[
            TemplateCardButton(text="确认发布", key="confirm", style=1),
            TemplateCardButton(text="取消",     key="cancel",  style=2),
        ],
    )

    chatid = os.getenv("WECOM_TARGET_CHATID")
    await client.send_message(chatid, SendTemplateCardMsgBody(template_card=card))
    print(f"task_id={task_id}")

    # 注册按钮回调
    @client.on("event.template_card_event")
    async def on_card(frame):
        ev = frame.body.event
        if ev.task_id != task_id:
            return
        # 5 秒内必须 update
        new_card = TemplateCard(
            card_type="text_notice",
            source=TemplateCardSource(desc="已处理"),
            main_title=TemplateCardMainTitle(
                title="[OK] 已确认" if ev.event_key == "confirm" else "[X] 已取消",
                desc=f"event_key={ev.event_key}",
            ),
            task_id=task_id,
            card_action=TemplateCardAction(type=1, url="https://work.weixin.qq.com"),
        )
        await client.update_template_card(frame, new_card)
        print(f"updated: {ev.event_key}")

    try:
        while True: await asyncio.sleep(1)
    except KeyboardInterrupt:
        await client.disconnect()

asyncio.run(main())
```

## 2. 按钮字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `text` | ✅ | 按钮文字（≤ 4 字） |
| `key`  | ✅ | 点击后回传 `event_key` |
| `style` |   | 1=蓝 2=红 3=灰 |

## 3. 回调与更新

```python
@client.on("event.template_card_event")
async def on_card(frame):
    # frame.body.event.event_key    # 用户点的按钮 key
    # frame.body.event.task_id      # 卡片任务 ID
    # 必须 5 秒内调用 update_template_card
    await client.update_template_card(frame, new_card)
```

约束：
- 新卡片 `task_id` 必须与原卡片一致。
- 同一 task_id 只能更新一次。
- `card_action.type=1` 时必须给 `url`；`type=2` 时给 `appid + pagepath`。

## 4. 其它交互卡类型

| `card_type` | 用途 | 示例 |
|-------------|------|------|
| `vote_interaction` | 单选投票 | `TemplateCardCheckbox` |
| `multiple_interaction` | 多项选择器 | `TemplateCardSelectionItem` |

详细字段可读 `src/wecom_aibot/types/template_card.py` 注释。