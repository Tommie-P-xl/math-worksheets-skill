# Real screenshot example: Chinese geometry folding

This example was supplied by the repository owner's user request. The original
photo is preserved as [source.png](source.png); its handwritten answers and
working are not part of the reproduced student worksheet.

## Prompt

```text
使用 math-worksheets，将这张照片中的几何题复现为中文 A4 PDF。
保留原题三问、点名、条件和顺序；不要另出题。
区分印刷题干与手写批注，不将手写答案作为已知条件；有遮挡歧义时先问我。
两幅几何图用程序重绘，学生版不包含答案或解题辅助线。
独立求解并验算，生成简洁答案册；第三问加一幅必要的折叠说明图。
不需要知识点总结。输出到指定工作目录，并完成全部构建检查。
```

## Reviewed transcription

The source has three parts, kept in this order:

1. 正方形 $ABCD$，$E,Q$ 分别在 $BC,AB$ 上，$DQ\perp AE$ 于 $O$；
   $G,F$ 分别在 $CD,AB$ 上，$GF\perp AE$。填 $DQ$ 与 $AE$ 的大小关系，
   推断 $GF/AE$。
2. 矩形 $ABCD$，$BC/AB=k$。沿 $GF$ 折叠，使 $A$ 落到 $BC$ 上的 $E$，
   得四边形 $FEPG$；$EP$ 与 $CD$ 交于 $H$，$AE$ 与 $GF$ 交于 $O$。
   探究 $GF$ 与 $AE$ 的关系并说明理由。
3. 在（2）的条件下，连接 $CP$；$k=2/3$，$BE/BF=3/4$，$GF=2\sqrt{10}$，求 $CP$。

For readable typography, the student's numbered subparts use LaTeX-drawn circled
numbers rather than missing Unicode glyphs. The original photograph's two
diagrams are reconstructed with TikZ; placement changes, mathematical content does
not. Part (3) uses the same diagram as part (2), without answer-only $CP$ or
computed coordinates added to the student figure.

## Results and checks

- Part (1): $DQ=AE$ and $GF/AE=1$.
- Part (2): $GF=k\,AE$.
- Part (3): $CP=9\sqrt5/5$; $AB=9$, $BC=6$, $BE=3$, $BF=4$ and
  $P=(39/5,18/5)$.

`verify_photo_folding.json` carries 10 machine checks and 2 manual geometric
reasoning entries, across three original parts. The coordinate-based symbolic
checks in `geometry_checks.json` independently check perpendicularity, segment
ratios, folding reflection and the numerical application. The geometric prose
and reconstruction were reviewed; they are not described as automatically proved
by the standard CAS gate. The build correctly returns exit 2 for manual reasoning.

`DQ` is the full segment to $Q$ on $AB$, not the shorter perpendicular distance
$DO$ from $D$ to $AE$. This distinction is retained in the verification notes.

Rebuild from the repository root (XeLaTeX, Chinese fonts, Bash, SymPy and
pdftotext required):

```bash
python tools/build_photo_example.py
pdftoppm -scale-to 1600 -png -singlefile docs/examples/photo-folding/ws_photo_folding.pdf docs/examples/photo-folding/worksheet
pdftoppm -scale-to 1600 -png -singlefile docs/examples/photo-folding/ak_photo_folding.pdf docs/examples/photo-folding/answer-key
```

The rebuild script recreates reviewed LaTeX and validation data. Changes to the
transcription require review against the source before regenerating source-review
hashes. PDFs, source photo and README previews are documentation examples, excluded
from the runtime-only release ZIP.

The answer-key preview shows page 1 (all solutions and the explanatory figure).
Page 2 is the separate [verification summary](verification-summary.png). The PDF and preview images were
rendered and visually inspected after the complete gate chain passed.
