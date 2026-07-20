"""
多机器人管理器
支持同时管理多个企业微信智能机器人，统一事件路由和生命周期管理
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from pyee.asyncio import AsyncIOEventEmitter

from wecom_aibot.client import WSClient
from wecom_aibot.logger import DefaultLogger
from wecom_aibot.types import WSClientOptions, WsFrame, Logger
from wecom_aibot.types.config import BotConfig, BotStatus


class BotManager(AsyncIOEventEmitter):
    """
    多机器人管理器

    统一管理多个 WSClient 实例，支持：
    - 从环境变量、JSON 配置文件加载多个机器人配置
    - 同时连接/断开所有机器人
    - 事件路由：携带 bot_name 标识，方便区分消息来源
    - 按名称获取单个机器人客户端
    - 运行状态监控

    事件命名规则：
    - "{bot_name}.connected"       — 某个机器人连接成功
    - "{bot_name}.authenticated"   — 某个机器人认证成功
    - "{bot_name}.disconnected"    — 某个机器人断开连接
    - "{bot_name}.error"           — 某个机器人发生错误
    - "{bot_name}.message"         — 某个机器人收到消息（通用）
    - "{bot_name}.message.text"    — 某个机器人收到文本消息
    - "{bot_name}.message.image"   — 某个机器人收到图片消息
    - "{bot_name}.message.mixed"   — 某个机器人收到图文混排消息
    - "{bot_name}.message.voice"   — 某个机器人收到语音消息
    - "{bot_name}.message.file"    — 某个机器人收到文件消息
    - "{bot_name}.event"           — 某个机器人收到事件（通用）
    - "{bot_name}.event.enter_chat"         — 某个机器人收到进入会话事件
    - "{bot_name}.event.template_card_event" — 某个机器人收到模板卡片事件
    - "{bot_name}.event.feedback_event"     — 某个机器人收到反馈事件
    - "bot.connected"              — 任意机器人连接成功
    - "bot.disconnected"           — 任意机器人断开连接
    - "bot.error"                  — 任意机器人发生错误
    """

    def __init__(self, logger: Logger | None = None):
        super().__init__()
        self._logger = logger or DefaultLogger("[BotManager]")
        self._bots: dict[str, WSClient] = {}
        self._configs: dict[str, BotConfig] = {}
        self._statuses: dict[str, BotStatus] = {}

    # ── 配置加载 ──────────────────────────────────────────

    def add_bot(self, config: BotConfig) -> None:
        """
        添加一个机器人配置

        Args:
            config: 机器人配置

        Raises:
            ValueError: 配置缺少 bot_id 或 secret，或 name 已存在
        """
        if not config.bot_id or not config.secret:
            raise ValueError(f"机器人配置缺少 bot_id 或 secret: {config}")

        name = config.name or config.bot_id
        if name in self._configs:
            raise ValueError(f"机器人名称已存在: {name}")

        self._configs[name] = config
        self._statuses[name] = BotStatus(name=name)

    def load_from_env(self, prefixes: list[str] | None = None) -> int:
        """
        从环境变量加载多个机器人配置

        环境变量格式：
            方式一：使用前缀列表
                WECOM_BOT_1_BOT_ID=xxx
                WECOM_BOT_1_BOT_SECRET=xxx
                WECOM_BOT_2_BOT_ID=yyy
                WECOM_BOT_2_BOT_SECRET=yyy

            方式二：使用默认格式（自动检测）
                WECOM_BOTS_COUNT=2
                WECOM_BOT_1_BOT_ID=xxx  (或 WECOM_BOT_ID=xxx 用于单机器人)
                ...

        Args:
            prefixes: 环境变量前缀列表，如 ["WECOM_BOT_1", "WECOM_BOT_2"]
                      为 None 时自动检测

        Returns:
            成功加载的机器人数量
        """
        before = len(self._configs)

        if prefixes is not None:
            for prefix in prefixes:
                config = BotConfig.from_env(prefix)
                if config.bot_id and config.secret:
                    self.add_bot(config)
            return len(self._configs) - before

        # 自动检测模式
        count_str = os.getenv("WECOM_BOTS_COUNT", "")
        if count_str:
            # 多机器人模式：WECOM_BOT_1_BOT_ID, WECOM_BOT_1_BOT_SECRET, ...
            count = int(count_str)
            for i in range(1, count + 1):
                config = BotConfig.from_env(f"WECOM_BOT_{i}")
                if config.bot_id and config.secret:
                    self.add_bot(config)
        else:
            # 单机器人模式（兼容旧配置 WECOM_BOT_ID / WECOM_BOT_SECRET）
            bot_id = os.getenv("WECOM_BOT_ID", "")
            secret = os.getenv("WECOM_BOT_SECRET", "")
            if bot_id and secret:
                config = BotConfig(
                    name=os.getenv("WECOM_BOT_NAME", "default"),
                    bot_id=bot_id,
                    secret=secret,
                    ws_url=os.getenv("WECOM_BOT_WS_URL", "wss://openws.work.weixin.qq.com"),
                )
                self.add_bot(config)

        return len(self._configs) - before

    def load_from_json(self, file_path: str) -> int:
        """
        从 JSON 配置文件加载多个机器人配置

        JSON 格式：
        {
            "bots": [
                {
                    "name": "客服机器人",
                    "bot_id": "xxx",
                    "secret": "xxx"
                },
                {
                    "name": "技术支持机器人",
                    "bot_id": "yyy",
                    "secret": "yyy"
                }
            ]
        }

        Args:
            file_path: JSON 配置文件路径

        Returns:
            成功加载的机器人数量
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        before = len(self._configs)
        bots = data.get("bots", [])
        for bot_data in bots:
            config = BotConfig.from_dict(bot_data)
            if config.bot_id and config.secret:
                self.add_bot(config)

        return len(self._configs) - before

    def load_from_dict(self, data: dict[str, Any]) -> int:
        """
        从字典加载多个机器人配置

        Args:
            data: 配置字典，格式同 JSON

        Returns:
            成功加载的机器人数量
        """
        before = len(self._configs)
        bots = data.get("bots", [])
        for bot_data in bots:
            config = BotConfig.from_dict(bot_data)
            if config.bot_id and config.secret:
                self.add_bot(config)

        return len(self._configs) - before

    # ── 连接管理 ──────────────────────────────────────────

    def connect_all(self) -> None:
        """连接所有已配置的机器人"""
        if not self._configs:
            self._logger.warn("没有配置任何机器人，请先调用 load_from_env / load_from_json / add_bot")
            return

        for name, config in self._configs.items():
            self._connect_bot(name, config)

        self._logger.info(f"已启动 {len(self._configs)} 个机器人连接")

    def connect_bot(self, name: str) -> None:
        """连接指定名称的机器人"""
        config = self._configs.get(name)
        if not config:
            raise ValueError(f"未找到机器人配置: {name}")
        self._connect_bot(name, config)

    def _connect_bot(self, name: str, config: BotConfig) -> WSClient:
        """创建并连接单个机器人"""
        # 断开已有连接，防止资源泄漏
        existing = self._bots.get(name)
        if existing:
            asyncio.create_task(existing.disconnect())

        bot_logger = DefaultLogger(f"[{name}]")
        options = config.to_ws_client_options(logger=bot_logger)
        client = WSClient(options)

        # 注册转发事件
        self._setup_bot_events(name, client)

        self._bots[name] = client
        client.connect()
        return client

    async def disconnect_all(self) -> None:
        """断开所有机器人连接"""
        tasks = []
        for name, client in self._bots.items():
            self._logger.info(f"正在断开机器人: {name}")
            tasks.append(client.disconnect())

        await asyncio.gather(*tasks, return_exceptions=True)
        self._bots.clear()
        self._logger.info("所有机器人已断开")

    async def disconnect_bot(self, name: str) -> None:
        """断开指定名称的机器人"""
        client = self._bots.get(name)
        if not client:
            return
        await client.disconnect()
        del self._bots[name]
        self._logger.info(f"机器人已断开: {name}")

    # ── 事件路由 ──────────────────────────────────────────

    def _setup_bot_events(self, name: str, client: WSClient) -> None:
        """为单个机器人设置事件转发"""

        @client.on("connected")
        def on_connected():
            self._update_status(name, connected=True)
            self.emit(f"{name}.connected")
            self.emit("bot.connected", name)

        @client.on("authenticated")
        def on_authenticated():
            self._update_status(name, authenticated=True)
            self.emit(f"{name}.authenticated")

        @client.on("disconnected")
        def on_disconnected(reason: str):
            self._update_status(name, connected=False, authenticated=False)
            self.emit(f"{name}.disconnected", reason)
            self.emit("bot.disconnected", name, reason)

        @client.on("reconnecting")
        def on_reconnecting(attempt: int):
            status = self._statuses.get(name)
            if status:
                status.reconnect_count = attempt
            self.emit(f"{name}.reconnecting", attempt)

        @client.on("error")
        def on_error(error: Exception):
            self._update_status(name, last_error=str(error))
            self.emit(f"{name}.error", error)
            self.emit("bot.error", name, error)

        # 转发消息事件
        for event_name in [
            "message", "message.text", "message.image",
            "message.mixed", "message.voice", "message.file",
        ]:
            self._forward_event(client, name, event_name)

        # 转发事件类型
        for event_name in [
            "event", "event.enter_chat",
            "event.template_card_event", "event.feedback_event",
        ]:
            self._forward_event(client, name, event_name)

    def _forward_event(self, client: WSClient, name: str, event_name: str) -> None:
        """转发单个事件到 BotManager"""
        @client.on(event_name)
        def handler(*args):
            self.emit(f"{name}.{event_name}", *args)

    def _update_status(
        self,
        name: str,
        connected: bool | None = None,
        authenticated: bool | None = None,
        last_error: str | None = None,
    ) -> None:
        """更新机器人状态"""
        status = self._statuses.get(name)
        if not status:
            return
        if connected is not None:
            status.connected = connected
        if authenticated is not None:
            status.authenticated = authenticated
        if last_error is not None:
            status.last_error = last_error

    # ── 查询接口 ──────────────────────────────────────────

    def get_bot(self, name: str) -> WSClient | None:
        """按名称获取机器人客户端"""
        return self._bots.get(name)

    def get_bot_config(self, name: str) -> BotConfig | None:
        """按名称获取机器人配置"""
        return self._configs.get(name)

    def get_status(self, name: str) -> BotStatus | None:
        """获取机器人运行状态"""
        return self._statuses.get(name)

    def get_all_statuses(self) -> dict[str, BotStatus]:
        """获取所有机器人运行状态"""
        for name, client in self._bots.items():
            status = self._statuses.get(name)
            if status:
                status.connected = client.is_connected
        return dict(self._statuses)

    @property
    def bot_names(self) -> list[str]:
        """获取所有机器人名称列表"""
        return list(self._configs.keys())

    @property
    def bot_count(self) -> int:
        """获取机器人数量"""
        return len(self._configs)

    def print_status(self) -> None:
        """打印所有机器人状态"""
        statuses = self.get_all_statuses()
        self._logger.info(f"=== 机器人状态总览 ({len(statuses)} 个) ===")
        for name, status in statuses.items():
            conn = "[OK] 已连接" if status.connected else "[--] 未连接"
            auth = "[OK] 已认证" if status.authenticated else "[--] 未认证"
            error = f" | 错误: {status.last_error}" if status.last_error else ""
            self._logger.info(f"  [{name}] {conn} | {auth}{error}")
