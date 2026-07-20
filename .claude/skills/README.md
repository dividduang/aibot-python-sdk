# aibot-python-sdk skills

按场景拆分，每个 skill 独立可复用。

| Skill | 用途 |
|-------|------|
| [`aibot-onboard`](./aibot-onboard/SKILL.md) | 环境、`.env`、长连接启动、常见错误排查 |
| [`aibot-receive-message`](./aibot-receive-message/SKILL.md) | 接收消息 / 事件 / 被动回复 |
| [`aibot-send-message`](./aibot-send-message/SKILL.md) | 主动推送 Markdown |
| [`aibot-send-text-card`](./aibot-send-text-card/SKILL.md) | `text_notice` 文本通知卡片 |
| [`aibot-send-button-card`](./aibot-send-button-card/SKILL.md) | `button_interaction` 按钮交互卡片 |
| [`aibot-send-media`](./aibot-send-media/SKILL.md) | 分片上传 + 主动/被动发媒体 |

## 典型组合

```text
onboard                    ← 先做接入
  └─ receive-message       ← 监听用户消息
       ├─ send-message     ← 直接 Markdown 推送
       ├─ send-text-card   ← 推送通知卡片
       ├─ send-button-card ← 推送按钮卡片 + 更新
       └─ send-media       ← 上传素材并发图/文件/视频
```