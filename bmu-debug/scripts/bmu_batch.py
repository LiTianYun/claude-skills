# BMU 批量命令执行：按脚本文件逐行发送命令，间隔时间可配，收发原始值与时间戳全量记录
#
# 脚本文件格式（UTF-8 文本，# 开头为注释，空行忽略）：
#   <间隔毫秒> <命令hex> [数据hex,逗号分隔]
# 间隔 = 发送本条命令前等待的时间（相对上一条）；数据缺省为 8 字节 0。
#
# 示例 test.txt：
#   # 切手动均衡（EnBal=0）
#   500   0x01  75,30,0C,E4,00,00,00,00
#   # 单AFE1全开，保持 5 秒
#   500   0x0C  01,00,02,01,00,00,00,00
#   5000  0x0C  00,00,00,00,00,00,00,00
#
# 用法：
#   py -3.11-32 bmu_batch.py test.txt
#   py -3.11-32 bmu_batch.py test.txt --bmu 3 --tail 3 --log run1.csv
from __future__ import annotations

import argparse
import sys
import time

import can  # noqa: E402
from bmu_common import (CsvLogger, fmt_data, fmt_ts, make_req_id, open_bus,
                        print_rx, ts_now)


def parse_script(path: str) -> list[tuple[int, int, list[int]]]:
    """解析脚本文件，返回 [(间隔ms, cmd, data), ...]"""
    steps = []
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                sys.exit(f"{path}:{lineno} 格式错误（至少 间隔ms 和 命令码）: {line}")
            try:
                interval = int(parts[0])
                cmd = int(parts[1], 16)
                data = [int(x, 16) for x in parts[2].split(",")] if len(parts) > 2 else [0] * 8
            except ValueError:
                sys.exit(f"{path}:{lineno} 数值解析失败: {line}")
            if len(data) < 8:
                data += [0] * (8 - len(data))
            steps.append((interval, cmd, data))
    if not steps:
        sys.exit(f"{path} 没有可执行的命令行")
    return steps


def drain_rx(bus, seconds: float, logger: CsvLogger) -> int:
    """在指定秒数内持续接收并记录总线帧，返回帧数"""
    count = 0
    end = time.time() + seconds
    while True:
        remain = end - time.time()
        if remain <= 0:
            break
        resp = bus.recv(timeout=remain)
        if resp is None:
            break
        print_rx(resp, logger)
        count += 1
    return count


def main() -> int:
    p = argparse.ArgumentParser(description="BMU 批量命令执行（GCAN/vci）")
    p.add_argument("script", help="命令脚本文件路径")
    p.add_argument("--bmu", type=int, default=1, help="BMU 地址 ID (1~40)，默认 1")
    p.add_argument("--tail", type=float, default=2.0, help="最后一条命令后的收尾监听秒数，默认 2")
    p.add_argument("--channel", default="1", help="CAN 通道，默认 1")
    p.add_argument("--bitrate", type=int, default=250000, help="波特率，默认 250000")
    p.add_argument("--dll", default="ControlCAN_GC.dll", help="VCI DLL，默认 GCAN")
    p.add_argument("--log", default="bmu_batch_log.csv", help="CSV 日志文件路径")
    args = p.parse_args()

    if not 1 <= args.bmu <= 40:
        sys.exit("--bmu 范围 1~40")
    steps = parse_script(args.script)

    bus = open_bus(args.channel, args.bitrate, args.dll)
    logger = CsvLogger(args.log)

    print(f"执行 {args.script}：{len(steps)} 条命令，目标 BMU {args.bmu}，日志 → {args.log}")
    rx_total = 0
    for idx, (interval, cmd, data) in enumerate(steps, 1):
        rx_total += drain_rx(bus, interval / 1000.0, logger)  # 间隔期间持续监听

        req_id = make_req_id(cmd, args.bmu)
        bus.send(can.Message(arbitration_id=req_id, data=data, is_extended_id=True))
        ts = ts_now()
        decoded = f"step{idx}/{len(steps)} cmd=0x{cmd:02X} bmu={args.bmu}"
        print(f"{fmt_ts(ts)} TX 0x{req_id:08X} [{len(data):02d}] {fmt_data(data)}  {decoded}")
        logger.log(ts, "TX", req_id, len(data), fmt_data(data), decoded)

    rx_total += drain_rx(bus, args.tail, logger)  # 收尾监听

    bus.shutdown()
    logger.close()
    print(f"--- 完成：{len(steps)} 条命令已发送，共收到 {rx_total} 帧，日志 → {args.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
