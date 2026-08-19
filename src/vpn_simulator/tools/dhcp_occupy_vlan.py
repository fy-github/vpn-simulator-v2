#!/usr/bin/env python3
import argparse
import ctypes
import fcntl
import json
import os
import queue
import random
import re
import select
import socket
import struct
import subprocess
import sys
import threading
import time

DHCP_SERVER_PORT = 67
DHCP_CLIENT_PORT = 68
BROADCAST = "255.255.255.255"
MAGIC = b"\x63\x82\x53\x63"
FLAG_BROADCAST = 0x8000
DEFAULT_STATE = "dhcp-leases.json"
PKT_SIZE = 300

TYPE_QUERY = {1: "DISCOVER", 2: "OFFER", 3: "REQUEST", 4: "DECLINE",
              5: "ACK", 6: "NAK", 7: "RELEASE", 8: "INFORM"}
IMPORTANT = (1, 3, 6, 12, 15, 28, 50, 51, 53, 54, 55, 61)

_print_lock = threading.Lock()
_fatal = threading.Event()


def pr(*a):
    with _print_lock:
        print(*a)
        sys.stdout.flush()


def random_mac():
    mac = [random.randint(0, 255) for _ in range(6)]
    mac[0] = (mac[0] & 0xFC) | 0x02
    return bytes(mac)


def mac_str(m):
    return ":".join("%02x" % b for b in m)


def mac_from_str(s):
    return bytes(int(x, 16) for x in s.split(":"))


def iface_mac(iface):
    out = subprocess.run(["ifconfig", iface], capture_output=True, text=True).stdout
    m = re.search(r"[ \t]ether ([0-9a-f:]{17})", out)
    if not m:
        sys.exit("==> 读取 %s 的真实 MAC 失败" % iface)
    return mac_from_str(m.group(1))


def parse_pool(spec):
    ip = re.match(r"^(\d+\.\d+\.\d+\.)(\d+)-(\d+)$", spec.strip())
    if not ip:
        sys.exit("--pool 格式应为 网段.起-止，如 192.168.99.50-150")
    base, lo, hi = ip.group(1), int(ip.group(2)), int(ip.group(3))
    if lo > hi or hi - lo + 1 > 400:
        sys.exit("--pool 范围非法或过大")
    return [base + str(i) for i in range(lo, hi + 1)]


def add_aliases(iface, ips):
    ok = 0
    for ip in ips:
        r = subprocess.run(["ifconfig", iface, "inet", ip, "netmask", "255.255.255.0", "alias"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            ok += 1
    return ok


def del_aliases(iface, ips):
    for ip in ips:
        subprocess.run(["ifconfig", iface, "inet", ip, "netmask", "255.255.255.0", "-alias"],
                       capture_output=True, text=True)


def ip_str(b):
    return socket.inet_ntoa(b)


def opt(t, v):
    return bytes([t, len(v)]) + v


def bootp(xid, mac, opts, ciaddr=b"\x00\x00\x00\x00"):
    s = struct.pack("!BBBBI", 1, 1, 6, 0, xid)
    s += struct.pack("!HH", 0, FLAG_BROADCAST)
    s += ciaddr + b"\x00\x00\x00\x00" + b"\x00" * 8
    s += mac + b"\x00" * 10
    s += b"\x00" * 64 + b"\x00" * 128
    s += MAGIC + opts + b"\xff"
    s += b"\x00" * max(0, PKT_SIZE - len(s))
    return s


def opts_disco(mac, requested=None):
    opts = opt(53, b"\x01") + opt(61, b"\x01" + mac) + opt(55, bytes([1, 3, 6, 15, 28, 51]))
    if requested:
        opts += opt(50, requested)
    return opts


def opts_req(mac, ip, server):
    return opt(53, b"\x03") + opt(61, b"\x01" + mac) + opt(50, ip) + opt(54, server)


def opts_release(server):
    return opt(53, b"\x07") + opt(54, server)


def parse_dhcp(data):
    if len(data) < 240 or data[236:240] != MAGIC:
        return None
    xid = struct.unpack("!I", data[4:8])[0]
    yiaddr = data[16:20]
    d = {"xid": xid, "yiaddr": yiaddr, "opts": {}}
    i = 240
    while i < len(data):
        t = data[i]
        if t == 0:
            i += 1
            continue
        if t == 255:
            break
        if i + 2 > len(data):
            break
        l = data[i + 1]
        if t in IMPORTANT:
            d["opts"][t] = data[i + 2:i + 2 + l]
        i += 2 + l
    return d


def msg_type(pkt):
    v = pkt["opts"].get(53)
    return TYPE_QUERY.get(v[0] if v else -1, "?")


def _iow(g, n, sz):
    return 0x80000000 | ((sz & 0x1fff) << 16) | (ord(g) << 8) | n


IP_BOUND_IF = 25
IFREQ_SIZE = 32
BIOCSETIF = _iow("B", 108, IFREQ_SIZE)
BIOCSBLEN = _iow("B", 102, 4) | 0x40000000
BIOCSETF = _iow("B", 103, 16)
BIOCIMMEDIATE = _iow("B", 112, 4)
BIOCSSEESENT = _iow("B", 119, 4)
BIOCSHDRCMPLT = _iow("B", 117, 4)


def bpf_passall():
    insn = ctypes.create_string_buffer(struct.pack("<BBHI", 6, 0, 0, 0xffffffff))

    class _Prog(ctypes.Structure):
        _fields_ = [("bf_len", ctypes.c_uint), ("bf_insns", ctypes.c_void_p)]
    p = _Prog(1, ctypes.addressof(insn))
    _bpf_refs.append((p, insn))
    return p


_bpf_refs: list = []
BROADCAST_MAC = b"\xff" * 6


def _sum16(bs):
    if len(bs) % 2:
        bs += b"\x00"
    s = sum(struct.unpack("!%dH" % (len(bs) // 2), bs))
    while s >> 16:
        s = (s & 0xffff) + (s >> 16)
    return s


def ip_checksum(hdr):
    return (~_sum16(hdr)) & 0xffff


def udp_checksum(payload, src, dst, sport, dport):
    udp = struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload
    pseudo = src + dst + struct.pack("!BBH", 0, 17, len(udp))
    s = _sum16(pseudo) + _sum16(udp)
    while s >> 16:
        s = (s & 0xffff) + (s >> 16)
    return (~s) & 0xffff


def build_udp(payload, sport, dport, src_ip="0.0.0.0", dst_ip=BROADCAST):
    src, dst = socket.inet_aton(src_ip), socket.inet_aton(dst_ip)
    ulen = 8 + len(payload)
    udp = struct.pack("!HHHH", sport, dport, ulen, udp_checksum(payload, src, dst, sport, dport)) + payload
    total = 20 + ulen
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total, random.getrandbits(16), 0, 64, 17, 0, src, dst)
    cs = ip_checksum(ip)
    ip = ip[:10] + struct.pack("!H", cs) + ip[12:]
    return ip + udp


def tagged_frame(src_mac, vlan, payload, dest=(BROADCAST, DHCP_SERVER_PORT)):
    eth = BROADCAST_MAC + src_mac + struct.pack("!HHH", 0x8100, vlan & 0x0fff, 0x0800)
    return eth + build_udp(payload, DHCP_CLIENT_PORT, dest[1], dst_ip=dest[0])

def make_sock(src_ip="0.0.0.0", iface=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except (AttributeError, OSError):
        pass
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if iface:
        try:
            s.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, socket.if_nametoindex(iface))
        except OSError as e:
            sys.exit("==> 设置接口 %s 失败（请用 ifconfig 确认网卡名）：%s" % (iface, e))
    for _ in range(10):
        try:
            s.bind((src_ip, DHCP_CLIENT_PORT))
            return s
        except OSError as e:
            if e.errno != 48:
                raise
            pr("!! UDP 68 端口暂时被占用，1 秒后重试（%d/10）..." % (_ + 1))
            time.sleep(1)
    sys.exit("==> 绑定 UDP 68 端口失败：端口一直被占用。\n"
             "    可能系统 DHCP 客户端(configd)或残留进程占用，请稍后再试：\n"
             "    pkill -f dhcp-occupy-vlan.py  # 残留进程"
             "\n    sudo lsof -nP -iUDP:68     # 查看谁占用")


class UDPCapture:
    def __init__(self, sock):
        self.sock = sock
        self.stopped = False

    def recv(self, timeout):
        self.sock.settimeout(timeout)
        try:
            data, _ = self.sock.recvfrom(4096)
        except socket.timeout:
            return None
        except OSError:
            self.stopped = True
            return None
        return data, None, None, None


def eth_ip_udp(frame):
    if len(frame) < 14:
        return None
    esrc = frame[6:12]
    edst = frame[0:6]
    vlan = None
    et = struct.unpack("!H", frame[12:14])[0]
    i = 14
    if et == 0x8100 and len(frame) >= 18:
        vlan = struct.unpack("!H", frame[14:16])[0] & 0x0fff
        et = struct.unpack("!H", frame[16:18])[0]
        i = 18
    if et != 0x0800 or len(frame) < i + 20:
        return None
    ihl = (frame[i] & 0x0f) * 4
    if frame[i + 9] != 17 or len(frame) < i + ihl + 8:
        return None
    sport, dport = struct.unpack("!HH", frame[i + ihl:i + ihl + 4])
    ulen = struct.unpack("!H", frame[i + ihl + 4:i + ihl + 6])[0]
    if sport != 67 or dport != 68:
        return None
    return frame[i + ihl + 8:i + ihl + ulen], esrc, edst, vlan


class BPFCapture:
    def __init__(self, iface, see_sent=False, rw=False):
        self.stopped = False
        self.fd = None
        self.vlan = 0
        for n in range(16):
            try:
                fd = os.open("/dev/bpf%d" % n, os.O_RDWR if (rw or see_sent) else os.O_RDONLY)
            except FileNotFoundError:
                continue
            except PermissionError:
                sys.exit("==> 打开 /dev/bpf 需要 root：请用 sudo 运行（sudo python3 %s ...）"
                         % os.path.basename(sys.argv[0]))
            except OSError:
                continue
            ifr = struct.pack("16s", iface.encode()[:15]) + b"\x00" * (IFREQ_SIZE - 16)
            try:
                fcntl.ioctl(fd, BIOCSBLEN, struct.pack("i", 65536))
            except OSError as e:
                os.close(fd)
                sys.exit("==> BPF BIOCSBLEN 失败（%s）" % e)
            try:
                fcntl.ioctl(fd, BIOCSETIF, ifr)
            except OSError as e:
                os.close(fd)
                sys.exit("==> BPF 挂载接口 %s 失败（%s）。该网卡可能不支持抓包，"
                         "改用 --iface 内建网卡（en0/en1）试试" % (iface, e))
            try:
                fcntl.ioctl(fd, BIOCSETF, bpf_passall())
            except OSError as e:
                os.close(fd)
                sys.exit("==> BPF BIOCSETF 失败（%s）" % e)
            fcntl.ioctl(fd, BIOCIMMEDIATE, struct.pack("i", 1))
            if rw:
                fcntl.ioctl(fd, BIOCSHDRCMPLT, struct.pack("i", 1))
            if see_sent or rw:
                fcntl.ioctl(fd, BIOCSSEESENT, struct.pack("i", 1))
            self.fd = fd
            break
        if self.fd is None:
            sys.exit("==> 没有可用 /dev/bpf 设备（可能都被 tcpdump 等占用，稍后重试）")

    def send_dhcp(self, payload, src_mac, dest=(BROADCAST, DHCP_SERVER_PORT)):
        os.write(self.fd, tagged_frame(src_mac, self.vlan, payload, dest))

    def close(self):
        self.stopped = True
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

    def recv(self, timeout):
        r, _, _ = select.select([self.fd], [], [], timeout)
        if not r:
            return None
        try:
            data = os.read(self.fd, 65536)
        except OSError:
            self.stopped = True
            return None
        off = 0
        while off + 18 <= len(data):
            caplen = struct.unpack("<I", data[off + 8:off + 12])[0]
            hdrlen = struct.unpack("<H", data[off + 16:off + 18])[0]
            if hdrlen < 18:
                hdrlen = 18
            end = off + hdrlen + caplen
            if caplen <= 0 or end > len(data):
                break
            r2 = eth_ip_udp(data[off + hdrlen:end])
            off = end
            if r2:
                return r2
        return None


class Router:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.lock = threading.Lock()
        self.queues = {}
        self.count = 0

    def register(self, xid):
        q = queue.Queue(64)
        with self.lock:
            self.queues[xid] = q
        return q

    def unregister(self, xid):
        with self.lock:
            self.queues.pop(xid, None)

    def route(self, pkt):
        with self.lock:
            q = self.queues.get(pkt["xid"])
        if q:
            try:
                q.put_nowait(pkt)
            except queue.Full:
                pass

    def on_recv(self, pkt):
        if msg_type(pkt) in ("OFFER", "ACK", "NAK"):
            self.count += 1
        if self.verbose:
            pr("  << 收到 %-8s xid=%08x 地址%s"
               % (msg_type(pkt), pkt["xid"], ip_str(pkt["yiaddr"])))


def reader_loop(cap, router, vlan=None):
    while not cap.stopped:
        got = cap.recv(1.0)
        if got is None:
            continue
        fvlan = got[3] if len(got) > 3 else None
        if vlan is not None and fvlan != vlan:
            continue
        p = parse_dhcp(got[0])
        if not p:
            continue
        router.on_recv(p)
        router.route(p)


def send(sock, pkt, verbose, tag, mac, dest=(BROADCAST, DHCP_SERVER_PORT)):
    try:
        if hasattr(sock, "send_dhcp"):
            sock.send_dhcp(pkt, mac, dest)
        else:
            sock.sendto(pkt, dest)
    except OSError as e:
        pr("  !! 发送 %-8s 失败: %s" % (tag, e))
        if e.errno == 51:
            pr("     普通 UDP 模式需要该网卡有 IPv4 地址且能路由到 %s。" % dest[0])
            pr("     若地址池在 VLAN 上（网卡本身无 IP），请改用 --vlan <ID> 走 BPF 收发。")
        _fatal.set()
        raise SystemExit(1)
    if verbose:
        pr("  >> 发送 %-8s %s 报文长度=%dB 目标=%s%s" % (tag, mac_str(mac), len(pkt), dest[0],
                                                  " VLAN%s" % getattr(sock, "vlan", "") if hasattr(sock, "vlan") and sock.vlan else ""))


def wait_pkt(q, timeout, pred):
    deadline = time.time() + timeout
    while True:
        left = deadline - time.time()
        if left <= 0:
            return None
        try:
            p = q.get(timeout=left)
        except queue.Empty:
            return None
        if pred(p):
            return p


def do_dora(sock, router, mac, timeout, attempts, verbose, requested=None, dest=(BROADCAST, DHCP_SERVER_PORT)):
    for _ in range(attempts):
        xid = random.getrandbits(32)
        q = router.register(xid)
        try:
            send(sock, bootp(xid, mac, opts_disco(mac, requested)), verbose, "DISCOVER", mac, dest)
            time.sleep(0.2)
            send(sock, bootp(xid, mac, opts_disco(mac, requested)), verbose, "DISCOVER", mac, dest)
            offer = wait_pkt(q, timeout, lambda p: msg_type(p) == "OFFER")
            if not offer:
                if verbose:
                    pr("  !! 未收到 OFFER (xid=%08x %s)" % (xid, mac_str(mac)))
                continue
            ip = offer["yiaddr"]
            server = offer["opts"].get(54, offer["siaddr"] if "siaddr" in offer else b"\x00\x00\x00\x00")
            lease = int.from_bytes(offer["opts"].get(51, b"\x00\x00\x00\x3c"), "big")
            if verbose:
                pr("  << OFFER 地址=%s 服务器=%s 租约=%ds (xid=%08x)"
                   % (ip_str(ip), ip_str(server), lease, xid))
            send(sock, bootp(xid, mac, opts_req(mac, ip, server)), verbose, "REQUEST", mac, dest)
            time.sleep(0.2)
            send(sock, bootp(xid, mac, opts_req(mac, ip, server)), verbose, "REQUEST", mac, dest)
            while True:
                reply = wait_pkt(q, timeout, lambda p: msg_type(p) in ("ACK", "NAK"))
                if not reply:
                    if verbose:
                        pr("  !! 未收到 ACK/NAK (xid=%08x %s)" % (xid, mac_str(mac)))
                    break
                if msg_type(reply) == "NAK":
                    if verbose:
                        pr("  !! 收到 NAK (xid=%08x %s)" % (xid, mac_str(mac)))
                    break
                if reply["yiaddr"] == ip:
                    return {"ip": ip, "server": server, "lease": lease, "xid": xid}
        finally:
            router.unregister(xid)
    return None


def renew_once(sock, router, mac, xid, ip, server, timeout, verbose, dest=(BROADCAST, DHCP_SERVER_PORT)):
    q = router.register(xid)
    try:
        send(sock, bootp(xid, mac, opts_req(mac, ip, server), ciaddr=ip), verbose, "RENEW", mac, dest)
        time.sleep(0.2)
        send(sock, bootp(xid, mac, opts_req(mac, ip, server), ciaddr=ip), verbose, "RENEW", mac, dest)
        while True:
            reply = wait_pkt(q, timeout, lambda p: msg_type(p) in ("ACK", "NAK"))
            if not reply:
                return False
            if msg_type(reply) == "NAK":
                return False
            return True
    finally:
        router.unregister(xid)


def release_once(sock, mac, xid, ip, server, dest=(BROADCAST, DHCP_SERVER_PORT)):
    try:
        pkt = bootp(xid, mac, opts_release(server), ciaddr=ip)
        if hasattr(sock, "send_dhcp"):
            sock.send_dhcp(pkt, mac, dest)
        else:
            sock.sendto(pkt, dest)
    except OSError:
        pass


def save_state(path, result, iface=None, pool=None):
    leases = []
    for got in result.values():
        if not got:
            continue
        leases.append({"mac": mac_str(got["mac"]), "ip": ip_str(got["ip"]),
                       "server": ip_str(got["server"]), "lease": got["lease"], "xid": got["xid"]})
    data = {"iface": iface, "pool": pool or [], "leases": leases}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def client_worker(name, mac, result, args, stop):
    if args._transport is not None:
        sock = args._transport
    else:
        sock = make_sock(args.src_ip, args.iface)
    requested = args._hint_ip(name) if args.pool else None
    try:
        got = do_dora(sock, args._router, mac, args.timeout, args.attempts, args.verbose,
                      requested, args._dest)
        if not got:
            pr("[%d] %s 获取失败" % (name, mac_str(mac)))
            return
        got["mac"] = mac
        result[name] = got
        pr("[%d] %s 占用成功 -> %s (server=%s lease=%ds)"
           % (name, mac_str(mac), ip_str(got["ip"]), ip_str(got["server"]), got["lease"]))
        if args.hold:
            while not stop.is_set():
                stop.wait(max(2, got["lease"] // 2))
                if stop.is_set():
                    break
                if renew_once(sock, args._router, mac, got["xid"], got["ip"],
                              got["server"], args.timeout, args.verbose, args._dest):
                    pr("[%d] %s 续期成功" % (name, ip_str(got["ip"])))
                    continue
                pr("[%d] %s 续期失败，重新获取" % (name, ip_str(got["ip"])))
                got = do_dora(sock, args._router, mac, args.timeout, args.attempts,
                              args.verbose, requested, args._dest)
                if not got:
                    return
                got["mac"] = mac
                result[name] = got
                pr("[%d] %s 重新占用 -> %s" % (name, mac_str(mac), ip_str(got["ip"])))
    finally:
        if args._transport is None:
            sock.close()


def blind_worker(name, mac, ip, server, args, result):
    sock = make_sock(args.src_ip, args.iface)
    try:
        xid = random.getrandbits(32)
        req_ip = socket.inet_aton(ip)
        srv = socket.inet_aton(server)
        for _ in range(2):
            send(sock, bootp(xid, mac, opts_disco(mac, req_ip)), args.verbose,
                 "DISCOVER", mac, args._dest)
            time.sleep(0.2)
        for _ in range(2):
            send(sock, bootp(xid, mac, opts_req(mac, req_ip, srv)), args.verbose,
                 "REQUEST", mac, args._dest)
            time.sleep(0.2)
        result[name] = {"ip": req_ip, "server": srv, "lease": 3600, "xid": xid, "mac": mac}
        pr("[%d] %s 盲写占用 -> %s (server=%s，未验证)"
           % (name, mac_str(mac), ip, server))
    finally:
        sock.close()


def cmd_release(args):
    if not os.path.exists(args.save):
        sys.exit("状态文件 %s 不存在，先运行获取命令再释放" % args.save)
    with open(args.save) as f:
        data = json.load(f)
    if isinstance(data, list):
        leases = data
        data = {}
    else:
        leases = data.get("leases", [])
    if not leases:
        sys.exit("状态文件为空，无需释放")
    args._dest = (args.server, args.server_port) if args.server else (BROADCAST, DHCP_SERVER_PORT)
    if args.vlan is not None:
        if not args.iface:
            sys.exit("--release 配合 --vlan 需要指定 --iface 网卡名")
        sock = BPFCapture(args.iface, rw=True)
        sock.vlan = args.vlan
        pr(">> 经 %s 打 VLAN%d 标签释放" % (args.iface, args.vlan))
    else:
        sock = make_sock(args.src_ip, args.iface)
    pr("开始释放 %d 个占用地址..." % len(leases))
    for le in leases:
        mac = mac_from_str(le["mac"])
        ip = socket.inet_aton(le["ip"])
        server = socket.inet_aton(le["server"])
        release_once(sock, mac, le["xid"], ip, server, args._dest)
        pr("  释放  %s -> %s (server=%s)" % (le["mac"], le["ip"], le["server"]))
        time.sleep(0.05)
    sock.close()
    pool = data.get("pool") or []
    if pool and data.get("iface"):
        del_aliases(data["iface"], pool)
        pr("  已移除 %s 上预挂的 %d 个别名" % (data["iface"], len(pool)))
    os.remove(args.save)
    pr("\n已释放 %d 个地址，状态文件已清理" % len(leases))


def cmd_watch(args):
    duration = args.watch
    if not args.iface:
        sys.exit("--watch 需要指定 --iface 网卡名")
    cap = BPFCapture(args.iface, see_sent=True)
    pr("监听 %s 上的 DHCP 流量 %ds（Ctrl+C 提前结束）..." % (args.iface, duration))
    start = time.time()
    seen = 0
    try:
        while time.time() - start < duration:
            got = cap.recv(1.0)
            if got is None:
                continue
            payload, esrc, edst, fvlan = got
            p = parse_dhcp(payload)
            if not p:
                continue
            seen += 1
            server = p["opts"].get(54)
            pr("  %-9s 二层%s -> %s  服务器%s 地址%s  xid=%08x%s"
               % (msg_type(p), mac_str(esrc), mac_str(edst),
                  ip_str(server) if server else "-",
                  ip_str(p["yiaddr"]) if any(p["yiaddr"]) else "-", p["xid"],
                  "  VLAN%d" % fvlan if fvlan else ""))
    except KeyboardInterrupt:
        pass
    pr("\n共看到 %d 条 DHCP 报文" % seen)


def cmd_acquire(args):
    if os.path.exists(args.save):
        pr("警告：状态文件 %s 已存在，将被本次运行覆盖" % args.save)

    vlan_mode = args.vlan is not None
    if vlan_mode and not args.iface:
        sys.exit("--vlan 需要指定 --iface 网卡名")
    if vlan_mode and args.blind:
        sys.exit("--vlan 与 --blind 不兼容：VLAN 走原始帧收发，盲写无意义")

    if args.pool and not (args.blind or vlan_mode):
        if os.geteuid() != 0:
            sys.exit("--pool 别名模式需要 root：sudo python3 %s ..." % os.path.basename(sys.argv[0]))
    if args.blind and not args.pool:
        sys.exit("--blind 需要 --pool 提供候选 IP 才能定向请求")

    pool = parse_pool(args.pool) if args.pool else []
    args._hint_ip = lambda name: socket.inet_aton(pool[(name - 1) % len(pool)]) if pool else None
    args._dest = (args.server, args.server_port) if (args.server and not args.raw) \
        else (BROADCAST, DHCP_SERVER_PORT)

    router = Router(args.verbose)
    args._router = router
    if vlan_mode:
        args._transport = BPFCapture(args.iface, rw=True)
        args._transport.vlan = args.vlan
        cap = args._transport
    else:
        args._transport = None
        sock = make_sock(args.src_ip, args.iface)
        if args.blind:
            cap = None
        else:
            cap = BPFCapture(args.iface) if args.raw else UDPCapture(sock)
    if cap is not None:
        threading.Thread(target=reader_loop, args=(cap, router, args.vlan), daemon=True).start()

    added = 0
    if pool and not (args.blind or vlan_mode):
        added = add_aliases(args.iface, pool)
        pr(">> 已在本机 %s 预挂 %d/%d 个别名" % (args.iface, added, len(pool)))
    if args.blind:
        if not args.server:
            sys.exit("--blind 需要 --server <DHCP服务器IP>")

    result = {}
    stop = threading.Event()
    threads = []
    real_mac = iface_mac(args.iface) if args.source_mac == "real" and args.iface else None
    for i in range(1, args.n + 1):
        if _fatal.is_set():
            pr("\n>> 网络不可达，停止后续启动")
            break
        mac = real_mac if args.source_mac == "real" else random_mac()
        if args.blind:
            th = threading.Thread(target=blind_worker,
                                  args=(i, mac, pool[(i - 1) % len(pool)], args.server, args, result))
        else:
            th = threading.Thread(target=client_worker, args=(i, mac, result, args, stop))
        threads.append(th)
        th.start()
        if i < args.n and args.interval > 0:
            time.sleep(args.interval)

    start = time.time()
    try:
        if args.hold:
            while args.duration <= 0 and any(th.is_alive() for th in threads):
                time.sleep(1)
            if args.duration > 0:
                while time.time() - start < args.duration:
                    time.sleep(1)
        else:
            for th in threads:
                th.join()
    except KeyboardInterrupt:
        pr("\n>> Ctrl+C，停止占用")
    finally:
        stop.set()
        if pool and not (args.blind or vlan_mode) and not args.keep_aliases and added:
            del_aliases(args.iface, pool)
            pr(">> 已移除 %s 上预挂的别名" % args.iface)

    save_state(args.save, result, args.iface, pool)
    total = len([v for v in result.values() if v])
    pr("\n========== 占用汇总 ==========")
    pr("  请求 %d 个地址，成功 %d 个，共收到 %d 条 DHCP 响应" % (args.n, total, router.count))
    pr()
    pr("  %-4s %-18s %-16s %-16s %s" % ("序号", "MAC", "IP", "服务器", "租约"))
    for i in range(1, args.n + 1):
        got = result.get(i)
        if got:
            pr("  %-4d %-18s %-16s %-16s %s"
               % (i, mac_str(got["mac"]), ip_str(got["ip"]),
                  ip_str(got["server"]), "%ds" % got["lease"] if not args.blind else "3600s?"))
        else:
            pr("  %-4d %-18s" % (i, "获取失败"))
    pr("\n状态已保存: %s" % args.save)
    pr("重新运行 --release 可显式释放以上全部地址")
    if total < args.n and router.count == 0 and not args.blind:
        pr("\n提示：未收到任何 DHCP 回包，请用 --source-mac real 复测区分原因：")
        pr("  python3 %s -n 1 --iface <网卡> --source-mac real -v" % os.path.basename(sys.argv[0]))
        pr("  若 real 能拿到而随机 MAC 不行，说明网关开启了 IP-MAC 绑定/防 DHCP 欺骗")
        pr("  （只放行 chaddr=二层源MAC 的请求），需在 DHCP 服务器侧关闭，工具无法绕过。")


def main():
    ap = argparse.ArgumentParser(
        description="DHCP 工具：随机 MAC 并发获取多个 DHCP 地址并占住（纯 Python UDP，无需 root）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("-n", type=int, default=5, metavar="数量", help="要获取的 DHCP 地址数量")
    ap.add_argument("--interval", type=float, default=0.5, metavar="秒",
                    help="并发启动每个占用请求的间隔，避免突发丢包，调大更稳")
    ap.add_argument("--timeout", type=float, default=6.0, help="单次请求等待回包秒数")
    ap.add_argument("--attempts", type=int, default=3, help="获取失败后的重试次数")
    ap.add_argument("--hold", action="store_true",
                    help="持续续期保持占用（配合 --duration 限时，否则直到 Ctrl+C）")
    ap.add_argument("--duration", type=float, default=0.0, help="--hold 时的总运行秒数，0 表示直到 Ctrl+C")
    ap.add_argument("--iface", default=None, help="指定发送网卡名（如 en1/en9），用于多网卡/默认路由被虚拟网卡占用时")
    ap.add_argument("--vlan", type=int, default=None, metavar="ID",
                    help="用 802.1Q 打 VLAN 标签，经 BPF 原始帧收发，直接对接交换机 trunk/指定 VLAN 的 DHCP"
                         "（需 sudo，配合 --iface；VLAN 模式下勿用 --raw/--blind）")
    ap.add_argument("--raw", action="store_true",
                    help="用 BPF 抓包方式接收 DHCP 回包（需 sudo），可绕过防火墙、也能收到单播回包")
    ap.add_argument("--source-mac", choices=["random", "real"], default="random",
                    help="chaddr 用随机 MAC 还是网卡真实 MAC（real 仅用于诊断网关是否丢弃伪造 chaddr）")
    ap.add_argument("--pool", default=None, metavar="网段.起-止",
                    help="DHCP 池区间（如 192.168.99.50-150）：预挂为本机别名，使单播 OFFER/ACK 可收到（需 sudo）")
    ap.add_argument("--server", default=None, metavar="IP", help="DHCP 服务器 IP（--blind 必填，如 192.168.99.1）")
    ap.add_argument("--server-port", type=int, default=67, metavar="端口", help="服务器 UDP 端口")
    ap.add_argument("--blind", action="store_true",
                    help="盲写模式：不等待回包，直接 DISCOVER+REQUEST 定向池内 IP（配合 --pool/--server）")
    ap.add_argument("--keep-aliases", action="store_true", help="运行结束保留 --pool 预挂的别名")
    ap.add_argument("--watch", type=float, default=0.0, metavar="秒",
                    help="被动监听网卡上所有 DHCP 流量并打印（需 sudo，配合 --iface），不发请求")
    ap.add_argument("--src-ip", default="0.0.0.0", help="绑定源 IP，一般无需修改")
    ap.add_argument("--verbose", "-v", action="store_true", help="打印每个 DHCP 收发报文，便于排查")
    ap.add_argument("--save", default=DEFAULT_STATE, help="租约状态文件路径")
    ap.add_argument("--release", action="store_true",
                    help="显式释放之前占用并保存在状态文件中的全部地址")
    args = ap.parse_args()

    if args.vlan is not None and not (0 <= args.vlan <= 4094):
        sys.exit("--vlan 取值需在 1-4094 之间")

    if args.watch > 0:
        cmd_watch(args)
        return
    if args.release:
        cmd_release(args)
        return
    if args.n < 1 or args.n > 200:
        sys.exit("数量 -n 需在 1-200 之间")
    cmd_acquire(args)


if __name__ == "__main__":
    main()