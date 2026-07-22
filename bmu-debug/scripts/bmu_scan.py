# BMU 在线扫描：向地址 1~40 逐个发送探测命令，列出有响应的在线 BMU
# 用法：
#   py -3.11-32 bmu_scan.py                     # 扫描 1~40
#   py -3.11-32 bmu_scan.py --range 1-8         # 只扫 1~8
#   py -3.11-32 bmu_scan.py --cmd 0xFD          # 用 UID 命令探测（默认 0x14 心跳）
from __future__ import annotations

import argparse
import sys
import time

from bmu_common import (CsvLogger, bmu_sa, decode_frame, fmt_data, fmt_ts,
                        make_req_id, open_bus, ts_now)
import can  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="BMU 在线扫描（GCAN/vci）")
    p.add_argument("--range", default="1-40", help="扫描地址范围，如 1-40，默认 1-40")
    p.add_argument("--cmd", default="0x14", help="探测命令码，默认 0x14（心跳查询）")
    p.add_argument("--timeout", type=float, default=0.15, help="每个地址等待回复秒数，默认 0.15")
    p.add_argument("--channel", default="1", help="CAN 通道，默认 1")
    p.add_argument("--bitrate", type=int, default=250000, help="波特率，默认 250000")
    p.add_argument("--dll", default="ControlCAN_GC.dll", help="VCI DLL，默认 GCAN")
    p.add_argument("--log", default="", help="可选：CSV 日志文件路径")
    args = p.parse_args()

    lo, hi = (int(x) for x in args.range.split("-"))
    if not (1 <= lo <= hi <= 40):
        sys.exit("--range 范围须在 1-40 内")
    probe = int(args.cmd, 16)

    bus = open_bus(args.channel, args.bitrate, args.dll)
    logger = CsvLogger(args.log) if args.log else None

    online: list[int] = []
    print(f"扫描 BMU {lo}~{hi}（探测命令 0x{probe:02X}，单地址超时 {args.timeout}s）...")

    for addr in range(lo, hi + 1):
        req_id = make_req_id(probe, addr)
        bus.send(can.Message(arbitration_id=req_id, data=[0] * 8, is_extended_id=True))
        ts = ts_now()
        if logger:
            logger.log(ts, "TX", req_id, 8, "00 " * 7 + "00", f"scan probe bmu={addr}")

        # 等待该地址回复：任何 SA == 0xC8+addr 的帧都算在线
        found = False
        end = time.time() + args.timeout
        while time.time() < end:
            resp = bus.recv(timeout=max(0.0, end - time.time()))
            if resp is None:
                break
            sa = resp.arbitration_id & 0xFF
            decoded = decode_frame(resp)
            if logger:
                logger.log(ts_now(), "RX", resp.arbitration_id, resp.dlc, fmt_data(resp.data), decoded)
            if sa == bmu_sa(addr):
                pf = (resp.arbitration_id >> 16) & 0xFF
                print(f"{fmt_ts(ts_now())} BMU {addr:2d} 在线  (回复 PF=0x{pf:02X})")
                found = True
                break
        if found:
            online.append(addr)

    bus.shutdown()
    if logger:
        logger.close()

    if online:
        print(f"--- 扫描完成：在线 BMU {len(online)} 个 → {online}")
        return 0
    print("--- 扫描完成：无在线 BMU（检查接线/终端电阻/波特率/地址分配）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
