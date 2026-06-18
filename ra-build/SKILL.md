---
name: ra-build
description: RA MCU 工程编译验证。当用户提到"编译"、"构建"、"build"、"验证编译"、"编译验证"、"检查编译"、"编译看看"、"能编译吗"时调用此 skill。也适用于用户说"帮我编译这个RA项目"、"验证一下能不能编过"等场景。
---

# RA MCU 工程编译验证

调用 `ra_build.sh` 命令行脚本对 RA MCU 项目进行编译验证，输出编译结果和错误信息。

## 构建脚本

```
C:/Renesas/RA/ra_build.sh
```

## 工作原理

脚本从 e² studio GUI 工作区（`C:/WorkSpace/E2_RA_WorkSpace`）复制项目配置到构建工作区，然后通过 Eclipse CDT Headless Build 直接调用 ARM GCC 编译。不新建项目、不重新导入——确保编译行为与 GUI 完全一致。

配置：
- e² studio: `C:/Renesas/RA/e2studio_v2021-01_fsp_v2.3.0/eclipse`
- GUI 工作区: `C:/WorkSpace/E2_RA_WorkSpace`
- 构建工作区: `C:/Renesas/RA/.build_workspace`
- 工具链: ARM GCC 9.2.1

## 工作流程

### 1. 确定项目路径

按以下优先级确定：

1. **用户明确指定** — 用户说了具体路径，直接用
2. **当前工作目录** — 检查当前目录是否包含 `.project` 文件
3. **自动搜索** — 在附近目录搜索 `.project` 文件

### 2. 确认构建配置

默认构建配置为 `all`（所有配置）。若用户指定了 `Release`、`Debug` 等，则作为第二个参数传入。

### 3. 执行编译

```bash
bash "C:/Renesas/RA/ra_build.sh" "<项目路径>" [构建配置]
```

脚本自动完成：
- 首次运行时从 GUI 工作区复制 `.metadata`（排除 `.lock`）
- 增量同步新项目到构建工作区
- 对已注册项目直接 `-build`（无需 `-import`）
- 对新项目先 `-import` 再 `-build`

### 4. 更新 .gitignore（如有 Git 仓库）

编译完成后，检查项目路径是否在 Git 仓库内（向上查找 `.git` 目录）。若找到 `.git`，则确保 `.gitignore` 中包含以下条目（不存在则追加）：

```
# e² studio 构建产物
ra_build.log
Debug/
Release/
```

检查方式：
```bash
# 查找项目所属的 Git 仓库根目录
git_dir=$(git -C "<项目路径>" rev-parse --show-toplevel 2>/dev/null)
if [ -n "$git_dir" ]; then
    gitignore="${git_dir}/.gitignore"
    touch "$gitignore"
    for entry in "ra_build.log" "Debug/" "Release/"; do
        if ! grep -qxF "$entry" "$gitignore" 2>/dev/null; then
            echo "$entry" >> "$gitignore"
            echo "✓ 已添加 $entry → .gitignore"
        fi
    done
fi
```

### 5. 报告结果

- **退出码 0** → 编译成功
- **退出码 1** → 编译失败，展示错误详情
- **退出码 2** → 脚本/环境配置错误

编译日志: `<项目路径>/ra_build.log`

## 前置条件

- 项目须先在 e² studio GUI 中构建过一次
- 项目目录下必须有 `.project` 和 `.cproject` 文件
- e² studio GUI 工作区位于 `C:/WorkSpace/E2_RA_WorkSpace`

## 已知注意事项

- GUI 运行时 `.lock` 文件无法复制，脚本自动跳过
- 首次运行从 GUI 工作区复制配置，耗时稍长；后续构建直接使用缓存
- Eclipse NLS 警告已自动过滤，只统计真正的编译警告
