# VPN Simulator v2 — PPP MPPE 数据面加密计划 v21

> 承接 V20（OpenVPN 真实 TLS）。本计划把 MS-CHAPv2 认证（V16）延伸出 **MPPE**
> （Microsoft Point-to-Point Encryption，RFC 3078/3079）密钥派生与 RC4 加密，
> 使 l2tp / pptp 的 PPP 数据面从「明文封装」升级为「真实 RC4 加密」。

## 一、背景与现状

- V16 已实现 MS-CHAPv2：`compute_nt_hash`（NT-Hash）+ `compute_challenge_response`
  （24 字节响应）。但未派生 MPPE 数据加密密钥。
- l2tp / pptp 数据面（`_run_l2tp_data_roundtrip` / `_run_gre_roundtrip`）当前发送
  明文 payload，PPP 数据面未加密。
- 真实 PPTP / L2TP+MPPE 在 MS-CHAPv2 认证后按 RFC 3079 派生会话密钥，用 RC4 加密
  PPP 数据面。

## 二、密钥派生（RFC 3079 §3.2/§3.4，128-bit MS-CHAPv2）

```
PasswordHash     = MD4(UTF-16LE(password))            # = NT-Hash (16 字节)
PasswordHashHash = MD4(PasswordHash)                  # 16 字节
MasterKey        = SHA1(PasswordHashHash | NTResponse |
                        "This is the MPPE Master Key")[0:16]
MasterSendKey    = MasterReceiveKey = MasterKey       # MS-CHAPv2 对称
SendSessionKey   = SHA1(MasterKey | 0x00*40 | MasterKey | 0xf2*40)[0:16]
ReceiveSessionKey = SendSessionKey                    # MS-CHAPv2 对称
```

- 数据面：`client→server` 用 `SendSessionKey`，`server→client` 用 `ReceiveSessionKey`，
  均为 RC4 流加密。
- 报文：`coherency_count(2, BE) | RC4(session_key, plaintext)`，coherency_count 每方向
  单调递增用于丢包/乱序检测（RFC 3078 教学简化）。

## 三、分阶段任务

### P1 — MPPE 密钥派生 + RC4 会话

新增 `plugins/protocols/ppp/mppe.py`：`derive_session_keys`（RFC 3079）+ `rc4_crypt`
（走 cryptography `ARC4`）+ `MPPESession`（send/recv 密钥 + 递增 coherency_count 的
encrypt/decrypt）。单元测试覆盖 RFC 3079 §4.1 输入向量 + RC4 经典向量。

### P2 — 接入 l2tp/pptp 数据面

`validation.py`：在 `_run_mschapv2_auth` 基础上派生 MPPE 会话密钥，l2tp/pptp 数据面
往返改用 `MPPESession` 加密 payload（不再明文）。

### P3 — 测试 + 文档

- `tests/unit/test_mppe.py`；l2tp/pptp 集成测试同步。
- `README.md`：测试数/特性说明同步。

## 四、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- l2tp / pptp 数据面走真实 MPPE（RFC 3079 密钥 + RC4 加密）。
- 每功能独立提交并推送到 `origin/main`。
