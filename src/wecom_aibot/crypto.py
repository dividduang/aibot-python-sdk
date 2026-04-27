"""
企业微信加解密通用核心

提供：
- 消息加解密（AES-256-CBC + PKCS#7）
- SHA1 签名计算与验证
- 文件解密
"""

from __future__ import annotations

import base64
import hashlib
import os
import struct
from typing import Optional

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

_PKCS7_BLOCK_SIZE = 32
_AES_KEY_LENGTH = 32

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def decode_encoding_aes_key(encoding_aes_key: str) -> bytes:
    """解码企业微信提供的 Base64 EncodingAESKey（尾部补 '=' 后解码）。"""
    trimmed = encoding_aes_key.strip()
    if not trimmed:
        raise ValueError("encodingAESKey is required")
    with_padding = trimmed if trimmed.endswith("=") else trimmed + "="
    key = base64.b64decode(with_padding)
    if len(key) != _AES_KEY_LENGTH:
        raise ValueError(
            f"invalid encodingAESKey (expected {_AES_KEY_LENGTH} bytes, got {len(key)})"
        )
    return key


def pkcs7_pad(data: bytes, block_size: int = _PKCS7_BLOCK_SIZE) -> bytes:
    """PKCS#7 填充。"""
    return pad(data, block_size)


def pkcs7_unpad(data: bytes, block_size: int = _PKCS7_BLOCK_SIZE) -> bytes:
    """PKCS#7 去除填充。"""
    return unpad(data, block_size)


# ---------------------------------------------------------------------------
# 文件解密（保持向后兼容）
# ---------------------------------------------------------------------------


def decrypt_file(encrypted_buffer: bytes, aes_key: str) -> bytes:
    """
    使用 AES-256-CBC 解密文件

    Args:
        encrypted_buffer: 加密的文件数据
        aes_key: Base64 编码的 AES-256 密钥

    Returns:
        解密后的文件 bytes

    Raises:
        ValueError: 密钥格式错误
    """
    try:
        key = base64.b64decode(aes_key)
    except Exception as e:
        raise ValueError(f"无效的 AES 密钥格式: {e}")

    if len(key) != _AES_KEY_LENGTH:
        raise ValueError(f"AES-256 密钥长度应为 32 字节，实际为 {len(key)} 字节")

    iv = key[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted_buffer)
    try:
        decrypted = unpad(decrypted, AES.block_size)
    except ValueError:
        pass

    return decrypted


# ---------------------------------------------------------------------------
# WecomCrypto — 消息加解密 & 签名
# ---------------------------------------------------------------------------


class WecomCrypto:
    """企业微信消息加解密与签名工具。

    独立于 Webhook、WebSocket、Agent 的具体协议形态，统一提供基于
    AES-256-CBC 的加解密与 SHA1 签名计算能力。

    Args:
        token: 消息校验 Token
        encoding_aes_key: 后台配置的 EncodingAESKey
        receive_id: corpId 或 botId（用于校验与追加）
    """

    def __init__(
        self,
        token: str,
        encoding_aes_key: str,
        receive_id: Optional[str] = None,
    ) -> None:
        if not token:
            raise ValueError("token is required")
        self.token = token
        self.receive_id = receive_id or ""
        self._aes_key = decode_encoding_aes_key(encoding_aes_key)
        self._iv = self._aes_key[:16]

    # -- 签名 ------------------------------------------------------------

    def compute_signature(
        self, timestamp: str, nonce: str, encrypt: str
    ) -> str:
        """计算企业微信消息签名。"""
        parts = sorted([self.token, str(timestamp), str(nonce), str(encrypt)])
        return hashlib.sha1("".join(parts).encode("utf-8")).hexdigest()

    def verify_signature(
        self, signature: str, timestamp: str, nonce: str, encrypt: str
    ) -> bool:
        """验证企业微信消息签名。"""
        return self.compute_signature(timestamp, nonce, encrypt) == signature

    # -- 解密 ------------------------------------------------------------

    def decrypt(self, encrypt_text: str) -> str:
        """解密消息，返回纯文本字符串（XML 或 JSON）。

        密文格式：Base64(AES(random_16 + msg_len_4 + msg + receive_id))
        """
        cipher = AES.new(self._aes_key, AES.MODE_CBC, self._iv)
        decrypted_padded = cipher.decrypt(base64.b64decode(encrypt_text))
        decrypted = pkcs7_unpad(decrypted_padded, _PKCS7_BLOCK_SIZE)

        if len(decrypted) < 20:
            raise ValueError(
                f"invalid payload (expected >=20 bytes, got {len(decrypted)})"
            )

        # 16 bytes random + 4 bytes msg length + msg + receive_id
        msg_len = struct.unpack(">I", decrypted[16:20])[0]
        msg_start = 20
        msg_end = msg_start + msg_len
        if msg_end > len(decrypted):
            raise ValueError(
                f"invalid msg length (msgEnd={msg_end}, total={len(decrypted)})"
            )

        msg = decrypted[msg_start:msg_end].decode("utf-8")

        if self.receive_id:
            trailing = decrypted[msg_end:].decode("utf-8")
            if trailing != self.receive_id:
                raise ValueError(
                    f'receiveId mismatch (expected "{self.receive_id}", '
                    f'got "{trailing}")'
                )

        return msg

    # -- 加密 ------------------------------------------------------------

    def encrypt(
        self, plain_text: str, timestamp: str, nonce: str
    ) -> tuple[str, str]:
        """加密明文消息。

        Returns:
            (encrypt_base64, signature) 元组
        """
        random_16 = os.urandom(16)
        msg_buf = (plain_text or "").encode("utf-8")
        msg_len = struct.pack(">I", len(msg_buf))
        receive_id_buf = self.receive_id.encode("utf-8")

        raw = random_16 + msg_len + msg_buf + receive_id_buf
        padded = pkcs7_pad(raw, _PKCS7_BLOCK_SIZE)

        cipher = AES.new(self._aes_key, AES.MODE_CBC, self._iv)
        encrypted = cipher.encrypt(padded)
        encrypt_base64 = base64.b64encode(encrypted).decode("utf-8")

        signature = self.compute_signature(timestamp, nonce, encrypt_base64)
        return encrypt_base64, signature
