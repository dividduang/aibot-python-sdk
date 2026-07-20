"""默认日志实现"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any


class DefaultLogger:
    """
    默认日志实现
    带有日志级别和时间戳的控制台日志
    """

    def __init__(self, prefix: str = "[WeComAIBot]"):
        self.prefix = prefix

    def _format_time(self) -> str:
        """格式化时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _log(self, level: str, message: str, *args: Any) -> None:
        """统一日志输出（兼容 Windows GBK 控制台）"""
        formatted_args = " ".join(str(arg) for arg in args) if args else ""
        line = f"{self.prefix} [{self._format_time()}] [{level}] {message} {formatted_args}"
        try:
            print(line)
        except UnicodeEncodeError:
            # 控制台编码无法输出部分字符时降级为 replace
            encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
            safe = line.encode(encoding, errors="replace").decode(encoding, errors="replace")
            print(safe)

    def debug(self, message: str, *args: Any) -> None:
        """调试级别日志"""
        self._log("DEBUG", message, *args)

    def info(self, message: str, *args: Any) -> None:
        """信息级别日志"""
        self._log("INFO", message, *args)

    def warn(self, message: str, *args: Any) -> None:
        """警告级别日志"""
        self._log("WARN", message, *args)

    def error(self, message: str, *args: Any) -> None:
        """错误级别日志"""
        self._log("ERROR", message, *args)
