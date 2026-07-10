# J-Link GDB 调试 Skill 用法

这个 skill 自带了一个可执行脚本 [scripts/jlink_debugger.py](../scripts/jlink_debugger.py)，适合在需要通过 J-Link 探针进行 GDB 调试时直接调用。

## 能力概览

- 检测 JLinkGDBServer 和 GDB 是否可用
- 启动 JLinkGDBServer 后台进程
- 三种调试模式：下载并停核、仅附着、崩溃现场检查
- SWO 输出捕获
- 输出结构化的调试结果报告

## 基础用法

```bash
# 探测调试环境
python3 skills/debug-jlink/scripts/jlink_debugger.py --detect

# 下载并停核调试（默认模式）
python3 skills/debug-jlink/scripts/jlink_debugger.py \
  --elf build/app.elf --device STM32F407VG

# 附着调试
python3 skills/debug-jlink/scripts/jlink_debugger.py \
  --elf build/app.elf --device STM32F407VG --mode attach-only

# 崩溃现场排查
python3 skills/debug-jlink/scripts/jlink_debugger.py \
  --elf build/app.elf --device STM32F407VG --mode crash-context
```

## 调试模式说明

### download-and-halt（默认）

将 ELF 下载到目标，复位后停在入口。适合常规开发调试。

### attach-only

不复位、不下载，直接附着到当前运行状态。适合观察运行中的程序。

### crash-context

停核后读取寄存器、回溯和 Cortex-M Fault 寄存器（CFSR/HFSR/MMFAR/BFAR）。适合 HardFault 排查。

## 参数说明

| 参数 | 说明 |
| --- | --- |
| `--detect` | 探测 J-Link 调试环境 |
| `--elf` | 带符号的 ELF 文件路径 |
| `--device` | 目标芯片型号（如 STM32F407VG） |
| `--mode` | 调试模式：`download-and-halt`、`attach-only`、`crash-context` |
| `--gdb` | GDB 可执行文件路径 |
| `--interface` | 调试接口：`SWD`（默认）或 `JTAG` |
| `--speed` | 通信速度 kHz（默认 4000） |
| `--port` | GDB 服务端口（默认 2331） |
| `--swo` | 启用 SWO 输出捕获 |
| `--save-config` | 探测成功后保存工具路径到配置 |
| `-v`, `--verbose` | 输出详细日志 |

## 与 debug-gdb-openocd 的区别

| 特性 | debug-jlink | debug-gdb-openocd |
|------|-------------|-------------------|
| GDB Server | JLinkGDBServer | OpenOCD |
| 默认端口 | 2331 | 3333 |
| 需要设备名 | 是（`--device`） | 否 |
| SWO 支持 | ✅ 原生 | ⚠️ 有限 |
| 配置复杂度 | 低（仅需设备名） | 高（需接口+目标配置） |

## 返回码

- `0`：调试会话成功完成
- `1`：参数非法、依赖缺失、连接失败、调试失败

## 故障排除

### GDB 连接 error 138 (Windows)

**现象**：JLinkGDBServer 启动成功，GDB 连接时报 `could not connect (error 138)`。

**原因**：GDB batch 模式下 `localhost` 在 Windows 上可能触发路径合并错误。

**解决**：脚本已默认使用 `127.0.0.1` 替代 `localhost`。若手动编写 GDB 脚本，同理替换。

### 设备名在 JLinkDevices.xml 中找不到

**现象**：`grep` 搜索 `JLinkDevices.xml` 找不到目标设备名（如 `R7FA2L1AB`）。

**原因**：部分 Renesas 等厂商的设备定义在 `JLinkARM.dll` 二进制中，不在 XML 数据库。

**解决**：脚本在启动调试前会自动搜索 XML + DLL 双源验证设备名。若仅在 DLL 中找到，会打印提示信息后正常连接。

### JLinkGDBServer 启动超时 / 端口冲突

**现象**：`JLinkGDBServer 启动超时，GDB 端口未就绪`。

**原因**：上次异常退出（如 Ctrl+C）后 JLinkGDBServer 进程未清理，端口 2331 仍被占用。

**解决**：脚本在启动前和结束后均自动执行 `taskkill`（Windows）或 `pkill`（Linux）清理僵尸进程。
