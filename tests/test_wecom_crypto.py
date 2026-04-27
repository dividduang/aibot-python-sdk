"""WecomCrypto 单元测试 — 对齐 Node.js wecom-crypto 模块"""

import pytest

from wecom_aibot.crypto import (
    WecomCrypto,
    decode_encoding_aes_key,
    pkcs7_pad,
    pkcs7_unpad,
)


# -- fixtures ---------------------------------------------------------------

ENCODING_AES_KEY = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG"
TOKEN = "test_token_abc"


@pytest.fixture
def crypto() -> WecomCrypto:
    return WecomCrypto(TOKEN, ENCODING_AES_KEY, "")


@pytest.fixture
def crypto_with_receive_id() -> WecomCrypto:
    return WecomCrypto(TOKEN, ENCODING_AES_KEY, "corp_id_123")


# -- decodeEncodingAESKey ---------------------------------------------------


class TestDecodeEncodingAESKey:
    def test_valid_key(self):
        key = decode_encoding_aes_key(ENCODING_AES_KEY)
        assert len(key) == 32

    def test_missing_key_raises(self):
        with pytest.raises(ValueError, match="encodingAESKey is required"):
            decode_encoding_aes_key("")

    def test_whitespace_key_raises(self):
        with pytest.raises(ValueError, match="encodingAESKey is required"):
            decode_encoding_aes_key("   ")


# -- PKCS#7 padding ----------------------------------------------------------


class TestPKCS7:
    def test_pad_adds_bytes(self):
        data = b"hello"
        padded = pkcs7_pad(data)
        assert len(padded) % 32 == 0
        assert len(padded) > len(data)

    def test_pad_unpad_roundtrip(self):
        data = b"round trip test data"
        assert pkcs7_unpad(pkcs7_pad(data)) == data

    def test_pad_when_length_is_multiple_of_block_size(self):
        # 32 bytes → should still add a full block of padding
        data = b"x" * 32
        padded = pkcs7_pad(data)
        assert len(padded) == 64
        assert pkcs7_unpad(padded) == data

    def test_invalid_padding_raises(self):
        with pytest.raises(ValueError):
            pkcs7_unpad(b"\x00" * 32)


# -- WecomCrypto: signature --------------------------------------------------


class TestSignature:
    def test_compute_signature_format(self, crypto: WecomCrypto):
        sig = crypto.compute_signature("123", "456", "ENCRYPT")
        assert len(sig) == 40
        assert all(c in "0123456789abcdef" for c in sig)

    def test_verify_signature_correct(self, crypto: WecomCrypto):
        sig = crypto.compute_signature("123", "456", "ENCRYPT")
        assert crypto.verify_signature(sig, "123", "456", "ENCRYPT") is True

    def test_verify_signature_wrong(self, crypto: WecomCrypto):
        assert crypto.verify_signature("bad", "123", "456", "ENCRYPT") is False

    def test_signature_changes_with_encrypt(self, crypto: WecomCrypto):
        """不同 encrypt 值应产生不同签名"""
        sig1 = crypto.compute_signature("123", "456", "encrypt_a")
        sig2 = crypto.compute_signature("123", "456", "encrypt_b")
        assert sig1 != sig2


# -- WecomCrypto: encrypt / decrypt round-trip ------------------------------


class TestEncryptDecrypt:
    def test_round_trip_json(self, crypto: WecomCrypto):
        plaintext = '{"hello":"world"}'
        encrypt, sig = crypto.encrypt(plaintext, "123", "456")
        assert crypto.verify_signature(sig, "123", "456", encrypt)
        assert crypto.decrypt(encrypt) == plaintext

    def test_round_trip_xml(self, crypto: WecomCrypto):
        plaintext = "<xml><content>test</content></xml>"
        encrypt, sig = crypto.encrypt(plaintext, "999", "abc")
        assert crypto.verify_signature(sig, "999", "abc", encrypt)
        assert crypto.decrypt(encrypt) == plaintext

    def test_round_trip_exact_block_size(self, crypto: WecomCrypto):
        # 明文恰好使 raw 长度为 32 的倍数
        plaintext = "x" * 12
        encrypt, _ = crypto.encrypt(plaintext, "123", "456")
        assert crypto.decrypt(encrypt) == plaintext

    def test_round_trip_with_receive_id(self, crypto_with_receive_id: WecomCrypto):
        plaintext = "hello with receive_id"
        encrypt, sig = crypto_with_receive_id.encrypt(plaintext, "1", "2")
        assert crypto_with_receive_id.verify_signature(sig, "1", "2", encrypt)
        assert crypto_with_receive_id.decrypt(encrypt) == plaintext

    def test_receive_id_mismatch_raises(self, crypto_with_receive_id: WecomCrypto):
        plaintext = "hello"
        encrypt, _ = crypto_with_receive_id.encrypt(plaintext, "1", "2")
        # 用不同的 receive_id 创建实例
        wrong = WecomCrypto(TOKEN, ENCODING_AES_KEY, "wrong_corp_id")
        with pytest.raises(ValueError, match="receiveId mismatch"):
            wrong.decrypt(encrypt)

    def test_empty_plaintext(self, crypto: WecomCrypto):
        plaintext = ""
        encrypt, sig = crypto.encrypt(plaintext, "1", "2")
        assert crypto.decrypt(encrypt) == plaintext


# -- WecomCrypto: constructor validation ------------------------------------


class TestConstructor:
    def test_missing_token_raises(self):
        with pytest.raises(ValueError, match="token is required"):
            WecomCrypto("", ENCODING_AES_KEY)

    def test_invalid_encoding_aes_key_raises(self):
        with pytest.raises(ValueError, match="invalid encodingAESKey"):
            WecomCrypto("token", "short_key")
