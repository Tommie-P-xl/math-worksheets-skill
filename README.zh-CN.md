# Math Worksheets Skill

[English](README.md) | 简体中文

让 AI Agent 生成数学练习 PDF，或将文字、截图、拍照中的已有题目复现为
可打印练习册。独立求解后使用 SymPy 检查可计算答案，支持简洁答案册和知识点总结。

## 安装

1. 在 [Releases](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest)
   下载 `math-worksheets-v*.zip`。
2. 打开 **CC Switch → Skills → 从 ZIP 安装**，选择该文件，再启用到所需 Agent。
3. 依赖：Bash、Python + `sympy>=1.12`（建议 `1.14.0`）、Tectonic 或
   pdflatex（pgfplots >=1.18）、Poppler 的 `pdftotext`。

ZIP 只包含一个 `math-worksheets/` 技能目录及运行必需文件，不包含评测语料、
测试和发布工具。首次安装后，若 Agent 未识别技能，重启或直接指定 `SKILL.md`。

也可克隆仓库，让 Agent 按仓库中的 `SKILL.md` 操作。
Windows 可使用 Git Bash/MSYS2；确保该 Bash 能找到 Python、TeX 和 `pdftotext`。
多 Python 环境可用 `MWS_PYTHON` 指定已安装 SymPy 的解释器；不要直接在 PowerShell
中执行 Bash 脚本。

## 使用示例

**出题：**

> 使用 math-worksheets，生成 10 道一元二次方程练习，A4 纸，附简洁分步答案和知识点总结。

**复现题目：**

> 将这几张截图里的题目按原顺序排成 PDF。排除手写解答；看不清的条件先问我。
> 函数和几何图优先程序重绘，附独立验算后的简洁答案。

**只要练习册：**

> 把下面的题目文字生成 PDF，只交付学生版，内部仍求解验算。

复现模式不另出题，不默认添加复习页。复杂照片/插图会先询问处理方式：
用户补充干净截图 → 支持时使用生图工具 → 不影响解题的程序示意图。
难解或抽象的答案可增加必要的说明图，文字保持精简。

## 工作方式与边界

Agent 写题目、LaTeX 和验证 JSON；`scripts/build.sh` 执行验算、文档一致性、
单位、作答空间、编译日志和 PDF 文字重叠检查。复现模式额外绑定题目审核记录
与外部图片文件，避免修改后沿用旧审核记录。

证明、开放解释、图片内容和 OCR 忠实度仍需审核。图片审核记录不是 CAS 证明；
通过检查不代表每一步推理、所有图形细节和教学质量都已经自动验证。

源自 [stellawuellner/math-worksheets-skill](https://github.com/stellawuellner/math-worksheets-skill)，
保留上游数学验证和模板。MIT 许可，详见 [LICENSE](LICENSE)。
