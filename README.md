# Claude Skills

我的 Claude Code 技能集合，用于增强 Claude 的专项能力。

## 技能列表

| 技能 | 说明 |
|------|------|
| **Git 提交助手** (`git-commit-helper`) | 分析未提交变更、按功能域分批提交、自动维护变更日志 |
| **技能创建器** (`skill-creator`) | 创建、测试、评估和优化 Claude Code 技能 |
| **工程变更比对** (`project-diff 工程变更比对`) | 智能对比两个代码工程，生成功能级变更报告 |
| **命令提醒** (`cmd-nav 命令提醒`) | 用中文描述需求时自动推荐对应的内置技能 |
| **Draw.io 转 Mermaid** (`drawio-to-mermaid`) | 将 draw.io 流程图文件转换为 Mermaid 语法 |
| **Word 文档处理** (`docx`) | 创建、编辑和分析 .docx 文件，支持修订标记、批注等 |
| **PDF 处理** (`pdf`) | 提取文本/表格、创建 PDF、合并/拆分文档、表单填写 |
| **PPT 处理** (`pptx`) | 创建、编辑和分析 .pptx 演示文稿 |
| **Excel 处理** (`xlsx`) | 创建、编辑和分析电子表格，支持公式、图表、数据可视化 |
| **RA 编译验证** (`ra-build`) | RA MCU 工程编译验证，支持命令行一键构建 |

## 目录结构

```
.claude/skills/
├── README.md
├── .gitignore
├── git-commit-helper/          # Git 提交助手
│   └── SKILL.md
├── cmd-nav 命令提醒/           # 中文技能导航
│   ├── SKILL.md
│   └── evals/
├── project-diff 工程变更比对/  # 工程变更比对
│   ├── SKILL.md
│   ├── evals/
│   └── scripts/
├── drawio-to-mermaid/           # Draw.io 转 Mermaid
│   └── SKILL.md
├── docx/                        # Word 文档处理
│   ├── SKILL.md
│   ├── ooxml/
│   └── scripts/
├── pdf/                         # PDF 处理
│   ├── SKILL.md
│   └── scripts/
├── pptx/                        # PPT 处理
│   ├── SKILL.md
│   ├── ooxml/
│   └── scripts/
├── xlsx/                        # Excel 处理
│   ├── SKILL.md
│   └── recalc.py
├── ra-build/                   # RA MCU 编译验证
│   └── SKILL.md
├── skill-creator/              # 技能创建器
│   ├── SKILL.md
│   ├── agents/                 # 评估子代理定义
│   ├── eval-viewer/            # 评估结果查看器
│   ├── references/             # 参考文档
│   └── scripts/                # 工具脚本
└── *-workspace/                # 技能测试工作区（不纳入版本控制）
```

## 安装

将本仓库克隆到 `~/.claude/skills/` 目录：

```bash
git clone https://github.com/LiTianYun/claude-skills.git ~/.claude/skills/
```

Claude Code 会自动识别该目录下的技能。

## 来源说明

- **Office 文档技能**（`docx`、`pdf`、`pptx`、`xlsx`）基于 [appautomaton/document-SKILLs](https://github.com/appautomaton/document-SKILLs) 改进，上游仓库以 MIT 许可证发布。

---

## 变更日志

<!-- 新条目添加在最上方 -->

### 2026-07-08

- **feat**: 新增 Office 文档处理技能（`docx`、`pdf`、`pptx`、`xlsx`），基于 document-SKILLs 改进
- **feat**: 新增 Draw.io 转 Mermaid 流程图技能（`drawio-to-mermaid`）
- **fix**: 修正技能 name 字段为纯英文标识符（`cmd-nav`、`project-diff`）

### 2026-06-18

- **feat**: 新增 RA MCU 编译验证技能，支持 e² studio 工程命令行一键构建（`ra-build`）
- **refactor**: 技能目录重命名为中英双语格式，提升 CLI 输入体验（`cmd-nav 命令提醒`、`project-diff 工程变更比对`）

### 2026-06-17

- **feat**: 新增工程变更比对技能，智能识别源码/构建目录，生成功能级变更报告（`工程变更比对`）

### 2026-06-16

- **feat**: 新增命令提醒技能，用中文描述需求时自动推荐对应的内置技能（`命令提醒`）
- **feat**: 新增 Git 提交助手，支持按功能域分批提交和维护变更日志（`git-commit-helper`）
