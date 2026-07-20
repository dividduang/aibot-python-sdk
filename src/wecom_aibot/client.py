"""
WebSocket 客户端
企业微信智能机器人 Python SDK 主入口
"""

from __future__ import annotations
import asyncio
import base64
import hashlib
import math
from typing import Any, Literal
from pyee.asyncio import AsyncIOEventEmitter

from wecom_aibot.types import (
    WSClientOptions,
    WsFrame,
    WsFrameHeaders,
    Logger,
    TemplateCard,
    StreamReplyBody,
    ReplyMsgItem,
    ReplyFeedback,
    WelcomeTextReplyBody,
    WelcomeTemplateCardReplyBody,
    SendMarkdownMsgBody,
    SendTemplateCardMsgBody,
    # 媒体上传类型
    WeComMediaType,
    VideoOptions,
    UploadMediaOptions,
    UploadMediaFinishResult,
)
from wecom_aibot.types.api import WsCmd
from wecom_aibot.ws_manager import WsConnectionManager
from wecom_aibot.api_client import WeComApiClient
from wecom_aibot.message_handler import MessageHandler
from wecom_aibot.logger import DefaultLogger
from wecom_aibot.utils import generate_req_id
from wecom_aibot.exceptions import (
    UploadError,
    UploadInitError,
    UploadFinishError,
    ChunkUploadError,
)


class WSClient(AsyncIOEventEmitter):
    """
    WebSocket 客户端

    企业微信智能机器人 SDK 主入口，提供：
    - WebSocket 长连接管理
    - 消息接收与事件分发
    - 流式回复
    - 模板卡片消息
    - 文件下载与解密
    """

    def __init__(self, options: WSClientOptions):
        """
        初始化客户端

        Args:
            options: 配置选项，包含 bot_id、secret 等
        """
        super().__init__()

        self._options = options
        self._logger = options.logger or DefaultLogger()
        self._started = False

        # 初始化组件
        self._api_client = WeComApiClient(
            logger=self._logger,
            timeout=options.request_timeout,
        )
        self._ws_manager = WsConnectionManager(
            logger=self._logger,
            heartbeat_interval=options.heartbeat_interval,
            reconnect_base_delay=options.reconnect_interval,
            max_reconnect_attempts=options.max_reconnect_attempts,
            ws_url=options.ws_url,
        )
        self._message_handler = MessageHandler(logger=self._logger)

        # 设置凭证
        self._ws_manager.set_credentials(options.bot_id, options.secret)

        # 设置 WebSocket 事件回调
        self._setup_ws_events()

    def _setup_ws_events(self) -> None:
        """设置 WebSocket 事件处理"""

        def on_connected():
            self._logger.info("WebSocket 已连接")
            self.emit("connected")

        def on_authenticated():
            self._logger.info("认证成功")
            self.emit("authenticated")

        def on_disconnected(reason: str):
            self._logger.info(f"连接断开: {reason}")
            self.emit("disconnected", reason)

        def on_message(frame: WsFrame):
            self._message_handler.handle_frame(frame, self)

        def on_reconnecting(attempt: int):
            self._logger.info(f"正在重连，第 {attempt} 次")
            self.emit("reconnecting", attempt)

        def on_error(error: Exception):
            self._logger.error(f"发生错误: {error}")
            self.emit("error", error)

        self._ws_manager.on_connected = on_connected
        self._ws_manager.on_authenticated = on_authenticated
        self._ws_manager.on_disconnected = on_disconnected
        self._ws_manager.on_message = on_message
        self._ws_manager.on_reconnecting = on_reconnecting
        self._ws_manager.on_error = on_error

    def connect(self) -> "WSClient":
        """
        建立 WebSocket 长连接

        SDK 使用内置默认地址建立连接，连接成功后自动发送认证帧（botId + secret）。
        支持链式调用：wsClient.connect().on('message', handler)

        Returns:
            返回 self，支持链式调用
        """
        if self._started:
            self._logger.warn("客户端已启动，跳过重复连接")
            return self

        self._started = True
        asyncio.create_task(self._ws_manager.connect())
        return self

    async def disconnect(self) -> None:
        """断开 WebSocket 连接"""
        self._started = False
        await self._ws_manager.disconnect()
        await self._api_client.close()

    async def reply(
        self,
        frame: WsFrameHeaders,
        body: dict[str, Any] | StreamReplyBody,
        cmd: str = WsCmd.RESPONSE,
    ) -> WsFrame:
        """
        通过 WebSocket 通道发送回复消息（通用方法）

        Args:
            frame: 收到的原始 WebSocket 帧，透传 headers.req_id
            body: 回复消息体
            cmd: 命令类型

        Returns:
            回执帧
        """
        req_id = frame.headers.get("req_id", "")
        if isinstance(body, StreamReplyBody):
            body_data = {"msgtype": body.msgtype, "stream": body.stream}
            # 调试：检查 stream 中是否有 msg_item
            if "msg_item" in body.stream:
                self._logger.debug(f"[SEND] stream 包含 msg_item, 数量: {len(body.stream['msg_item'])}")
                for i, item in enumerate(body.stream['msg_item']):
                    self._logger.debug(f"[SEND] msg_item[{i}]: {list(item.keys())}")
                    if 'image' in item:
                        img = item['image']
                        self._logger.debug(f"[SEND]   image keys: {list(img.keys()) if isinstance(img, dict) else type(img)}")
                        if isinstance(img, dict) and 'base64' in img:
                            self._logger.debug(f"[SEND]   base64 长度: {len(img['base64'])}, md5 前16位: {img.get('md5', 'N/A')[:16]}")
        else:
            body_data = body

        return await self._ws_manager.send_reply(req_id, body_data, cmd)

    async def reply_stream(
        self,
        frame: WsFrameHeaders,
        stream_id: str,
        content: str,
        finish: bool = False,
        msg_item: list[ReplyMsgItem] | None = None,
        feedback: ReplyFeedback | None = None,
    ) -> WsFrame:
        """
        发送流式文本回复（便捷方法）

        Args:
            frame: 收到的原始 WebSocket 帧，透传 headers.req_id
            stream_id: 流式消息 ID
            content: 回复内容（支持 Markdown）
            finish: 是否结束流式消息，默认 False
            msg_item: 图文混排项（仅在 finish=True 时有效），用于在结束时附带图片内容
            feedback: 反馈信息（仅在首次回复时设置）

        Returns:
            回执帧
        """
        body = StreamReplyBody.create(
            stream_id=stream_id,
            content=content,
            finish=finish,
            msg_item=msg_item,
            feedback=feedback,
        )
        return await self.reply(frame, body)

    async def reply_welcome(
        self,
        frame: WsFrameHeaders,
        body: WelcomeTextReplyBody | WelcomeTemplateCardReplyBody,
    ) -> WsFrame:
        """
        发送欢迎语回复

        注意：此方法需要使用对应事件（如 enter_chat）的 req_id 才能调用，
        即 frame 参数应来自触发欢迎语的事件帧。
        收到事件回调后需在 5 秒内发送回复，超时将无法发送欢迎语。

        Args:
            frame: 对应事件的 WebSocket 帧（需包含该事件的 req_id）
            body: 欢迎语消息体（支持文本或模板卡片格式）

        Returns:
            回执帧
        """
        if isinstance(body, WelcomeTextReplyBody):
            body_data = {"msgtype": body.msgtype, "text": body.text}
        else:
            body_data = {
                "msgtype": body.msgtype,
                "template_card": self._template_card_to_dict(body.template_card),
            }

        return await self.reply(frame, body_data, WsCmd.RESPONSE_WELCOME)

    async def reply_template_card(
        self,
        frame: WsFrameHeaders,
        template_card: TemplateCard,
        feedback: ReplyFeedback | None = None,
    ) -> WsFrame:
        """
        回复模板卡片消息

        收到消息回调或进入会话事件后，可使用此方法回复模板卡片消息。

        Args:
            frame: 收到的原始 WebSocket 帧，透传 headers.req_id
            template_card: 模板卡片内容
            feedback: 反馈信息

        Returns:
            回执帧
        """
        body: dict[str, Any] = {
            "msgtype": "template_card",
            "template_card": self._template_card_to_dict(template_card),
        }
        if feedback:
            body["template_card"]["feedback"] = {"id": feedback.id}

        return await self.reply(frame, body)

    async def reply_stream_with_card(
        self,
        frame: WsFrameHeaders,
        stream_id: str,
        content: str,
        finish: bool = False,
        msg_item: list[ReplyMsgItem] | None = None,
        stream_feedback: ReplyFeedback | None = None,
        template_card: TemplateCard | None = None,
        card_feedback: ReplyFeedback | None = None,
    ) -> WsFrame:
        """
        发送流式消息 + 模板卡片组合回复

        首次回复时必须返回 stream 的 id。
        template_card 可首次回复，也可在后续回复中发送，但同一个消息只能回复一次。

        Args:
            frame: 收到的原始 WebSocket 帧，透传 headers.req_id
            stream_id: 流式消息 ID
            content: 回复内容（支持 Markdown）
            finish: 是否结束流式消息，默认 False
            msg_item: 图文混排项（仅在 finish=True 时有效）
            stream_feedback: 流式消息反馈信息（首次回复时设置）
            template_card: 模板卡片内容（同一消息只能回复一次）
            card_feedback: 模板卡片反馈信息

        Returns:
            回执帧
        """
        body: dict[str, Any] = {
            "msgtype": "stream_with_template_card",
            "stream": {
                "id": stream_id,
                "content": content,
            },
        }

        if finish:
            body["stream"]["finish"] = True
        if msg_item:
            # 序列化 msg_item，确保图片数据正确
            serialized_items = []
            for item in msg_item:
                item_dict = {"msgtype": item.msgtype}
                if hasattr(item, 'image') and item.image:
                    # 确保 image 是字典格式
                    if hasattr(item.image, '__dict__'):
                        item_dict["image"] = item.image.__dict__
                    else:
                        item_dict["image"] = item.image
                serialized_items.append(item_dict)
            body["stream"]["msg_item"] = serialized_items
            self._logger.debug(f"msg_item 序列化结果: msgtype={serialized_items[0]['msgtype']}, image_keys={list(serialized_items[0].get('image', {}).keys())}")
        if stream_feedback:
            body["stream"]["feedback"] = {"id": stream_feedback.id}

        if template_card:
            card_dict = self._template_card_to_dict(template_card)
            if card_feedback:
                card_dict["feedback"] = {"id": card_feedback.id}
            body["template_card"] = card_dict

        return await self.reply(frame, body)

    async def update_template_card(
        self,
        frame: WsFrameHeaders,
        template_card: TemplateCard,
        userids: list[str] | None = None,
    ) -> WsFrame:
        """
        更新模板卡片

        注意：此方法需要使用对应事件（template_card_event）的 req_id 才能调用，
        即 frame 参数应来自触发更新的事件帧。
        收到事件回调后需在 5 秒内发送回复，超时将无法更新卡片。

        Args:
            frame: 对应事件的 WebSocket 帧（需包含该事件的 req_id）
            template_card: 模板卡片内容（task_id 需跟回调收到的 task_id 一致）
            userids: 要替换模版卡片消息的 userid 列表，若不填则替换所有用户

        Returns:
            回执帧
        """
        body: dict[str, Any] = {
            "response_type": "update_template_card",
            "template_card": self._template_card_to_dict(template_card),
        }
        if userids:
            body["userids"] = userids

        return await self.reply(frame, body, WsCmd.RESPONSE_UPDATE)

    async def send_message(
        self,
        chatid: str,
        body: SendMarkdownMsgBody | SendTemplateCardMsgBody,
    ) -> WsFrame:
        """
        主动发送消息

        向指定会话（单聊或群聊）主动推送消息，无需依赖收到的回调帧。

        Args:
            chatid: 会话 ID，单聊填用户的 userid，群聊填对应群聊的 chatid
            body: 消息体（支持 markdown 或 template_card 格式）

        Returns:
            回执帧

        Example:
            ```python
            # 发送 markdown 消息
            await ws_client.send_message('CHATID', SendMarkdownMsgBody.create('这是一条**主动推送**的消息'))

            # 发送模板卡片消息
            card = TemplateCard(card_type='text_notice', ...)
            await ws_client.send_message('CHATID', SendTemplateCardMsgBody(template_card=card))
            ```
        """
        if isinstance(body, SendMarkdownMsgBody):
            body_data = {"msgtype": body.msgtype, "markdown": body.markdown}
        else:
            body_data = {
                "msgtype": body.msgtype,
                "template_card": self._template_card_to_dict(body.template_card),
            }

        req_id = generate_req_id("send")
        frame: dict[str, Any] = {
            "cmd": WsCmd.SEND_MSG,
            "headers": {"req_id": req_id},
            "body": {"chatid": chatid, **body_data},
        }

        return await self._ws_manager.send_reply(req_id, frame["body"], WsCmd.SEND_MSG)

    async def download_file(self, url: str, aes_key: str | None = None) -> tuple[bytes, str | None]:
        """
        下载文件并使用 AES 密钥解密

        Args:
            url: 文件下载地址
            aes_key: AES 解密密钥（Base64 编码），取自消息中 image.aeskey 或 file.aeskey 字段

        Returns:
            (解密后的文件内容, 文件名) 元组

        Example:
            ```python
            # aes_key 来自消息体中的 image.aeskey 或 file.aeskey
            buffer, filename = await ws_client.download_file(image_url, body.image.aeskey)
            ```
        """
        return await self._api_client.download_file(url, aes_key)

    async def uploadMedia(
        self,
        file_bytes: bytes,
        options: UploadMediaOptions,
    ) -> UploadMediaFinishResult:
        """
        上传临时素材（三步分片上传）

        通过 WebSocket 长连接执行分片上传：init → chunk × N → finish

        Args:
            file_bytes: 文件字节数据
            options: 上传选项（类型、文件名）

        Returns:
            上传结果，包含 media_id（3天内有效）

        Raises:
            UploadInitError: 上传初始化失败
            ChunkUploadError: 分片上传失败
            UploadFinishError: 上传完成失败
            UploadError: 其他上传失败
        """
        total_size = len(file_bytes)

        # 分片大小：512KB（Base64 编码前）
        CHUNK_SIZE = 512 * 1024
        total_chunks = math.ceil(total_size / CHUNK_SIZE) if total_size > 0 else 0

        if total_chunks > 100:
            raise UploadError(f"File too large: {total_chunks} chunks exceeds maximum of 100 chunks (max ~50MB)")

        # 计算文件 MD5
        md5 = hashlib.md5(file_bytes).hexdigest()

        self._logger.info(f"Uploading media: type={options.type}, filename={options.filename}, size={total_size}, chunks={total_chunks}")

        # Step 1: 初始化上传
        init_req_id = generate_req_id("upload_init")
        init_result = await self._ws_manager.send_reply(
            init_req_id,
            {
                "type": options.type,
                "filename": options.filename,
                "total_size": total_size,
                "total_chunks": total_chunks,
                "md5": md5,
            },
            WsCmd.UPLOAD_MEDIA_INIT,
        )

        upload_id = init_result.body.get("upload_id") if init_result.body else None
        if not upload_id:
            raise UploadInitError(f"Upload init failed: no upload_id returned. Response: {init_result}")

        self._logger.info(f"Upload init success: upload_id={upload_id}")

        # Step 2: 分片上传（带重试，根据分片数动态调整并发）
        MAX_CHUNK_RETRIES = 2
        # 动态并发数：1~4分片全并发，5~10分片并发3，>10分片并发2
        if total_chunks <= 4:
            MAX_CONCURRENCY = total_chunks
        elif total_chunks <= 10:
            MAX_CONCURRENCY = 3
        else:
            MAX_CONCURRENCY = 2

        async def upload_chunk(chunk_index: int) -> None:
            start = chunk_index * CHUNK_SIZE
            end = min(start + CHUNK_SIZE, total_size)
            chunk = file_bytes[start:end]
            base64_data = base64.b64encode(chunk).decode("utf-8")

            last_error = None
            for attempt in range(MAX_CHUNK_RETRIES + 1):
                try:
                    chunk_req_id = generate_req_id("upload_chunk")
                    await self._ws_manager.send_reply(
                        chunk_req_id,
                        {
                            "upload_id": upload_id,
                            "chunk_index": chunk_index,
                            "base64_data": base64_data,
                        },
                        WsCmd.UPLOAD_MEDIA_CHUNK,
                    )
                    self._logger.debug(f"Uploaded chunk {chunk_index + 1}/{total_chunks} ({len(chunk)} bytes)")
                    return
                except Exception as err:
                    last_error = err
                    if attempt < MAX_CHUNK_RETRIES:
                        delay = 500 * (attempt + 1)
                        self._logger.warn(
                            f"Chunk {chunk_index} upload failed (attempt {attempt + 1}/{MAX_CHUNK_RETRIES + 1}), "
                            f"retrying in {delay}ms... error: {err}"
                        )
                        await asyncio.sleep(delay / 1000)

            raise ChunkUploadError(
                chunk_index=chunk_index,
                attempts=MAX_CHUNK_RETRIES + 1,
                message=str(last_error) if last_error else "Unknown error",
            )

        self._logger.debug(f"Upload concurrency: {MAX_CONCURRENCY} workers for {total_chunks} chunks")

        if total_chunks <= 1:
            # 单分片直接上传
            await upload_chunk(0)
        else:
            # 多分片并发上传
            next_index = 0
            errors: list[Exception] = []

            async def run_worker() -> None:
                nonlocal next_index
                while next_index < total_chunks:
                    idx = next_index
                    next_index += 1
                    try:
                        await upload_chunk(idx)
                    except Exception as err:
                        errors.append(err)

            worker_count = min(MAX_CONCURRENCY, total_chunks)
            await asyncio.gather(*[run_worker() for _ in range(worker_count)])

            if errors:
                raise UploadError(f"Upload failed: {len(errors)} chunk(s) failed. First error: {errors[0]}")

        self._logger.info(f"All {total_chunks} chunks uploaded, finishing...")

        # Step 3: 完成上传
        finish_req_id = generate_req_id("upload_finish")
        finish_result = await self._ws_manager.send_reply(
            finish_req_id,
            {"upload_id": upload_id},
            WsCmd.UPLOAD_MEDIA_FINISH,
        )

        media_id = finish_result.body.get("media_id") if finish_result.body else None
        if not media_id:
            raise UploadFinishError(f"Upload finish failed: no media_id returned. Response: {finish_result}")

        self._logger.info(f"Upload complete: media_id={media_id}, type={finish_result.body.get('type')}")

        return UploadMediaFinishResult.from_response(finish_result.body)

    async def replyMedia(
        self,
        frame: WsFrameHeaders,
        media_type: WeComMediaType,
        media_id: str,
        video_options: VideoOptions | None = None,
    ) -> WsFrame:
        """
        被动回复媒体消息

        通过 aibot_respond_msg 被动回复通道发送媒体消息

        Args:
            frame: 收到的原始 WebSocket 帧
            media_type: 媒体类型（file/image/voice/video）
            media_id: 临时素材 media_id
            video_options: 视频消息可选参数（仅 media_type='video' 时生效）

        Returns:
            回执帧
        """
        media_content: dict[str, Any] = {"media_id": media_id}
        if media_type == "video" and video_options:
            if video_options.title:
                media_content["title"] = video_options.title
            if video_options.description:
                media_content["description"] = video_options.description

        body: dict[str, Any] = {
            "msgtype": media_type,
            media_type: media_content,
        }
        return await self.reply(frame, body)

    async def sendMediaMessage(
        self,
        chatid: str,
        media_type: WeComMediaType,
        media_id: str,
        video_options: VideoOptions | None = None,
    ) -> WsFrame:
        """
        主动发送媒体消息

        通过 aibot_send_msg 主动推送通道发送媒体消息

        Args:
            chatid: 会话 ID（单聊填 userid，群聊填 chatid）
            media_type: 媒体类型（file/image/voice/video）
            media_id: 临时素材 media_id
            video_options: 视频消息可选参数（仅 media_type='video' 时生效）

        Returns:
            回执帧
        """
        media_content: dict[str, Any] = {"media_id": media_id}
        if media_type == "video" and video_options:
            if video_options.title:
                media_content["title"] = video_options.title
            if video_options.description:
                media_content["description"] = video_options.description

        body: dict[str, Any] = {
            "msgtype": media_type,
            media_type: media_content,
        }

        req_id = generate_req_id("send_media")
        full_body = {
            "chatid": chatid,
            **body,
        }
        return await self._ws_manager.send_reply(req_id, full_body, WsCmd.SEND_MSG)

    # Pythonic snake_case aliases（与 Node SDK camelCase 方法等价）
    upload_media = uploadMedia
    reply_media = replyMedia
    send_media_message = sendMediaMessage

    @property
    def is_connected(self) -> bool:
        """获取当前连接状态"""
        return self._ws_manager.is_connected

    @property
    def api(self) -> WeComApiClient:
        """获取 API 客户端实例（供高级用途使用，如文件下载）"""
        return self._api_client

    def _template_card_to_dict(self, card: TemplateCard) -> dict[str, Any]:
        """将 TemplateCard 转换为字典"""
        from dataclasses import asdict

        result: dict[str, Any] = {"card_type": card.card_type}

        # 只添加非 None 的字段
        if card.source:
            result["source"] = {k: v for k, v in asdict(card.source).items() if v is not None}
        if card.action_menu:
            result["action_menu"] = asdict(card.action_menu)
        if card.main_title:
            result["main_title"] = {k: v for k, v in asdict(card.main_title).items() if v is not None}
        if card.emphasis_content:
            result["emphasis_content"] = {k: v for k, v in asdict(card.emphasis_content).items() if v is not None}
        if card.quote_area:
            result["quote_area"] = {k: v for k, v in asdict(card.quote_area).items() if v is not None}
        if card.sub_title_text:
            result["sub_title_text"] = card.sub_title_text
        if card.horizontal_content_list:
            result["horizontal_content_list"] = [
                {k: v for k, v in asdict(item).items() if v is not None} for item in card.horizontal_content_list
            ]
        if card.jump_list:
            result["jump_list"] = [{k: v for k, v in asdict(item).items() if v is not None} for item in card.jump_list]
        if card.card_action:
            result["card_action"] = {k: v for k, v in asdict(card.card_action).items() if v is not None}
        if card.card_image:
            result["card_image"] = {k: v for k, v in asdict(card.card_image).items() if v is not None}
        if card.image_text_area:
            result["image_text_area"] = {k: v for k, v in asdict(card.image_text_area).items() if v is not None}
        if card.vertical_content_list:
            result["vertical_content_list"] = [asdict(item) for item in card.vertical_content_list]
        if card.button_selection:
            result["button_selection"] = {k: v for k, v in asdict(card.button_selection).items() if v is not None}
        if card.button_list:
            result["button_list"] = [asdict(item) for item in card.button_list]
        if card.checkbox:
            result["checkbox"] = {k: v for k, v in asdict(card.checkbox).items() if v is not None}
        if card.select_list:
            result["select_list"] = [{k: v for k, v in asdict(item).items() if v is not None} for item in card.select_list]
        if card.submit_button:
            result["submit_button"] = asdict(card.submit_button)
        if card.task_id:
            result["task_id"] = card.task_id
        if card.feedback:
            result["feedback"] = card.feedback

        return result
