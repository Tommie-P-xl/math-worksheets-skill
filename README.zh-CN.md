<a id="readme-top"></a>

<div align="center">

<h1>Math Worksheets Skill</h1>
<p><strong>为 AI Agent 提供数学出题、原题复现与可积累的命题经验</strong></p>

<p>
  <a href="https://github.com/Tommie-P-xl/math-worksheets-skill/actions/workflows/tests.yml"><img src="https://github.com/Tommie-P-xl/math-worksheets-skill/actions/workflows/tests.yml/badge.svg" alt="Checks"></a>
  <a href="https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest"><img src="https://img.shields.io/github/v/release/Tommie-P-xl/math-worksheets-skill?label=release&amp;color=2563eb" alt="Latest release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-64748b" alt="MIT license"></a>
</p>

<p><a href="README.zh-CN.md">简体中文</a> &nbsp;|&nbsp; <a href="README.md">English</a></p>
<p><a href="#quick-start">快速开始</a> &nbsp;·&nbsp; <a href="#效果展示">效果展示</a> &nbsp;·&nbsp; <a href="#全局题库">全局题库</a> &nbsp;·&nbsp; <a href="#使用模板">使用模板</a></p>

</div>


告诉 AI 你想练什么，或直接提供题目文字、截图、照片，生成可打印的数学练习 PDF。
支持基础算术到 AP 微积分，可独立求解、验算答案，并用程序绘制数学图形。
使用 Agent 已有的模型与工具，不需要专用的出题服务。

可选的全局题库提供参考题目和命题经验。**默认不收藏**：每道题及每次命题文档更新，
都需要用户分别审核、确认后保存。详见[题库使用说明](references/question-bank.md)。

| 新出题 | 原题复现 | 全局参考题库 |
|:---|:---|:---|
| 围绕已学知识设计练习，独立求解，输出题目、答案与可选总结。 | 核对照片与手写干扰，保留原题条件，用代码重绘数学图形。 | 复用已批准题目与命题经验，默认不收录，跨项目使用。 |


<details>
<summary>文档导航</summary>

- [快速开始](#quick-start)
- [效果展示](#效果展示)
- [安装](#安装)
- [使用模板](#使用模板)
- [工作方式](#工作方式)
- [全局题库](#全局题库)
- [版本与构建](#版本与构建)
- [来源与许可](#来源与许可)

</details>


---

<a id="quick-start"></a>

## 快速开始

| 1 · 安装 Skill | 2 · 准备运行环境 | 3 · 交给 Agent |
|---|---|---|
| 从 [Releases](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest) 下载 `math-worksheets.zip`，通过 CC Switch 或手动安装。 | 仅管理题库需要 Python；生成 PDF 还需要 Bash、SymPy、LaTeX 和 Poppler，[完整依赖见下文](#运行依赖)。 | 说明知识范围、数量、语言与交付物，或提供题目照片并指定复现。 |

```text
使用 math-worksheets，参考我上传的题目，出 4 道同类型的新题。
先确认年级与已学知识，保持原题的考查结构和难度梯度。
输出中文 A4 练习册与详细答案，题目和答案分页。
每道题和命题文档都先询问我，未确认前不要收录到全局题库。
```

> **先选工作模式：**参考图出新题用“新出题”；保留原题文字和数字用“复现”。
> 数学验证不等于所有证明或图形细节均已自动证明，审核边界见[工作方式](#工作方式)。


---

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

<p align="right"><a href="#readme-top">返回顶部</a></p>


---

## 安装

### 方式一：使用 CC Switch 安装 ZIP

1. 打开 [Releases](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest)，
   下载名称为 **`math-worksheets.zip`** 的附件。
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
| Python ≥3.10 + SymPy ≥1.12 | 验算答案；建议使用上游评测基线版本 1.14.0 |
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

<p align="right"><a href="#readme-top">返回顶部</a></p>


---

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


<details>
<summary>将题目文字排成 PDF</summary>

**将题目文字排成 PDF**

```text
使用 math-worksheets，把下面的题目文字整理成 A4 PDF。
保留原题题干、数值、选项与顺序，不增加题目。
有函数图像或几何图形时优先程序重绘，独立求解并生成简洁答案册。
[在这里粘贴题目]
```

</details>

<details>
<summary>复现带手写内容的截图/照片：上面的实际示例</summary>

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

</details>

<details>
<summary>只交付学生练习册</summary>

**只交付学生练习册**

```text
使用 math-worksheets 复现这些已有题目，只交付空白的学生练习 PDF。
答案仍在内部独立求解和验算，但不输出答案册。
去除手写过程，学生图中不添加答案专用的辅助线和计算结果。
```

</details>

<details>
<summary>题干含火车、照片等复杂插图</summary>

**题干含火车、照片等复杂插图**

```text
将这道含火车/实景照片的题排成练习册，数学图形用程序重绘。
复杂图片请先提供处理选择：我补充干净截图、可用时借助生图、
用不影响解题的程序示意图，让我选定后再处理。
不要根据猜测的答案补造看不清的标注或已知条件。
```

</details>

<details>
<summary>需要图形化解释的答案</summary>

**需要图形化解释的答案**

```text
为这些函数或几何题制作简洁答案册，独立求解验算。
解答中凡是添加辅助线、垂足、交点或对称点，务必画出添加后的图形并标注。
答案里的分式（包括中间步骤、坐标和分数指数）统一使用 LaTeX 分式命令，不用斜杠。
文字只保留关键推理，答案专用信息不要出现在学生练习册中。
```

</details>

<details>
<summary>只制作知识点总结</summary>

**只制作知识点总结**

```text
围绕[主题]制作两页知识点总结，包含公式、分步例题和独立尝试题。
验算所有计算结果，不额外生成练习册。
```

</details>


<p align="right"><a href="#readme-top">返回顶部</a></p>


---

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

<p align="right"><a href="#readme-top">返回顶部</a></p>


---

## 全局题库

题库使用 **纯文本与代码题库**：每题保存完整题面、答案、逐步解答、标签、
难度分析、语义图形条件与 TikZ/pgfplots/SVG 绘图代码。函数图像和辅助线也用
代码描述，AI 读取文字即可理解参考题，无需再打开图片。
照片仍可作为本次整理的输入；题库仅保存原文件名、题号/页码、哈希或 URL 等
来源信息，不复制原图。全局数据不会打入安装包。

每道题仍需用户确认后收录。入库或修订后，Agent 检查对应命题指南：有新的
可复用方法就提出精简更新并取得批准；现有内容已覆盖时，记录检查结论。
`guide-status` 按题目 ID 与修订版本显示尚未审阅的记录，避免指南长期漏更新。
指南仍是每个学段/学科唯一、可直接编辑的 Markdown 文件。

### 数据位置与实时配置

| 系统 | 默认位置 |
| --- | --- |
| Windows | `%LOCALAPPDATA%/MathWorksheets` |
| macOS | `~/Library/Application Support/MathWorksheets` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/math-worksheets` |

`MWS_DATA_HOME` 或 `--home` 可指定位置；数据位于 skill 安装目录之外，重装不会覆盖。
运行 `config --init` 可生成完整 `config.json`。常用数值与开关集中在这个文件，
修改后下一次命令或构建立即生效，详见[配置说明](references/configuration.md)。

配置文件保持标准JSON格式；`_comments`为每个参数提供中文简要说明和默认值，
读取配置时只使用实际参数值。运行`config --init`可补齐参数、刷新说明，并保留
已有有效设置；旧的不带说明的配置仍可读取。

<details>
<summary>全部配置参数、默认值与作用</summary>

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `guide_max_chars` | `6000` | 单份学段/学科命题指南的字符上限，含标题和链接；范围500–12000。 |
| `backup_keep` | `1` | 自动备份保留代数，范围1–100；手动备份不自动删除。 |
| `auto_backup_enabled` | `true` | 是否在写入前自动备份上一代已提交数据。 |
| `reference_limit` | `10` | 每次命题可参考的不同题目和指南总上限，范围1–100。 |
| `reference_default` | `5` | 单次检索默认返回的参考数量，包含指南；不得大于reference_limit。 |
| `context_max_chars` | `10000` | 单次检索结果的默认字符预算，至少1200且不超过context_max_chars_limit。 |
| `context_max_chars_limit` | `50000` | 允许指定的检索字符预算上限，不超过1000000。 |
| `guide_excerpt_chars` | `2400` | 检索结果中命题指南节选的字符上限。 |
| `stem_excerpt_chars` | `1600` | 检索结果中每题题面节选的字符上限。 |
| `answer_excerpt_chars` | `500` | 检索结果中每题答案节选的字符上限。 |
| `solution_excerpt_chars` | `900` | 检索结果中每题解答节选的字符上限；完整内容用show读取。 |
| `givens_excerpt_chars` | `1200` | 检索结果中每题图形已知关系节选的字符上限。 |
| `duplicate_threshold` | `0.82` | 疑似重复题的文本相似度阈值，大于0且不超过1。 |
| `duplicate_scan_limit` | `300` | 检查疑似重复题时比较的最近题目数量。 |
| `duplicate_candidate_limit` | `5` | 预览时最多显示多少个疑似重复题候选。 |
| `guide_review_on_commit` | `true` | 题目入库或修订后是否要求Agent检查命题指南覆盖情况。 |
| `default_question_count` | `10` | 用户未指定数量时，Agent默认生成的练习题数。 |
| `page_margin_left_mm` | `12` | PDF正文左页边距，单位毫米；范围5–50。 |
| `page_margin_right_mm` | `12` | PDF正文右页边距，单位毫米；范围5–50。 |
| `page_margin_top_mm` | `12` | PDF正文上页边距，单位毫米；范围5–50，启用页眉时需留足空间。 |
| `page_margin_bottom_mm` | `12` | PDF正文下页边距，单位毫米；范围5–50。 |
| `page_numbers` | `true` | 是否显示模板页码。 |
| `name_date_fields` | `false` | 是否显示首页姓名/日期填写栏；栏名由文档按所用语言提供。 |
| `header_rule` | `false` | 是否显示页眉下方的分隔横线。 |
| `quick_answers` | `false` | 是否生成答案速查表；不自动追加验证或课程总结页。 |
| `problem_gap_mm` | `1.5` | 紧凑排版时题目之间的间距，单位毫米，可使用小数。 |
| `answer_problem_gap_mm` | `2` | 答案册相邻题目之间的间距，单位毫米，使用正整数。 |

</details>

自动备份在每次写入前保存上一代状态，按配置保留代数；手动命名的备份不自动删除。
备份包含数据库、指南、配置和校验清单，不含图片。

### 升级已有题库

先安装更新后的 skill，再查看迁移计划，确认后执行。迁移保持题目 ID、修订号、完整解答和
绘图代码，移除当前记录及审计历史中的图片依赖，验证文本备份后清理题库原图。
如果解答还依赖图片，迁移会报错，需要先补齐文本/代码；不会自行猜补答案。

```bash
python SKILL_DIR/scripts/question_bank.py migrate
python SKILL_DIR/scripts/question_bank.py migrate --apply --backup-keep 1
python SKILL_DIR/scripts/question_bank.py doctor
python SKILL_DIR/scripts/question_bank.py stats
python SKILL_DIR/scripts/question_bank.py config --init
python SKILL_DIR/scripts/question_bank.py guide-status --stage 初中 --subject 数学
python SKILL_DIR/scripts/question_bank.py show QUESTION_ID
python SKILL_DIR/scripts/question_bank.py backup --out /chosen/path/bank.zip
```

`SKILL_DIR` 请替换为实际安装路径；Windows PowerShell 对含空格路径加引号。
完整命令、题目 JSON、逐题审核和恢复方式见[题库说明](references/question-bank.md)。
旧版 ZIP 先用兼容旧版的 skill 恢复到独立目录，再迁移到 schema 2。

### PDF 模板

默认采用紧凑排版与 12 mm 页边距。模板只输出传入的标题、内容与可选页码，
不会自动追加英文姓名日期、续页提示、学习口号、课程标准或验证总结页。
正文语言由任务决定。需要姓名栏、额外标签或速查表时再明确启用。
历史展示图保留用于说明功能，不代表当前默认样式。


---

## 版本与构建

skill 版本号只保存在根目录 [`VERSION`](VERSION)。
[`tools/version.py`](tools/version.py) 读取它并校验发布标签。
源文件、文档与固定名称的 `math-worksheets.zip` 不重复保存 skill 版本号，
GitHub 发布标签与标题在发布时自动派生。

| 产物 | 获取方式 |
|---|---|
| 安装包与校验文件 | [最新 Release](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest) 提供 `math-worksheets.zip` 和 `.zip.sha256`。 |
| 源码与更新记录 | [源码](https://github.com/Tommie-P-xl/math-worksheets-skill) · [发布说明](RELEASE_NOTES.md) · [维护工具](tools/README.md) |

<details>
<summary>展开：维护者构建与验证命令</summary>

```bash
python tools/version.py
python tools/version.py --tag
python tools/package_skill.py
python -m unittest discover -s tests -v
```

构建输出到 `dist/`，ZIP 内只有 `math-worksheets/` 运行目录。
GitHub Release 流程校验标签、构建安装包、运行测试后发布 ZIP 与 SHA-256 文件。
运行完整测试需要上述 PDF 依赖；个人题库、原件与备份不进入发布包。

</details>


<p align="right"><a href="#readme-top">返回顶部</a></p>


---

## 来源与许可

基于 [stellawuellner/math-worksheets-skill](https://github.com/stellawuellner/math-worksheets-skill)，
保留其数学验证器、模板和参考资料。原有预览来自上游提交 `21312be`；
中文拍照题示例由本 fork 实际生成和检查。使用 [MIT 许可](LICENSE)。

<p align="right"><a href="#readme-top">返回顶部</a></p>
