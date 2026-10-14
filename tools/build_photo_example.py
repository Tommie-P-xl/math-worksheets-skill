"""Rebuild the documented Chinese folding example from reviewed transcription.

Read docs/examples/photo-folding/README.md before changing the transcription.
The optional --source argument preserves the original uploaded image once.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import sympy as s

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'docs/examples/photo-folding'
sys.path.insert(0, str(ROOT / 'scripts/checks'))
from _tex_segments import blank_comments, segment_spans
from check_sources import digest
sys.path.insert(0, str(ROOT / 'scripts'))
from geometry_labels import tikz_labels


def verify_geometry():
    h, w, t = s.symbols('h w t', positive=True)
    A, D, E = s.Matrix([0, h]), s.Matrix([w, h]), s.Matrix([t, 0])
    Q = s.Matrix([0, h-w*t/h])
    f = (h*h-t*t)/(2*h)
    F, G = s.Matrix([0, f]), s.Matrix([w, f+w*t/h])
    ae = E-A
    # DQ is the complete segment to Q on AB, not the shorter perpendicular DO.
    assert s.simplify((D-Q).dot(ae)) == 0
    assert s.simplify((D-Q).dot(D-Q)/ae.dot(ae)-(w/h)**2) == 0
    assert s.simplify((G-F).dot(ae)) == 0
    assert s.simplify((G-F).dot(G-F)/ae.dot(ae)-(w/h)**2) == 0
    M = (A+E)/2
    assert s.simplify((M-F).dot(ae)) == 0
    reflected_a = s.simplify(A-2*((A-M).dot(ae))/ae.dot(ae)*ae)
    assert reflected_a == E
    r = s.symbols('r', positive=True)
    roots = s.solve(s.Eq(2*r/(1-r*r), s.Rational(3,4)), r)
    assert roots == [s.Rational(1,3)]
    height = s.simplify(2*s.sqrt(10)/(s.Rational(2,3)*s.sqrt(1+roots[0]**2)))
    assert height == 9
    subs = {h: height, w: s.Rational(2,3)*height, t: roots[0]*height}
    P = s.simplify(D-2*((D-M).dot(ae))/ae.dot(ae)*ae).subs(subs)
    C = s.Matrix([6,0])
    cp = s.sqrt((P-C).dot(P-C))
    assert P == s.Matrix([s.Rational(39,5),s.Rational(18,5)])
    assert cp == 9*s.sqrt(5)/5
    assert f.subs(subs) == 4
    assert s.simplify((G-F).dot(G-F).subs(subs)) == 40
    return {'AB': '9', 'BC': '6', 'BE': '3', 'BF': '4',
            'P': ['39/5', '18/5'], 'CP': '9*sqrt(5)/5',
            'symbolic_checks': ['DQ perpendicular AE', 'DQ/AE=BC/AB',
                                'GF perpendicular AE', 'GF/AE=BC/AB',
                                'GF through midpoint AE', 'reflection A to E'],
            'proof_review': 'Geometric explanations remain manual; symbolic coordinate identities and application arithmetic independently checked.'}


def figure_square():
    return r'''
\begin{tikzpicture}[scale=.43,line cap=round,line join=round]
\coordinate (A) at (0,10); \coordinate (B) at (0,0);
\coordinate (C) at (10,0); \coordinate (D) at (10,10);
\coordinate (E) at (3,0); \coordinate (Q) at (0,7);
\coordinate (F) at (0,3); \coordinate (G) at (10,6);
\coordinate (O) at (.825688,7.247706);
\draw[thick] (A)--(B)--(C)--(D)--cycle;
\draw[thick] (A)--(E) (Q)--(D) (F)--(G);
\draw ($(O)+(.16,-.54)$)--($(O)+(.70,-.38)$)--($(O)+(.54,.16)$);
''' + tikz_labels(
        {'A':(0,10),'B':(0,0),'C':(10,0),'D':(10,10),'E':(3,0),
         'Q':(0,7),'F':(0,3),'G':(10,6),'O':(.825688,7.247706)},
        [('A','B'),('B','C'),('C','D'),('D','A'),('A','E'),('Q','D'),('F','G'),
         ((.985688,6.707706),(1.525688,6.867706)),
         ((1.525688,6.867706),(1.365688,7.407706))], scale_cm=.43) + r'''
\node at (5,-1.4) {图（1）};
\end{tikzpicture}
'''


def figure_fold(solution=False):
    construction = r'''
\begin{tikzpicture}[scale=.47,line cap=round,line join=round]
\coordinate (A) at (0,9); \coordinate (B) at (0,0);
\coordinate (C) at (6,0); \coordinate (D) at (6,9);
\coordinate (E) at (3,0); \coordinate (F) at (0,4);
\coordinate (G) at (6,6); \coordinate (P) at (7.8,3.6);
\coordinate (H) at (6,2.25); \coordinate (O) at (1.5,4.5);
\draw[thick] (A)--(B)--(C)--(D)--cycle;
\draw[thick] (A)--(E) (F)--(G) (F)--(E)--(P)--(G);
''' + tikz_labels(
        {'A':(0,9),'B':(0,0),'C':(6,0),'D':(6,9),'E':(3,0),
         'F':(0,4),'G':(6,6),'P':(7.8,3.6),'H':(6,2.25),'O':(1.5,4.5)},
        [('A','B'),('B','C'),('C','D'),('D','A'),('A','E'),('F','G'),
         ('F','E'),('E','P'),('P','G')] + ([('C','P'),((-1,0),(-1,9)),((0,-1.1),(6,-1.1))] if solution else []), scale_cm=.47)
    if solution:
        construction += r'''
\draw[very thick,dashed] (C)--(P);
\draw[thin,<->] (-1.0,0)--(-1.0,9) node[midway,left] {$9$};
\draw[thin,<->] (0,-1.1)--(6,-1.1) node[midway,below] {$6$};
\node[right,align=left] at (8.3,5.2) {$P(\frac{39}{5},\frac{18}{5})$};
\node[above,fill=none,inner sep=2pt] at (3,7.6) {$GF\perp AE$};
\node[below] at (3,-2.4) {折叠说明图：虚线为待求的 $CP$};
'''
    else:
        construction += r'\node at (3,-1.4) {图（2）};' + '\n'
    return construction + r'\end{tikzpicture}' + '\n'


PREAMBLE = r'''\documentclass[UTF8,fontset=fandol,12pt,a4paper]{ctexart}
\usepackage[margin=1.8cm,top=1.5cm,bottom=1.6cm]{geometry}
\input{worksheet-preamble}
\usetikzlibrary{calc}
\setlength{\parindent}{0pt}
\setlength{\parskip}{3pt}
\begin{document}
'''


def prepare(source=None):
    EXAMPLE.mkdir(parents=True, exist_ok=True)
    if source:
        target = EXAMPLE / 'source.png'
        if target.exists() and target.read_bytes() != Path(source).read_bytes():
            raise ValueError('Original source already exists; do not overwrite another source.')
        shutil.copy2(source, target)
    evidence = verify_geometry()
    (EXAMPLE / 'geometry_checks.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    ws = PREAMBLE + r'''
\wstitleblock{几何折叠：证明、探究与应用}{}{}
\noindent 姓名：\underline{\hspace{3cm}}\hfill 日期：\underline{\hspace{3cm}}
\begin{center}
''' + figure_square() + r'\hspace{2.0cm}' + figure_fold() + r'''
\end{center}
\problem{\textbf{证明推断。} 如图（1），在正方形 $ABCD$ 中，点 $E$、$Q$ 分别在边 $BC$、$AB$ 上，$DQ\perp AE$ 于点 $O$；点 $G$、$F$ 分别在边 $CD$、$AB$ 上，$GF\perp AE$。
\par \tikz[baseline=(n.base)]{\node[draw,circle,inner sep=1pt,font=\small] (n) {1};} 填空：$DQ$ \ansblank\ $AE$（填“$>$”“$<$”或“$=$”）；\tikz[baseline=(n.base)]{\node[draw,circle,inner sep=1pt,font=\small] (n) {2};} 推断 $\dfrac{GF}{AE}$ 的值为 \ansblank。}
\problem{\textbf{类比探究。} 如图（2），在矩形 $ABCD$ 中，$\dfrac{BC}{AB}=k$（$k$ 为常数）。将矩形 $ABCD$ 沿 $GF$ 折叠，使点 $A$ 落在 $BC$ 边上的点 $E$ 处，得到四边形 $FEPG$；$EP$ 交 $CD$ 于点 $H$，连接 $AE$ 交 $GF$ 于点 $O$。试探究 $GF$ 与 $AE$ 之间的数量关系，并说明理由。\noansline}
\problem{\textbf{拓展应用。} 在第（2）问的条件下，连接 $CP$。当 $k=\dfrac{2}{3}$ 时，若 $\dfrac{BE}{BF}=\dfrac{3}{4}$，$GF=2\sqrt{10}$，求 $CP$ 的长。}
\end{document}
'''
    ak = PREAMBLE + r'''
\wstitleblock{几何折叠：参考答案与说明}{}{}
\input{qa_photo_folding}
\problem{\textbf{第（1）问。} \quad $\boxed{DQ=AE}$；$\boxed{\dfrac{GF}{AE}=1}$。
\par 由 $DQ\perp AE$ 及 $AD\perp AB$，得 $\angle ADQ=\angle BAE$，故直角三角形 $ADQ$ 与 $BAE$ 相似。正方形中 $AD=AB$，所以 $DQ=AE$。
\par 取 $AB$ 上与 $G$ 同高的点 $T$，$TG=BC$。由 $\triangle TFG$ 与 $\triangle ABE$ 相似，得 $\dfrac{GF}{AE}=\dfrac{TG}{AB}=\dfrac{BC}{AB}=1$。}
\problem{\textbf{第（2）问。} \quad $\boxed{\dfrac{GF}{AE}=k}$，即 $GF=k\,AE$。
\par 折叠使 $A$ 与 $E$ 关于 $GF$ 对称，故 $GF$ 是 $AE$ 的垂直平分线。设 $T$ 为 $AB$ 上与 $G$ 同高的点，$TG=BC$。由 $GF\perp AE$、$AB\perp TG$，有 $\triangle TFG\sim\triangle ABE$，所以 $\dfrac{GF}{AE}=\dfrac{TG}{AB}=\dfrac{BC}{AB}=k$。}
\problem{\textbf{第（3）问。} \quad $\boxed{CP=\dfrac{9\sqrt5}{5}}$。
\par 设 $AB=h$、$BE=t$。折叠有 $AF=EF$，故 $BF=\dfrac{h^2-t^2}{2h}$。
由 $\dfrac{BE}{BF}=\dfrac34$ 得 $\dfrac{t}{h}=\dfrac13$（取符合图形的正根）。
\par 又 $BC=\dfrac23h$，$AE=\dfrac{\sqrt{10}}3h$，故 $GF=\dfrac{2\sqrt{10}}9h=2\sqrt{10}$，得到 $\boxed{AB=9,\ BC=6,\ BE=3,\ BF=4}$。
\par 取 $B(0,0)$、$C(6,0)$，则 $A(0,9)$、$D(6,9)$、$E(3,0)$，折痕 $GF$ 为 $y=\dfrac13x+4$。将 $D$ 关于折痕反射，得到 $\boxed{P(\dfrac{39}{5},\dfrac{18}{5})}$。
因此 $CP=\sqrt{(\dfrac{39}{5}-6)^2+(\dfrac{18}{5})^2}=\dfrac{9\sqrt5}{5}$。
\begin{center}
''' + figure_fold(True) + r'''
\end{center}}
\end{document}
'''
    (EXAMPLE/'ws_photo_folding.tex').write_text(ws, encoding='utf-8', newline='\n')
    (EXAMPLE/'ak_photo_folding.tex').write_text(ak, encoding='utf-8', newline='\n')
    verification = {'topic': '截图题复现：几何折叠', 'problem_count': 3, 'problems': [
        {'id': 1, 'type': 'compare', 'values': ['sqrt(1+x**2)', 'sqrt(1+x**2)'], 'order': 'relation', 'expected': '='},
        {'id': 1, 'type': 'equiv', 'expr': 'sqrt(1+x**2)/sqrt(1+x**2)', 'expected': '1', 'workspace_cm': 0},
        {'id': 1, 'type': 'manual', 'desc': 'Review triangle similarity and full segment DQ (not perpendicular distance DO).'},
        {'id': 2, 'type': 'equiv', 'expr': 'k*sqrt(1+x**2)/sqrt(1+x**2)', 'expected': 'k', 'workspace_cm': 0},
        {'id': 2, 'type': 'manual', 'desc': 'Review folding/perpendicular-bisector and auxiliary-triangle proof.'},
        {'id': 3, 'type': 'approx', 'expr': '2*sqrt(10)/(2/3*sqrt(1+(1/3)**2))', 'expected': 9, 'workspace_cm': 0},
        {'id': 3, 'type': 'approx', 'expr': '2/3*9', 'expected': 6},
        {'id': 3, 'type': 'approx', 'expr': '9/3', 'expected': 3},
        {'id': 3, 'type': 'approx', 'expr': '(9**2-3**2)/(2*9)', 'expected': 4},
        {'id': 3, 'type': 'approx', 'expr': '3+6*(9**2-3**2)/(9**2+3**2)', 'expected': '39/5'},
        {'id': 3, 'type': 'approx', 'expr': '2*9*6*3/(9**2+3**2)', 'expected': '18/5'},
        {'id': 3, 'type': 'distance', 'points': [[6,0],['39/5','18/5']], 'expected': '9*sqrt(5)/5'},
    ]}
    (EXAMPLE/'verify_photo_folding.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    tex = blank_comments(ws)
    manifest = {'mode': 'reproduce', 'problems': [
        {'id': i, 'source': f'User photograph, original question 1 part ({i}); handwritten answers excluded',
         'transcription_reviewed': True, 'uncertainties': [], 'block_sha256': digest(tex[a:b])}
        for i,(a,b) in enumerate(segment_spans(tex),1)], 'assets': []}
    (EXAMPLE/'sources_photo_folding.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(prepare(args.source), ensure_ascii=False, indent=2))
    if args.prepare_only:
        return 0
    bash = shutil.which('bash')
    if os.name == 'nt' and Path('C:/msys64/usr/bin/bash.exe').exists():
        bash = 'C:/msys64/usr/bin/bash.exe'
    if not bash:
        raise RuntimeError('Bash is required')
    env = os.environ.copy()
    env.update(PYTHONUTF8='1', MWS_PYTHON=sys.executable.replace('\\','/'),
               MSYS2_PATH_TYPE='inherit', MWS_LATEX_ENGINE='xelatex')
    result = subprocess.run([bash, '-l', str(ROOT/'scripts/build.sh'),
        str(EXAMPLE/'verify_photo_folding.json'), '--reproduce', '--outdir', str(EXAMPLE)], env=env)
    if result.returncode not in (0,2):
        return result.returncode
    # Keep public example artifacts small; staged templates and generated banks
    # are reproducible build intermediates, not documentation assets.
    for name in ['worksheet-preamble.tex','figure-macros.tex','qa_photo_folding.tex',
                 'ws_photo_folding.aux','ak_photo_folding.aux']:
        (EXAMPLE/name).unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
