---
name: aibot-channel
description: 企业微信「频道（话题）」消息的识别、触发策略与 @机器人 事件处理。当用户说"频道 / 话题 / topic / channel / topic_at_bot / 话题里 @机器人 / 刷屏" 时使用。
---

# aibot-channel

频道（话题）场景的完整处理：**怎么识别频道、什么时候该回、怎么从 @机器人 事件还原被 @ 的内容**。

## 1. 识别：必须看 compat_info.source

频道消息复用群聊语义：`chattype` 仍是 `group`，**判定频道只能看 `compat_info.source == "channel"`**（SDK 已封装为 `is_channel`）。

```python
msg = frame.body
msg.is_channel          # True 表示来自频道
msg.topic_key          # 话题标识：优先 topic_id，回退 chatid
```

## 2. 关键事实：频道消息是全量推送的

> 2026-10-21 实测：话题里**没有 @机器人** 的普通消息同样会到达（与「群聊只有被 @ 才推送」不同），且**不会**伴随 `topic_at_bot` 事件。

所以「收到频道消息」≠「被呼叫」。逐条回复必然刷屏。

## 3. 触发策略（默认只回被 @ 的）

`WSClientOptions.channel_trigger`：

| 值 | 行为 |
|----|------|
| `"mention"`（默认） | 只回应正文以 @ 开头的频道消息，以及平台已通过 `topic_at_bot` 事件确认被 @ 的消息 |
| `"all"` | 回应话题内的每一条消息 |

```python
client = WSClient(WSClientOptions(
    bot_id=..., secret=...,
    channel_trigger="mention",   # 默认
))
```

判断用 `client.should_reply(msg)`，不要自己重复实现规则：

```python
@client.on("message.text")
async def on_text(frame):
    msg = frame.body
    if not msg.is_channel:
        return
    if not client.should_reply(msg):
        print(f"[SKIP] 话题里的普通消息: {msg.text.content}")
        return
    await client.reply_topic(frame, msg, "收到频道消息", finish=True)
```

## 4. 回复：用 reply_topic，不要直接 reply_stream

`reply_topic` 负责三件事：按策略判断、**去重**、用原始回调帧回复。

```python
await client.reply_topic(frame, msg, "收到频道消息", finish=True)
```

去重的必要性：同一次 @ 会带来「频道消息」+「`topic_at_bot` 事件」两条通路，直接各回一次就是重复回答。

## 5. topic_at_bot 事件：还原被 @ 的内容

事件体**既没有正文也没有 `chatid`**，只有 `msgid` / `from.userid` / `create_time` / `topic_id` / `event.post_id`。

```python
@client.on("event.topic_at_bot")
async def on_at_bot(frame):
    event = frame.body
    # 自动配对被 @ 的那条频道消息（等它到达），并去重
    await client.reply_topic_at_bot(event, "收到你的 @")
```

`reply_topic_at_bot` 内部按「用户 + 时间窗」配对；消息尚未到达时会等待 `channel_pair_window`（默认 30 秒）。

只想拿内容、不急着回复：

```python
paired = client.topic_tracker.pending_for(event)   # 未配对时为 None
if paired:
    print(paired.text.content)
```

## 6. id 空间不同：不要混用

| 载荷 | 频道标识 | 正文 |
|------|---------|------|
| 频道文本消息 | `chatid=opx…` | 有 |
| `topic_at_bot` 事件 | `topic_id=Ci…` | **无** |

两者前缀空间不同，**不能互相当作同一个 key**；需要关联时走配对器，不要自己拼 key。

## 7. 字段速查

| 字段 | 位置 | 说明 |
|------|------|------|
| `msg.is_channel` | 消息 | 是否来自频道 |
| `msg.at_list` | 消息 | 正文中的 @提及（原始提及名） |
| `msg.is_mention` | 消息 | 正文是否以 @ 开头，即是否在呼叫机器人 |
| `msg.topic_key` | 消息 / 事件 | 话题标识（优先 `topic_id`，回退 `chatid`） |
| `event.post_id` | `topic_at_bot` / `topic_event` 内 | 相关帖子 ID |
| `event.type` | `topic_event` 内 | 事件细分类型，语义未公开 |

## 8. 事件一览

| 事件名 | 何时触发 |
|--------|---------|
| `event.topic_at_bot` | 频道中 @机器人（无正文，靠配对还原） |
| `event.topic_event` | 频道事件（`type` / `post_id`，原始数据在 `event.data`） |
| `event.topic` | 所有频道事件（`eventtype` 以 `topic` 开头） |

## 9. 踩过的坑

| 症状 | 原因 | 处理 |
|------|------|------|
| 话题里机器人刷屏 | 频道消息全量推送，逐条回复了 | 用 `should_reply` + `reply_topic`，或改 `channel_trigger="all"`（仅在确实需要时） |
| 同一次 @ 回了两次 | 消息与 `topic_at_bot` 事件各回了一次 | 统一走 `reply_topic`（自带去重） |
| 事件里拿不到用户说了什么 | 事件体无正文 | `reply_topic_at_bot` 或 `topic_tracker.pending_for(event)` |
| `should_reply` 恒为 False | 消息不是频道消息（缺 `compat_info.source`） | 确认机器人确实被加进了频道 |
| 配对到了别人的消息 | 同用户时间窗内发了多条 | 收紧 `channel_pair_window`；配对优先选正文以 @ 开头的那条 |

## 10. 可运行示例

- `examples/example_channel.py`：默认触发策略（非 @ 消息打印 `[SKIP]`）
- `examples/example_topic_trigger.py`：`channel_trigger="all"`
