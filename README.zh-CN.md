# Math Worksheets Skill

[English](README.md) | 简体中文

[![checks](https://github.com/Tommie-P-xl/math-worksheets-skill/actions/workflows/tests.yml/badge.svg)](https://github.com/Tommie-P-xl/math-worksheets-skill/actions/workflows/tests.yml)
[![release](https://img.shields.io/github/v/release/Tommie-P-xl/math-worksheets-skill)](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest)
[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

告诉 AI 你想练什么，或直接提供题目文字、截图、照片，生成可打印的数学练习 PDF。
支持基础算术到 AP 微积分，可独立求解、验算答案，并用程序绘制数学图形。
使用 Agent 已有的模型与工具，不需要专用的出题服务。

[效果展示](#效果展示) · [安装](#安装) · [使用模板](#使用模板) · [工作方式](#工作方式)

## 效果展示

### 功能一：生成练习题

| 学生练习册 | 答案册 | 知识点总结 |
|:---:|:---:|:---:|
| [<img src="docs/samples/upstream/worksheet_geometry-1.png" width="250" alt="几何练习册">](docs/samples/upstream/worksheet_geometry-1.png) | [<img src="docs/samples/upstream/answerkey_geometry-1.png" width="250" alt="分步答案册">](docs/samples/upstream/answerkey_geometry-1.png) | [<img src="docs/samples/upstream/skills_summary-1.png" width="250" alt="知识点总结">](docs/samples/upstream/skills_summary-1.png) |
| 数学图形与可打印题目 | 快速答案与解题步骤 | 公式、例题和独立尝试题 |

这组展示练习册、答案册和知识点总结的形式，示例来源见文末。
还可查看[数据处理练习册](docs/samples/upstream/worksheet_data-1.png)
和[答案册总结页](docs/samples/upstream/answerkey_summary_page.png)。
这组预览演示了留答题空间的排版；当前默认采用紧凑型，效果见功能二。
需要留空白作答区域时，请在提示中明确说明。

### 功能二：复现已有题目

| 用户原始照片 | 重排后的学生练习册 | 含说明图的简洁答案册 |
|:---:|:---:|:---:|
| [<img src="docs/examples/photo-folding/source.png" width="250" alt="有手写批注的原始题目照片">](docs/examples/photo-folding/source.png) | [<img src="docs/examples/photo-folding/worksheet.png" width="250" alt="中文题目复现效果">](docs/examples/photo-folding/ws_photo_folding.pdf) | [<img src="docs/examples/photo-folding/answer-key.png" width="250" alt="几何折叠解答与说明图">](docs/examples/photo-folding/ak_photo_folding.pdf) |
| 留存原始输入作为核对依据 | 排除手写过程，程序重绘两幅图 | 独立求解，在答案中补充必要图示 |

这组是本 fork **实际生成并检查的结果**：保留原题三问，生成 1 页学生练习册、
2 页答案册；答案预览展示含说明图的解答页，第 2 页为验证摘要。第三问结果为
`CP = 9√5/5`。10 项数学检查通过，2 项几何理由保留人工审核标记。

[下载练习册 PDF](docs/examples/photo-folding/ws_photo_folding.pdf) ·
[下载完整答案册 PDF](docs/examples/photo-folding/ak_photo_folding.pdf) ·
[查看题干核对记录、使用提示与复现方法](docs/examples/photo-folding/README.md)

## 安装

### 方式一：使用 CC Switch 安装 ZIP

1. 打开 [Releases](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest)，
   下载名称为 **`math-worksheets-v*.zip`** 的附件。
2. 打开 **CC Switch → Skills → 从 ZIP 安装**，选择下载的 ZIP。
3. 将技能启用或同步到 Claude Code、Codex 等需要使用的 Agent。
4. 按下面的说明准备运行依赖。若 Agent 尚未显示该技能，重启，或直接指定安装目录的 `SKILL.md`。

ZIP 中只有一个 `math-worksheets/` 目录，包含技能入口、脚本、模板、参考资料和许可。
README 图片、示例 PDF、测试和发布工具不进入安装包。每个发布版本附带 SHA-256 校验文件。
操作界面可参考 [CC Switch 技能管理说明](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/zh/3-extensions/3.3-skills.md)。

### 方式二：手动安装

解压同一个 ZIP，把其中的 **`math-worksheets` 文件夹**放入对应的个人技能目录：

| Agent | 安装位置 |
|---|---|
| Claude Code | `~/.claude/skills/math-worksheets/` |
| Codex | `~/.agents/skills/math-worksheets/` |
| 其他 Agent | 对应的技能目录，或直接在提示中指定 `SKILL.md` |

Codex 可以用 `$math-worksheets` 显式调用；其他 Agent 可直接使用后面的自然语言模板。
Codex 的技能加载方式见[官方说明](https://learn.chatgpt.com/docs/build-skills)。
如果要查看或开发源码，也可以克隆仓库：

```bash
git clone --depth 1 https://github.com/Tommie-P-xl/math-worksheets-skill.git
```

随后告诉 Agent：`请按照 /绝对路径/math-worksheets-skill/SKILL.md 制作练习册。`

### 运行依赖

| 工具 | 用途 |
|---|---|
| Bash | 执行构建流程；Windows 可使用 Git Bash 或 MSYS2 |
| Python + SymPy ≥1.12 | 验算答案；建议使用上游评测基线版本 1.14.0 |
| Tectonic 或 pdflatex | 编译普通 LaTeX 文档，需要 pgfplots ≥1.18 |
| XeLaTeX 与中文字体 | 编译中文示例；本例使用 ctex 与 Fandol 字体 |
| Poppler 的 `pdftotext` | 检查成品 PDF 中的文字位置和重叠 |

```bash
python -m pip install "sympy==1.14.0"
```

LaTeX 可以使用 [Tectonic](https://github.com/tectonic-typesetting/tectonic/releases)
或已有的 TeX 发行版。Debian/Ubuntu 的中文编译依赖包括 `texlive-xetex`、
`texlive-lang-chinese`；PDF 工具由 `poppler-utils` 提供。

Windows 需要在 Bash 中运行脚本，并确保能找到 Python、TeX 和 `pdftotext`。
多个 Python 并存时，用 `MWS_PYTHON` 指定已安装 SymPy 的解释器。
中文文档可设置 `MWS_LATEX_ENGINE=xelatex`；自动模式会识别 ctex/xeCJK/fontspec 源文件。

## 使用模板

题目默认紧凑排列，不在题干之间留答题空间；原题中的填空位置保留。
只有明确要求时才增加作答区域。几何字母采用透明背景，并放在不与线条相交的位置。

### 通用模板

```text
使用 math-worksheets。
模式：[新出练习题 / 复现已有题目 / 仅制作知识点总结]
输入或主题：[知识点、粘贴的题目文字，或附上的截图/照片]
年级和题量：[新出题时填写；复现时保留原题，不增加题目]
语言和纸张：[中文/英文等；A4/Letter]
交付：[练习册+简洁答案+总结 / 练习册+答案 / 仅学生练习册]
图形：数学图形优先用程序重绘，复杂照片先询问处理方案。
答案：独立求解、验算可计算结果，说明精简但保留关键推理。
输出目录：[指定文件夹]
```

### 功能一使用模板：生成练习题

| 场景 | 可直接复制的使用提示 |
|---|---|
| 正弦定理、余弦定理 | `使用 math-worksheets，给 Leo 出 8 道正弦定理和余弦定理练习，每题配图，附分步答案和知识点总结。` |
| 小学乘法 | `给三年级学生 Lucy 制作 12 道乘法表练习，附答案册和知识点总结。` |
| 因式分解 | `给八年级学生出 15 道三项式因式分解题，难度逐渐增加，附简洁分步解答。` |
| 统计与数据读取 | `制作 8 道读取柱状图并计算平均数、中位数、众数和极差的题，附图表、验算答案和复习页。` |
| 微积分 | `制作 10 道 AP 微积分链式法则练习，附分步答案和简短的求导公式总结。` |
| 分层练习 | `围绕 8.EE.C.8 方程组标准制作基础、常规、挑战三个层次的练习册，每层单独验算并附答案。` |
| 参考照片风格另出题 | `把这张作业照片作为风格和难度参考，另外出 10 道新的多项式图像题，使用匹配的坐标网格并附解答。` |

“参考照片风格另出题”会生成**新题**；如果需要保留照片中的原题，请用下面的复现模板。

### 功能二使用模板：复现与解释题目

**将题目文字排成 PDF**

```text
使用 math-worksheets，把下面的题目文字整理成 A4 PDF。
保留原题题干、数值、选项与顺序，不增加题目。
有函数图像或几何图形时优先程序重绘，独立求解并生成简洁答案册。
[在这里粘贴题目]
```

**复现带手写内容的截图/照片：上面的实际示例**

```text
使用 math-worksheets，将附上的几何题照片复现为中文 A4 练习册。
保留原题三问、点名、条件与顺序，不另出题。
区分印刷题干与手写批注，学生版不保留手写答案。
如果重要符号或图形标注被遮挡、无法确认，先问我，不要猜。
两幅数学图形用程序重绘。独立求解并验算，制作简洁答案册。
最后一问增加必要的说明图，不需要知识点总结。
全部文件保存到我指定的输出目录。
```

**只交付学生练习册**

```text
使用 math-worksheets 复现这些已有题目，只交付空白的学生练习 PDF。
答案仍在内部独立求解和验算，但不输出答案册。
去除手写过程，学生图中不添加答案专用的辅助线和计算结果。
```

**题干含火车、照片等复杂插图**

```text
将这道含火车/实景照片的题排成练习册，数学图形用程序重绘。
复杂图片请先提供处理选择：我补充干净截图、可用时借助生图、
用不影响解题的程序示意图，让我选定后再处理。
不要根据猜测的答案补造看不清的标注或已知条件。
```

**需要图形化解释的答案**

```text
为这些函数或几何题制作简洁答案册，独立求解验算。
涉及交点、辅助线、折叠或抽象步骤时，适当用程序加一幅说明图。
文字只保留关键推理，答案专用信息不要出现在学生练习册中。
```

**只制作知识点总结**

```text
围绕[主题]制作两页知识点总结，包含公式、分步例题和独立尝试题。
验算所有计算结果，不额外生成练习册。
```

## 工作方式

Agent 出题或转录题目、独立求解，并写入 LaTeX 与验证 JSON。
构建流程检查数学结果、作答项覆盖、单位、文档一致性和作答空间，
编译 PDF 后再检查文字重叠。复现模式额外绑定题目审核记录与外部图片文件。

| 模式 | 默认输出 |
|---|---|
| 新出题 | 练习册、答案册、知识点总结 |
| 复现已有题目 | 练习册、答案册；总结可选 |
| 仅学生练习册 | 学生 PDF；内部仍验算答案 |
| 仅知识点总结 | 含已验算例题的总结 PDF |

证明、开放解释、OCR 忠实度和外部图片内容仍需要审核。
CAS 通过表示支持的数学计算通过检查，不代表每句证明和所有图形细节都已自动验证；
图片审核记录也不等于机器证明。

## 来源与许可

基于 [stellawuellner/math-worksheets-skill](https://github.com/stellawuellner/math-worksheets-skill)，
保留其数学验证器、模板和参考资料。原有预览来自上游提交 `21312be`；
中文拍照题示例由本 fork 实际生成和检查。使用 [MIT 许可](LICENSE)。
