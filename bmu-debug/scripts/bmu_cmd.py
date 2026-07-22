# BMU CAN 通用指令工具：向指定 BMU 发送一条命令，带时间戳打印回复并记录 CSV 日志
# 依赖：python-can；GCAN 卡需 32-bit Python（py -3.11-32）
#
# 用法：
#   py -3.11-32 bmu_cmd.py --cmd 0xFD                            # 查询 BMU1 芯片 UID
#   py -3.11-32 bmu_cmd.py --bmu 5 --cmd 0xFD                    # 查询 BMU5
#   py -3.11-32 bmu_cmd.py --cmd 0x0C --data 01,00,02,01         # 单AFE1全开均衡
#   py -3.11-32 bmu_cmd.py --cmd 0x01 --data 75,30,0C,E4,00,00,00,00  # 切手动均衡
#   py -3.11-32 bmu_cmd.py --cmd 0x71 --data A5 --yes            # 看门狗测试(BMU将复位!)
#   py -3.11-32 bmu_cmd.py --cmd 0x13 --listen 3                 # 查询单体电压(多包,听久些)
from __future__ import annotations

import argparse
import sys
import time

from bmu_common import (CsvLogger, bmu_sa, open_bus, print_rx, send_frame)


def is_dangerous(cmd: int, data: list[int]) -> str:
    """识别危险帧，返回危险原因（空串=安全）"""
    if cmd == 0x71 and data and data[0] == 0xA5:
        return "看门狗测试：BMU 将关中断死循环，只能靠外部看门狗复位"
    if cmd == 0x12 and data and data[0] in (0xBA, 0xBC):
        return ("恢复出厂+复位：清空全部参数（含校准值）" if data[0] == 0xBC else "软件复位")
    return ""


def main() -> int:
    p = argparse.ArgumentParser(description="BMU CAN 通用指令工具（GCAN/vci，扩展帧）")
    p.add_argument("--cmd", required=True, help="命令码 hex，如 0xFD")
    p.add_argument("--data", default="", help="数据字节，逗号分隔 hex，如 01,00,02,01；缺省补 8 字节 0")
    p.add_argument("--bmu", type=int, default=1, help="BMU 地址 ID (1~40)，默认 1")
    p.add_argument("--listen", type=float, default=2.0, help="发送后监听秒数，默认 2")
    p.add_argument("--channel", default="1", help="CAN 通道，默认 1")
    p.add_argument("--bitrate", type=int, default=250000, help="波特率，默认 250000")
    p.add_argument("--dll", default="ControlCAN_GC.dll", help="VCI DLL，默认 GCAN")
    p.add_argument("--log", default="bmu_debug_log.csv", help="CSV 日志文件路径")
    p.add_argument("--yes", action="store_true", help="确认执行危险命令(0x71/0x12复位类)")
    args = p.parse_args()

    if not 1 <= args.bmu <= 40:
        sys.exit("--bmu 范围 1~40")
    cmd = int(args.cmd, 16)
    data = [int(x, 16) for x in args.data.split(",")] if args.data else [0] * 8
    if len(data) < 8:
        data += [0] * (8 - len(data))  # 协议固定 8 字节，不足补 0

    reason = is_dangerous(cmd, data)
    if reason and not args.yes:
        sys.exit(f"[!] 危险命令（{reason}），请加 --yes 确认执行")

    bus = open_bus(args.channel, args.bitrate, args.dll)
    logger = CsvLogger(args.log)
    uid_buf: dict = {}

    send_frame(bus, cmd, args.bmu, data, logger)

    rx_count = 0
    end = time.time() + args.listen
    while time.time() < end:
        resp = bus.recv(timeout=0.2)
        if resp is None:
            continue
        print_rx(resp, logger, uid_buf)
        rx_count += 1

    bus.shutdown()
    logger.close()
    print(f"--- 收到 {rx_count} 帧，日志已追加到 {args.log}")
    return 0 if rx_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
