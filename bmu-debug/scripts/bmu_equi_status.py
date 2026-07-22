# BMU 均衡状态解码：发送 0x0B 查询，按监听窗口自适应收集位图包，解码为逐通道列表
# 由 agent 在需要确认"哪些电芯正在均衡"时调用
#
# 用法：
#   py -3.11-32 bmu_equi_status.py              # 查询 BMU1
#   py -3.11-32 bmu_equi_status.py --bmu 3
#   py -3.11-32 bmu_equi_status.py --cells-per-afe 0   # 不按 AFE 分组（或未知平台）
#
# 协议（固件 Send_Cmd_GetSigEquiStatu）：0x0B 查询 → N 包回复，PF 从 0x6F (111) 起连续，
# 每包 Byte4~7 为 4 字节位图；包数随平台总节数变化（N=ceil(总节数/32)），不写死。
# 全部位图拼接后 bit k 置位 = 第 k+1 节正在均衡。
from __future__ import annotations

import argparse
import sys
import time

from bmu_common import (CsvLogger, bmu_sa, open_bus, print_rx, send_frame)

BASE_PF = 0x6F   # 均衡状态首包 PF（十进制 111）


def main() -> int:
    p = argparse.ArgumentParser(description="BMU 均衡状态解码（GCAN/vci）")
    p.add_argument("--bmu", type=int, default=1, help="BMU 地址 ID (1~40)，默认 1")
    p.add_argument("--listen", type=float, default=2.0, help="监听秒数，默认 2")
    p.add_argument("--cells-per-afe", type=int, default=13,
                   help="每 AFE 节数（用于分组显示），默认 13；0=不按 AFE 分组")
    p.add_argument("--channel", default="1", help="CAN 通道，默认 1")
    p.add_argument("--bitrate", type=int, default=250000, help="波特率，默认 250000")
    p.add_argument("--dll", default="ControlCAN_GC.dll", help="VCI DLL，默认 GCAN")
    p.add_argument("--log", default="bmu_debug_log.csv", help="CSV 日志文件路径")
    args = p.parse_args()

    if not 1 <= args.bmu <= 40:
        sys.exit("--bmu 范围 1~40")

    bus = open_bus(args.channel, args.bitrate, args.dll)
    logger = CsvLogger(args.log)

    send_frame(bus, 0x0B, args.bmu, [0] * 8, logger, note=f"cmd=0x0B 查询均衡状态 bmu={args.bmu}")

    # 按监听窗口收集位图包：PF 从 0x6F 起连续即收，收满窗口为止（包数随平台自适应）
    packets: dict[int, bytes] = {}   # 包序号 → 4 字节位图
    end = time.time() + args.listen
    while time.time() < end:
        resp = bus.recv(timeout=0.2)
        if resp is None:
            if packets:
                break   # 已开始收包后总线静默，认为收完
            continue
        print_rx(resp, logger)
        pf = (resp.arbitration_id >> 16) & 0xFF
        sa = resp.arbitration_id & 0xFF
        if sa == bmu_sa(args.bmu) and pf >= BASE_PF and len(resp.data) >= 8:
            seq = pf - BASE_PF
            if seq == len(packets):          # 只收严格连续的包，防止误收其他 PF
                packets[seq] = bytes(resp.data[4:8])
            elif seq > len(packets):
                break                        # 出现跳号说明位图包已结束

    bus.shutdown()
    logger.close()

    if not packets:
        print("[!] 未收到任何位图包（BMU 离线或固件无 0x0B 命令）")
        return 1

    # 拼接实际收到的位图，逐 bit 解码
    raw = b"".join(packets[k] for k in sorted(packets))
    cells = [k + 1 for k in range(len(raw) * 8) if raw[k // 8] & (1 << (k % 8))]

    print(f"--- BMU {args.bmu} 均衡状态：收到 {len(packets)} 包位图（{len(raw)} 字节），"
          f"共 {len(cells)} 节正在均衡")
    if cells and args.cells_per_afe > 0:
        n = args.cells_per_afe
        for afe in range((max(cells) + n - 1) // n):
            lo, hi = afe * n + 1, (afe + 1) * n
            in_afe = [c for c in cells if lo <= c <= hi]
            if in_afe:
                local = [c - afe * n for c in in_afe]
                print(f"    AFE{afe + 1}: 全局通道 {in_afe}（AFE 内通道 {local}）")
    elif cells:
        print(f"    全局通道 {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
