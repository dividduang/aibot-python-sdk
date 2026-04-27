"""
媒体上传示例

演示如何使用 uploadMedia、replyMedia、sendMediaMessage 方法
"""

import asyncio
from wecom_aibot import WSClient, WSClientOptions
from wecom_aibot.types import UploadMediaOptions, VideoOptions


async def main():
    # 创建客户端
    client = WSClient(WSClientOptions(
        bot_id="your-bot-id",
        secret="your-secret",
    ))

    # 连接
    client.connect()

    @client.on("message.text")
    async def on_text(frame):
        """收到文本消息时，上传图片并回复"""
        try:
            # 读取本地图片文件
            with open("response_image.png", "rb") as f:
                file_bytes = f.read()

            # 上传图片
            result = await client.uploadMedia(file_bytes, UploadMediaOptions(
                type="image",
                filename="response_image.png",
            ))

            print(f"上传成功，media_id: {result.media_id}")

            # 被动回复图片
            await client.replyMedia(frame, "image", result.media_id)

        except FileNotFoundError:
            print("未找到 response_image.png 文件，跳过图片回复")
        except Exception as e:
            print(f"上传/回复失败: {e}")

    @client.on("message.file")
    async def on_file(frame):
        """收到文件消息时，回复文件"""
        try:
            # 读取本地文件
            with open("report.pdf", "rb") as f:
                file_bytes = f.read()

            # 上传文件
            result = await client.uploadMedia(file_bytes, UploadMediaOptions(
                type="file",
                filename="report.pdf",
            ))

            # 被动回复文件
            await client.replyMedia(frame, "file", result.media_id)

        except FileNotFoundError:
            print("未找到 report.pdf 文件")
        except Exception as e:
            print(f"文件上传失败: {e}")

    @client.on("authenticated")
    async def on_auth():
        """认证成功后，主动发送媒体消息示例"""
        print("认证成功，可以主动发送媒体消息")

        # 示例：主动发送文件
        # try:
        #     with open("report.pdf", "rb") as f:
        #         result = await client.uploadMedia(f.read(), UploadMediaOptions(
        #             type="file",
        #             filename="report.pdf",
        #         ))
        #
        #     # 主动发送给指定用户
        #     await client.sendMediaMessage("target_userid", "file", result.media_id)
        # except Exception as e:
        #     print(f"发送失败: {e}")

        # 示例：主动发送视频（带标题描述）
        # try:
        #     with open("demo.mp4", "rb") as f:
        #         video_result = await client.uploadMedia(f.read(), UploadMediaOptions(
        #             type="video",
        #             filename="demo.mp4",
        #         ))
        #
        #     await client.sendMediaMessage(
        #         "target_userid",
        #         "video",
        #         video_result.media_id,
        #         video_options=VideoOptions(
        #             title="产品演示",
        #             description="这是一个产品功能演示视频",
        #         ),
        #     )
        # except Exception as e:
        #     print(f"视频发送失败: {e}")

    # 等待退出信号
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
