# VPN Simulator v2 — PPP MS-CHAPv2 认证（真实 MD4/SHA1/DES）计划 v16

> 承接 `PLAN_ENHANCEMENT_V15.md`（9 协议全部接入 validation）。本计划把 PPP 层
> **MS-CHAPv2 挑战-响应认证**（RFC 2759）真实化，替换 l2tp/pptp 隧道步骤里的
> 「PPP 认证待接入」占位：真实 NT-Hash（MD4 + UTF-16LE）、ChallengeHash（SHA1）、
> 3×DES 挑战-响应，驱动隧道步骤从「数据面往返成功」升级为「数据面往返 + 真实
> MS-CHAPv2 认证成功」。

## 一、背景与现状

- l2tp / pptp 的 PPP 载荷层认证当前为占位（`PPP 认证待接入`）。
- MS-CHAPv2 是 PPTP/L2TP（及 SSTP/OpenConnect 承载的 PPP）最常见认证，密码学价值最高：
  MD4 + SHA1 + 3×DES 挑战-响应，全部可用真实密码学实现。

## 二、密码学（RFC 2759，真实）

```
NtPasswordHash = MD4( UTF-16LE(password) )                        # 16 字节
Challenge      = SHA1( PeerChallenge(16) + ServerChallenge(16) + Username )[0:8]  # 8 字节
ChallengeResponse =
    DES( NtHash[0:7]  →key, Challenge ) ||                        # 8 字节
    DES( NtHash[7:14] →key, Challenge ) ||                        # 8 字节
    DES( NtHash[14:16] + 5×0 →key, Challenge )                    # 8 字节
```

- 7 字节 DES key → 8 字节（每 7 位插 1 位奇校验位）。
- 3 段 DES 加密的是**同一个 8 字节 Challenge**（非 3DES 链式）。
- 校验用 `hmac.compare_digest` 常量时间比较。

## 三、分阶段任务

### P1 — MS-CHAPv2 密码学

新增 `plugins/protocols/ppp/mschapv2.py`（`__init__.py` 为空、无 `plugin.py`，不注册
插件）：`generate_challenge` / `compute_nt_hash` / `compute_challenge` /
`compute_challenge_response` / `verify_challenge_response`。附 RFC 2759 测试向量单测。

### P2 — 接入 l2tp / pptp 隧道步骤

`validation.py`：新增 `_run_mschapv2_auth(username, password)`，在 l2tp / pptp 隧道
步骤的数据面往返之后做真实 MS-CHAPv2，成功条件改为「数据面往返 AND MS-CHAPv2」。

### P3 — 测试 + 文档

- `tests/unit/test_mschapv2.py`：RFC 2759 向量 + 错误密码/错误挑战拒绝。
- `tests/integration/test_*`：l2tp / pptp 隧道步骤消息含「MS-CHAPv2 认证成功」。
- `README.md`：测试数/特性说明同步。

## 四、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- l2tp / pptp 的 tunnel 步骤为「真实数据面往返 + 真实 MS-CHAPv2 认证」。
- 每功能独立提交并推送到 `origin/main`。

## 五、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。l2tp / pptp 隧道步骤的
「PPP 认证待接入」占位已替换为真实 MS-CHAPv2（MD4 + SHA1 + 3×DES）。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `cf94ae0` | `ppp/mschapv2.py`（自实现 MD4 + NT-Hash + 3×DES）+ 单元测试（RFC 1320/2759 向量） |
| P2 | `6e32a33` | `validation.py` 接入 l2tp/pptp 隧道步骤（`_run_mschapv2_auth`）+ 测试断言 |
| P3 | 本提交 | README 同步 |

实现要点：`cryptography` 42+ 移除了 MD4，故按 RFC 1320 自实现 MD4（含第 2/3 轮
加法常量 `0x5A827999` / `0x6ED9EBA1`）；单 DES 走 `cryptography.hazmat.decrepit`
的 `TripleDES`（8 字节 key）并抑制单 DES 弃用告警。RFC 2759 向量：UserName=User /
Password=clientPass → NT-Hash `44EBBA8D5312B8D611474411F56989AE`、
ChallengeResponse `82309ECD8D708B5EA08FAA3981CD83544233114A3D85D6DF`。

最终指标：后端 1321 tests 通过、82.2% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

