"""配置相关类型定义"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Any


class Logger(Protocol):
    """日志接口协议"""

    def debug(self, message: str, *args: Any) -> None: ...
    def info(self, message: str, *args: Any) -> None: ...
    def warn(self, message: str, *args: Any) -> None: ...
    def error(self, message: str, *args: Any) -> None: ...


@dataclass
class WSClientOptions:
    """WSClient 配置选项"""

    # 机器人 ID（在企业微信后台获取）
    bot_id: str
    # 机器人 Secret（在企业微信后台获取）
    secret: str
    # WebSocket 重连基础延迟（毫秒），实际延迟按指数退避递增，默认 1000
    reconnect_interval: int = 1000
    # 最大重连次数，默认 10，设为 -1 表示无限重连
    max_reconnect_attempts: int = 10
    # 心跳间隔（毫秒），默认 30000
    heartbeat_interval: int = 30000
    # 请求超时时间（毫秒），默认 10000
    request_timeout: int = 10000
    # 自定义 WebSocket 连接地址，默认 wss://openws.work.weixin.qq.com
    ws_url: str = "wss://openws.work.weixin.qq.com"
    # 自定义日志函数
    logger: Logger | None = None


@dataclass
class BotConfig:
    """单个机器人配置"""

    # 机器人名称（用于标识，非必填）
    name: str = ""
    # 机器人 ID
    bot_id: str = ""
    # 机器人 Secret
    secret: str = ""
    # WebSocket 连接地址（可选，留空使用默认值）
    ws_url: str = "wss://openws.work.weixin.qq.com"
    # 心跳间隔（毫秒），可选
    heartbeat_interval: int = 30000
    # 最大重连次数，可选
    max_reconnect_attempts: int = 10
    # 重连基础延迟（毫秒），可选
    reconnect_interval: int = 1000
    # 请求超时（毫秒），可选
    request_timeout: int = 10000

    def to_ws_client_options(self, logger: Logger | None = None) -> WSClientOptions:
        """转换为 WSClientOptions"""
        return WSClientOptions(
            bot_id=self.bot_id,
            secret=self.secret,
            ws_url=self.ws_url,
            heartbeat_interval=self.heartbeat_interval,
            max_reconnect_attempts=self.max_reconnect_attempts,
            reconnect_interval=self.reconnect_interval,
            request_timeout=self.request_timeout,
            logger=logger,
        )

    @staticmethod
    def from_env(prefix: str = "WECOM_BOT") -> "BotConfig":
        """
        从环境变量加载单个机器人配置

        环境变量格式：
            {prefix}_BOT_ID - 机器人 ID
            {prefix}_BOT_SECRET - 机器人 Secret
            {prefix}_WS_URL - WebSocket 地址（可选）
            {prefix}_HEARTBEAT_INTERVAL - 心跳间隔（可选）
            {prefix}_MAX_RECONNECT_ATTEMPTS - 最大重连次数（可选）

        示例：prefix="WECOM_BOT_1" → WECOM_BOT_1_BOT_ID, WECOM_BOT_1_BOT_SECRET
        """
        import os

        bot_id = os.getenv(f"{prefix}_BOT_ID", "")
        secret = os.getenv(f"{prefix}_BOT_SECRET", "")

        return BotConfig(
            name=os.getenv(f"{prefix}_NAME", prefix),
            bot_id=bot_id,
            secret=secret,
            ws_url=os.getenv(f"{prefix}_WS_URL", "wss://openws.work.weixin.qq.com"),
            heartbeat_interval=int(os.getenv(f"{prefix}_HEARTBEAT_INTERVAL", "30000")),
            max_reconnect_attempts=int(os.getenv(f"{prefix}_MAX_RECONNECT_ATTEMPTS", "10")),
            reconnect_interval=int(os.getenv(f"{prefix}_RECONNECT_INTERVAL", "1000")),
            request_timeout=int(os.getenv(f"{prefix}_REQUEST_TIMEOUT", "10000")),
        )

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "BotConfig":
        """从字典创建 BotConfig"""
        return BotConfig(
            name=data.get("name", ""),
            bot_id=data.get("bot_id", ""),
            secret=data.get("secret", ""),
            ws_url=data.get("ws_url", "wss://openws.work.weixin.qq.com"),
            heartbeat_interval=data.get("heartbeat_interval", 30000),
            max_reconnect_attempts=data.get("max_reconnect_attempts", 10),
            reconnect_interval=data.get("reconnect_interval", 1000),
            request_timeout=data.get("request_timeout", 10000),
        )


@dataclass
class BotStatus:
    """机器人运行状态"""

    # 机器人名称
    name: str
    # 是否已连接
    connected: bool = False
    # 是否已认证
    authenticated: bool = False
    # 重连次数
    reconnect_count: int = 0
    # 最后错误信息
    last_error: str | None = None
