# 一次性测试脚本：单次打开 VCI 总线，发送请求后收集所有响应帧
# 用法: py -3.11-32 can_exchange.py <req_id_hex> <data_csv> <listen_sec>
import sys, time
sys.path.insert(0, r"C:/Users/L/.agents/skills/can-debug/scripts")
from can_tool import create_bus

req_id = int(sys.argv[1], 16)
data = [int(x, 16) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 and sys.argv[2] else []
listen_sec = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0

bus, err = create_bus("vci", "1", 250000, dll="ControlCAN_GC.dll")
if bus is None:
    print("连接失败:", err); sys.exit(1)
import can
msg = can.Message(arbitration_id=req_id, data=data, is_extended_id=True)
bus.send(msg)
print(f"TX 0x{req_id:08X} [{len(data)}] " + " ".join(f"{b:02X}" for b in data))

end = time.time() + listen_sec
while time.time() < end:
    resp = bus.recv(timeout=0.2)
    if resp:
        print(f"RX 0x{resp.arbitration_id:08X} [{resp.dlc}] " + " ".join(f"{b:02X}" for b in resp.data))
bus.shutdown()
