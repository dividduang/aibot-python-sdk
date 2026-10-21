# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

## [Unreleased]

### Added

- 频道（话题）触发策略：`WSClientOptions.channel_trigger`，默认 `"mention"`（只回应正文以 @ 开头的频道消息），可设为 `"all"` 回应话题内全部消息。
- 频道（话题）配对时间窗配置：`WSClientOptions.channel_pair_window`，默认 30 秒。
- `TopicMentionTracker`：把频道消息与 `topic_at_bot` 事件配对（配对键为「用户 + 时间窗」），并按消息身份去重，避免同一次 @ 回答两次。
- `WSClient.should_reply(message)`：按触发策略判断频道消息是否应被回应。
- `WSClient.reply_topic(frame, message, content)`：按策略 + 去重回应一条频道消息。
- `WSClient.reply_topic_at_bot(event, content)`：从 `topic_at_bot` 事件还原被 @ 的频道消息并回应。
- `WSClient.options` / `WSClient.topic_tracker` 只读属性。
- 消息类型新增字段：`BaseMessage.topic_id` / `at_list` / `is_mention`，`BaseMessage.topic_key` 与 `EventMessage.topic_key` 属性（优先 `topic_id`，回退 `chatid`）。
- 新增示例 `examples/example_topic_trigger.py`（`channel_trigger="all"`）。

### Changed

- `examples/example_channel.py` 改为体现触发策略：未被 @ 的频道消息打印 `[SKIP]` 而不回复。
- `BaseMessage` 解析时填充正文中的 @提及（`at_list` / `is_mention`）。

### Notes

- 企微对「频道」是**全量推送**的：话题里没有 @机器人 的普通消息同样会到达，与「群聊只有被 @ 才推送」不同。SDK 默认触发策略因此为 `mention`，避免逐条刷屏；如需保留旧的全量回复行为，显式设置 `channel_trigger="all"`。
- 频道消息体只有 `chatid`，`topic_at_bot` 事件体只有 `topic_id`，两者 id 前缀空间不同，不能互相当作同一个 key，需通过「用户 + 时间窗」配对。
