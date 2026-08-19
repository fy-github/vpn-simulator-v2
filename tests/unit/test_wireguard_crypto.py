"""Tests for the WireGuard Noise_IKpsk2 crypto module (real curves)."""

from __future__ import annotations

import pytest
from cryptography.exceptions import InvalidTag
from vpn_simulator.plugins.protocols.wireguard.crypto import (
    INITIATION_LEN,
    RESPONSE_LEN,
    ChaCha20Poly1305,
    WireGuardIdentity,
    b64_to_key,
    build_initiation,
    build_response,
    finish_initiator,
    finish_responder,
    key_to_b64,
    parse_initiation,
)


@pytest.fixture
def identities() -> tuple[WireGuardIdentity, WireGuardIdentity]:
    return WireGuardIdentity.generate(), WireGuardIdentity.generate()


@pytest.fixture
def handshake(identities):
    initiator, responder = identities
    init_msg, init_hs = build_initiation(initiator, responder.public_bytes, 0x11223344)
    parsed = parse_initiation(responder, init_msg)
    resp_msg, resp_state = build_response(
        responder, parsed, sender_index=0x55667788, receiver_index=0x11223344
    )
    return initiator, responder, init_hs, resp_msg, resp_state


def test_message_sizes(identities):
    initiator, responder = identities
    init_msg, _ = build_initiation(initiator, responder.public_bytes, 1)
    assert len(init_msg) == INITIATION_LEN == 148

    parsed = parse_initiation(responder, init_msg)
    resp_msg, _ = build_response(responder, parsed, 2, 1)
    assert len(resp_msg) == RESPONSE_LEN == 92


def test_initiation_recovers_initiator_static_key(identities):
    initiator, responder = identities
    init_msg, _ = build_initiation(initiator, responder.public_bytes, 1)
    parsed = parse_initiation(responder, init_msg)
    assert parsed.initiator_static == initiator.public_bytes


def test_handshake_derives_matching_transport_keys(handshake):
    initiator, _responder, init_hs, resp_msg, resp_state = handshake
    init_send, init_recv = finish_initiator(init_hs, resp_msg)
    resp_recv, resp_send = finish_responder(resp_state)

    assert init_send == resp_recv
    assert init_recv == resp_send
    assert init_send != init_recv


def test_transport_aead_round_trip(handshake):
    _initiator, _responder, init_hs, resp_msg, resp_state = handshake
    init_send, _init_recv = finish_initiator(init_hs, resp_msg)
    _resp_recv, _resp_send = finish_responder(resp_state)

    # 响应方接收侧用同一密钥解密发起方发送的密文
    nonce = b"\x00" * 12
    aad = b"transport"
    plaintext = b"hello wireguard"
    ciphertext = ChaCha20Poly1305(init_send).encrypt(nonce, plaintext, aad)
    assert ChaCha20Poly1305(init_send).decrypt(nonce, ciphertext, aad) == plaintext


def test_tampered_initiation_rejected(identities):
    initiator, responder = identities
    init_msg, _ = build_initiation(initiator, responder.public_bytes, 1)

    tampered = bytearray(init_msg)
    tampered[40] ^= 0xFF  # 翻转 encrypted_static 的第一个字节
    with pytest.raises(InvalidTag):
        parse_initiation(responder, bytes(tampered))


def test_wrong_responder_cannot_decrypt(identities):
    initiator, responder = identities
    other = WireGuardIdentity.generate()
    init_msg, _ = build_initiation(initiator, responder.public_bytes, 1)
    with pytest.raises(InvalidTag):
        parse_initiation(other, init_msg)


def test_key_base64_round_trip():
    raw = b"\x00\x01\x02" * 11
    assert b64_to_key(key_to_b64(raw)) == raw


def test_handshake_is_nondeterministic(identities):
    """每次握手使用新临时密钥，传输密钥应不同。"""
    initiator, responder = identities
    keys = set()
    for _ in range(3):
        init_msg, init_hs = build_initiation(initiator, responder.public_bytes, 1)
        parsed = parse_initiation(responder, init_msg)
        resp_msg, resp_state = build_response(responder, parsed, 2, 1)
        send, recv = finish_initiator(init_hs, resp_msg)
        _resp_recv, _resp_send = finish_responder(resp_state)
        keys.add(send)
        keys.add(recv)
    assert len(keys) == 6  # 3 次握手，每次 2 个不同密钥
