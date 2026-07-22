---
name: bmu-debug
description: BMU（电池管理单元，RA2L1+MP2797 平台）完整调试——J-Link 烧录/校验、CAN 总线通信、GDB 断点/寄存器/回溯调试。内置编址规则（0xC8+BMU ID）、请求/回复 ID 组帧公式、命令字典和全套脚本。当用户提到 BMU 调试、烧录 BMU、刷固件、BMS 通信测试、查询 BMU 电压/温度/UID、强制均衡、看门狗测试、恢复出厂、CAN 报文无回复、HardFault 排查、上位机联调、产线工位测试时使用。
---

# BMU 调试

BMU 是**被动响应**设备：不发请求就一帧数据都没有（除非开了主动上传）。J-Link（SWD）和 GCAN（CAN）可同时连接，互不冲突。

---

## 一、硬件参数

### J-Link（烧录 & 调试）

| 项目 | 值 |
|------|-----|
| 目标芯片 | **R7FA2L1AB** |
| 接口 | SWD，4000 kHz |

烧录用 `/flash-jlink`，调试用 `/debug-jlink`。本 skill 提供 BMU 专用参数，J-Link 通用操作见各 skill 自身文档。

### GCAN（CAN 通信）

| 项目 | 值 |
|------|-----|
| 适配器 | 广成 GCAN，vci 接口，`ControlCAN_GC.dll`（CX DLL 不可用） |
| Python | **32-bit** `py -3.11-32` |
| 波特率 | 250 kbps，CAN1（通道 1），扩展帧 |

VCI 设备单进程独占，收发必须在同一进程内完成。

---

## 二、固件烧录

### 支持格式

| 格式 | 完整包 | 仅 APP | 备注 |
|------|--------|--------|------|
| HEX | ✅ | ✅ | 推荐 |
| ELF | ✅ | ✅ | 可按段擦写，不误伤 bootloader |
| BIN | ✅（需 `--base-address`） | ❌ | 无地址信息 |
| S19/SREC | 先用 `srec_cat` 转 HEX | 同左 | JLinkExe 不原生支持 |

### 烧录命令

```bash
/flash-jlink --artifact <固件> --device R7FA2L1AB
```

HEX 用于完整包（含 bootloader），ELF 用于日常仅刷 APP。烧录后自动校验+硬件复位。

### 复位

- **硬件复位**：`/flash-jlink` 烧录后自动执行；也可用 `/debug-jlink --mode attach-only` 附着后发 reset。
- **CAN 软件复位**：通过 CAN 发复位命令（见 commands.md），适用于无 J-Link 场景，不适用于 CPU 已卡死状态。

---

## 三、CAN 通信

### 编址与组帧

BMU 地址 = `0xC8 + ExtAddr`（ExtAddr 出厂默认 1，SA=0xC9）；主机地址固定 `0xC8`。

```
请求: ID = (6<<26) | (CMD<<16) | ((0xC8+BMU_ID)<<8) | 0xC8
回复: ID = (6<<26) | (RESP_PF<<16) | (0xC8<<8) | (0xC8+BMU_ID)
```

例如 BMU1 UID 查询：请求 `0x18FD C9 C8`，回复 `0x18FD C8 C9`。

**高频错误**：

1. PS=目标=BMU，SA=源=主机=0xC8，**不要搞反**（`...C9 C8` 正确，`...C8 C9` 在请求中是错的）。
2. 回复 PF ≠ 请求 PF（UID 查询例外），不要用请求 PF 等回复。
3. 主机 SA 不能等于 BMU 地址，否则被固件自回环过滤丢弃。

固件不校验 PS，但不要依赖这一点。

### 脚本工具（scripts/）

所有脚本共享 `bmu_common.py`（连接/组帧/解码/CSV 日志），默认 GCAN 参数，可用 `--channel/--bitrate/--dll` 覆盖。

| 脚本 | 用途 |
|------|------|
| `bmu_cmd.py` | 发单条命令，`--cmd <PF> [--data <hex>] [--bmu <id>] [--listen <秒>]`。不足 8 字节自动补 0；危险帧需 `--yes` |
| `bmu_scan.py` | 心跳扫描 1~40 号 BMU，列出在线节点，`--range` 限定范围 |
| `bmu_batch.py` | 按脚本文件批量发送，格式：`<间隔ms> <命令hex> [数据hex]` |
| `bmu_equi_status.py` | 均衡状态位图解码，`--cells-per-afe 0` 关闭 AFE 分组 |

命令 PF 查 [commands.md](references/commands.md)。收发带毫秒时间戳打印 + CSV 日志。

---

## 四、GDB 调试

使用 `/debug-jlink`，设备固定 `R7FA2L1AB`。

| 模式 | 用途 |
|------|------|
| `attach-only` | 附着运行中的 BMU，查看寄存器/内存/栈，不影响 CAN 通信 |
| `crash-context` | 停核读 Fault 寄存器（CFSR/HFSR/MMFAR/BFAR）+ LR 链回溯，排查 HardFault |
| `download-and-halt` | 下载 ELF 并停在入口 |

常见 Fault：IACCVIOL（野指针跳转）、DACCVIOL（外设未初始化就访问）、UNALIGNED（CAN 帧非对齐取值）、UNDEFINSTR（栈被覆写）。

BMU 开了 ITM 输出的，可用 `--swo` 捕获，不占串口。

---

## 五、常见坑

1. **均衡模式冲突**：Flash 旧参数致 EnBal≠0，手动均衡被忽略。临时切手动（系统状态帧 Byte7=0，RAM 生效），或恢复出厂（持久但清校准值）。
2. **单通道均衡位累加**：连续发多条叠加开启，关均衡必须显式发关闭帧。
3. **看门狗测试不可逆**：密钥匹配后 BMU 死循环，仅靠外部看门狗（~1.6s）恢复。回复确认帧后总线沉默正常，等 8 秒再验证。
4. **陌生帧不是 BMU 的**：菊花链其他节点会发帧。按 SA = 0xC8+BMU_ID 过滤。
5. **GC DLL 间歇性 TX 失败**：拔插 USB 重试（已内置 200ms 延迟+3 次重试）。
6. **CAN 5 秒无接收触发重初始化**（CAN0_RX_TIMEOUT_SEC=5）：久不发命令后首帧偶发丢失，重发即可。
7. **烧录后首帧丢失**：复位到 CAN 就绪约 100ms，稍等或重发。
8. **回复 PF 与文档不一致**：固件版本差异，以 `bmu_cmd.py` 实际解码为准。

---

## 六、命令字典

[references/commands.md](references/commands.md) — 请求/回复格式、产线命令、复位子命令、查询类速查表。组包前先查，不要凭记忆。
