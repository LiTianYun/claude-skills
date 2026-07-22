# BMU CAN 调试共享模块：总线连接、ID 组帧、回复解码、CSV 日志
# 编址规则（勿随意改动）：
#   请求 ID = (6<<26) | (CMD<<16) | ((0xC8+BMU_ID)<<8) | 0xC8      主机 SA=0xC8
#   回复 ID = (6<<26) | (RESP_PF<<16) | (0xC8<<8) | (0xC8+BMU_ID)  BMU SA=0xC8+ID
from __future__ import annotations

import csv
import os
import sys
from datetime import datetime

# Windows 控制台默认 GBK，强制 UTF-8 输出避免中文乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import can  # noqa: E402
import can.interfaces  # noqa: E402
from vci_adapter import VciBus  # noqa: E402,F401  注册用，勿删
can.interfaces.BACKENDS["vci"] = ("vci_adapter", "VciBus")

HOST_SA = 0xC8
PRO = 6  # 优先级字段，固件 Send_CAN0_Manage 固定左移 26 位

# 回复 PF 名称表（按固件 can0.c 中 Send_CAN0_Manage 的第一个参数）
RESP_PF_NAMES = {
    0x0B: "系统状态1", 0x0C: "系统状态2", 0x15: "内阻", 0x1F: "温度", 0x29: "SOC",
    0x33: "电压告警参数", 0x3D: "温度告警参数", 0x47: "组端电压参数", 0x51: "容量参数",
    0x5B: "温度校准K", 0x65: "均衡状态", 0x6F: "均衡状态包1", 0x70: "均衡状态包2",
    0x71: "均衡状态包3", 0x72: "均衡状态包4", 0x74: "强制均衡回复", 0x79: "SOC告警参数",
    0x83: "均衡电流参数", 0x8D: "均衡电流", 0x8E: "系统状态3", 0x97: "单体电压",
    0xA1: "心跳", 0xAB: "扩展地址", 0xB5: "电压补偿", 0xB6: "看门狗测试确认",
    0xB9: "模块SN", 0xBD: "最大最小", 0xC1: "完整SN", 0xFD: "芯片UID", 0xFE: "未定义命令",
}

EQUI_MODE_NAMES = {0: "关闭所有", 1: "单通道开", 2: "单AFE全开", 3: "全AFE全开", 0xFF: "自动模式忽略"}


def open_bus(channel: str = "1", bitrate: int = 250000, dll: str = "ControlCAN_GC.dll"):
    """打开 GCAN 总线，失败时抛出带排查提示的异常"""
    try:
        return can.Bus(interface="vci", channel=channel, bitrate=bitrate, dll=dll)
    except Exception as e:
        raise RuntimeError(f"CAN 连接失败: {e}（检查 GCAN 卡/驱动/是否被其他进程占用）") from e


def make_req_id(cmd: int, bmu: int) -> int:
    """组请求帧 ID：pro<<26 | cmd<<16 | (0xC8+bmu)<<8 | 0xC8"""
    return (PRO << 26) | (cmd << 16) | ((HOST_SA + bmu) << 8) | HOST_SA


def bmu_sa(bmu: int) -> int:
    """BMU 的源地址 SA"""
    return HOST_SA + bmu


def fmt_data(data) -> str:
    """字节列转空格分隔大写 hex 字符串"""
    return " ".join(f"{b:02X}" for b in data)


def decode_frame(msg, uid_buf: dict | None = None) -> str:
    """解码已知回复 PF，返回人类可读描述；UID 分片存入 uid_buf 凑齐后输出完整 UID"""
    pf = (msg.arbitration_id >> 16) & 0xFF
    sa = msg.arbitration_id & 0xFF
    d = list(msg.data)
    name = RESP_PF_NAMES.get(pf, "")
    base = f"PF=0x{pf:02X} SA=0x{sa:02X} {name}".rstrip()

    if pf == 0xFD and len(d) >= 5 and uid_buf is not None:  # 芯片 UID 分片
        pkt = d[0]
        uid_buf[pkt] = d[1:5]
        if all(k in uid_buf for k in (1, 2, 3, 4)):
            uid = "_".join("".join(f"{b:02X}" for b in uid_buf[k]) for k in (1, 2, 3, 4))
            return f"{base} | 包{pkt}/4 | UID={uid}"
        return f"{base} | 包{pkt}/4 word={d[1]:02X}{d[2]:02X}{d[3]:02X}{d[4]:02X}"
    if pf == 0x74 and len(d) >= 5:  # 强制均衡回复
        mode = d[0]
        return (f"{base} | mode=0x{mode:02X}({EQUI_MODE_NAMES.get(mode, '?')}) "
                f"AFE={d[1]} CH={d[2]} 开启数={d[3]} 均衡模式={d[4]}")
    if pf == 0xB6:  # 看门狗测试确认
        return f"{base} | 密钥回显=0x{d[0]:02X}（BMU 即将死机等看门狗复位）"
    if pf == 0xFE:  # 未定义命令
        return f"{base} | 未识别的命令 PF=0x{d[0]:02X}"
    if 0x1F <= pf <= 0x28 and len(d) >= 8:  # 温度包：PF 从 0x1F 起连续（单地址组最多 10 包），每包 4 个 2 字节值
        vals = []
        for k in range(4):
            raw = (d[k * 2] << 8) | d[k * 2 + 1]
            vals.append("无效" if raw >= 10790 else f"{raw / 10 - 80:.1f}°C")  # 原始值=(T+80)*10
        return f"{base} | 温度包{pf - 0x1F + 1} ch{4 * (pf - 0x1F) + 1}~{4 * (pf - 0x1F) + 4}: {vals}"
    if 0xBF <= pf <= 0xC8 and len(d) >= 8:  # 电压包：PF 从 0xBF(191) 起连续（单地址组最多 10 包），每包 4 节 mV
        vals = []
        for k in range(4):
            raw = (d[k * 2] << 8) | d[k * 2 + 1]
            vals.append("掉线" if raw == 65000 else f"{raw}mV")
        return f"{base} | 电压包{pf - 0xBF + 1} ch{4 * (pf - 0xBF) + 1}~{4 * (pf - 0xBF) + 4}: {vals}"
    return base


def ts_now() -> datetime:
    """当前时间（打印与日志共用）"""
    return datetime.now()


def fmt_ts(ts: datetime) -> str:
    """毫秒精度时间戳字符串 HH:MM:SS.fff"""
    return ts.strftime("%H:%M:%S.%f")[:-3]


class CsvLogger:
    """CSV 收发日志：timestamp,dir,can_id,dlc,data,decoded（UTF-8-BOM，Excel 可直接打开）"""

    def __init__(self, path: str):
        self.path = path
        new_file = not os.path.exists(path)
        self._f = open(path, "a", newline="", encoding="utf-8-sig")
        self._w = csv.writer(self._f)
        if new_file:
            self._w.writerow(["timestamp", "dir", "can_id", "dlc", "data", "decoded"])
            self._f.flush()

    def log(self, ts: datetime, direction: str, can_id: int, dlc: int, data_hex: str, decoded: str = ""):
        """追加一行日志并立即落盘"""
        self._w.writerow((ts.isoformat(timespec="milliseconds"), direction,
                          f"0x{can_id:08X}", dlc, data_hex, decoded))
        self._f.flush()

    def close(self):
        self._f.close()


def send_frame(bus, cmd: int, bmu: int, data: list[int], logger: CsvLogger | None, note: str = ""):
    """发送一帧请求，打印并记录日志"""
    req_id = make_req_id(cmd, bmu)
    msg = can.Message(arbitration_id=req_id, data=data, is_extended_id=True)
    bus.send(msg)
    ts = ts_now()
    decoded = note or f"cmd=0x{cmd:02X} bmu={bmu}"
    print(f"{fmt_ts(ts)} TX 0x{req_id:08X} [{len(data):02d}] {fmt_data(data)}  {decoded}")
    if logger:
        logger.log(ts, "TX", req_id, len(data), fmt_data(data), decoded)


def print_rx(msg, logger: CsvLogger | None, uid_buf: dict | None = None):
    """打印并记录一帧接收"""
    ts = ts_now()
    decoded = decode_frame(msg, uid_buf)
    print(f"{fmt_ts(ts)} RX 0x{msg.arbitration_id:08X} [{msg.dlc:02d}] {fmt_data(msg.data)}  {decoded}")
    if logger:
        logger.log(ts, "RX", msg.arbitration_id, msg.dlc, fmt_data(msg.data), decoded)
