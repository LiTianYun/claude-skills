---
name: build-cmake
description: 当项目目录内存在 Build_Tool 可执行文件，需要通过它构建 CMake 工程、查询工具链状态或执行 post-build 流程时使用。
---

# 构建 CMake 工程（Build_Tool）

## 适用场景

- 项目目录内存在 `Build_Tool`（Windows 下可能为 `Build_Tool.exe`）。
- 用户希望对该工程执行编译、清理重建、查询工程/工具链状态，或运行 post-build 流程。
- 烧录或调试流程需要新的固件产物。

若项目目录内没有 `Build_Tool`，本 skill 不适用，应改用 `build-makefile` 或 `build-keil`。

## 执行步骤

1. 确认项目根目录存在 `Build_Tool` / `Build_Tool.exe`，并在该目录下执行命令。
2. 按需选择命令（见下方 CLI Reference）；默认构建使用 `--json` 以便解析产物路径。
3. 多工程场景用 `-f <file>` 指定工程文件，工程根不在当前目录时用 `-p <path>` 指定。
4. 根据退出码判断结果（见下方 Exit Codes），将产物路径交给下游烧录/调试 skill。

## Build_Tool — CLI Reference

### Commands

| 命令 | 说明 |
|---|---|
| `build_tool` | Launch GUI |
| `build_tool --status` | Query project/toolchain |
| `build_tool --json` | Build with JSON output |
| `build_tool --clean` | Clean rebuild |
| `build_tool -p <path>` | Specify project root |
| `build_tool -f <file>` | Specify project file (Keil multi-project) |
| `build_tool --timestamp` | Update Message.h timestamp |
| `build_tool --post-build` | Run post-build (hex->s19 + bootloader) |
| `build_tool --init [path]` | Initialize project scaffold |

### Exit Codes

| 退出码 | 含义 |
|---|---|
| `0` | Success |
| `1` | Build failed |
| `2` | Config error |

## 失败分流

- 退出码 `1`：构建失败，向用户报告工具输出中的错误信息。
- 退出码 `2`：配置错误（`project-config-error`），先用 `--status` 查询工程/工具链状态定位问题。
- 项目目录内找不到 `Build_Tool`：本 skill 不适用，不要猜测替代构建方式，提示用户确认工程类型。

## 交接关系

- 构建成功后，下一步烧录交给 `flash-openocd` 或 `flash-jlink`。
- 需要调试会话时，交给 `debug-gdb-openocd` 或 `debug-jlink`。
