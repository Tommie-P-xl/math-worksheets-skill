"""Build a standalone demo from synthetic questions, never from a personal bank."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import question_bank as qb
from bank_browser import export_browser


def questions():
    item = qb.example()
    item.update(title="平行线中的相似三角形", summary="识别相似关系，再求线段长度。",
                stem=r"如图，在 $\triangle ABC$ 中，$D$、$E$ 分别在 $AB$、$AC$ 上，$DE\parallel BC$。已知 $AD=3$，$DB=2$，$BC=10$，求 $DE$。",
                answer=r"$DE=6$。",
                solution=r"因 $DE\parallel BC$，对应角相等，故 $\triangle ADE\sim\triangle ABC$。$AB=3+2=5$，所以 $\frac{DE}{BC}=\frac{AD}{AB}=\frac{3}{5}$，得 $DE=6$。",
                family="parallel-triangle-ratio",
                diagram={"format": "svg", "givens": ["D∈AB，E∈AC，DE∥BC", "AD=3，DB=2，BC=10"],
                         "code": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 195" width="300" height="225"><g fill="none" stroke="#386457" stroke-width="1.5"><path d="M130 20 L30 160 L230 160 Z M70 104 L190 104"/></g><g font-family="serif" font-size="14" fill="#182b30"><text x="126" y="14">A</text><text x="14" y="167">B</text><text x="235" y="167">C</text><text x="53" y="103">D</text><text x="197" y="103">E</text><text x="82" y="60">3</text><text x="37" y="132">2</text><text x="123" y="183">10</text></g></svg>'})
    item["tags"].update(grades=["九年级"], topics=["相似三角形"], types=["几何计算"], methods=["AA相似", "比例关系"])
    item["demand"].update(knowledge_span="平行线对应角、三角形相似及对应边成比例", reasoning_steps=3,
                          scaffolding="已给出平行关系", difficulty={"estimate": 2, "basis": "estimated", "reason": "相似关系较明确，需要先求整边；未作答校准。"})
    item["verification"] = {"status": "reviewed", "notes": "演示题，已独立核对比例和计算；不属于个人题库。"}
    item["stem"] += r"\begin{enumerate}[label=（\arabic*）]\item 说明相似关系，并分别写出：\begin{enumerate}[label=\textcircled{\arabic*}]\item 相似的判定条件；\item 对应边的比例。\end{enumerate}\item 求 $DE$。\end{enumerate}"
    item["solution"] = r"\textbf{（1）}因 $DE\parallel BC$，对应角相等，故 $\triangle ADE\sim\triangle ABC$，判定条件为 AA，对应边成比例。\par\textbf{（2）}$AB=3+2=5$，由 $\frac{DE}{10}=\frac{3}{5}$ 得\ans{DE=6}"
    q1 = deepcopy(item)

    item = qb.example()
    item.update(title="含分母的一元一次方程", summary="去分母后移项求解。",
                stem=r"解方程：\frac{x-1}{2}+\frac{x+1}{3}=4。", answer=r"$x=5$。",
                solution=r"两边同乘 $6$，得 $3(x-1)+2(x+1)=24$，整理为 $5x-1=24$，所以 $x=5$。代回原式，左边等于 $4$。",
                family="linear-equation-denominators")
    item["demand"].update(knowledge_span="去分母、一元一次方程", reasoning_steps=3, calculation_load="中", difficulty={"estimate": 2, "basis": "estimated", "reason": "需去分母及合并同类项；未作答校准。"})
    item["verification"] = {"status": "reviewed", "notes": "演示题，已代入核对。"}
    q2 = deepcopy(item)

    item = qb.example()
    item.update(title="直角三角形的边长", summary="由两条直角边求斜边。",
                stem=r"如图，在 $\mathrm{Rt}\triangle ABC$ 中，$\angle A=90^\circ$，$AB=6$，$AC=8$，求 $BC$。",
                answer=r"$BC=10$。", solution=r"由勾股定理，$BC^2=AB^2+AC^2=6^2+8^2=100$。边长为正，故 $BC=10$。",
                family="right-triangle-hypotenuse",
                diagram={"format": "tikz", "givens": ["∠A=90°，AB=6，AC=8"],
                         "code": r"\begin{tikzpicture}[scale=.5,line width=.7pt]\coordinate(A)at(0,0);\coordinate(B)at(0,6);\coordinate(C)at(8,0);\draw(A)--(B)--(C)--cycle;\draw(.4,0)--(.4,.4)--(0,.4);\node[below left]at(A){$A$};\node[above]at(B){$B$};\node[right]at(C){$C$};\node[left]at(0,3){$6$};\node[below]at(4,0){$8$};\end{tikzpicture}"})
    item["tags"].update(grades=["八年级"], topics=["勾股定理"], types=["几何计算"], methods=["勾股定理"])
    item["demand"].update(knowledge_span="勾股定理、算术平方根", reasoning_steps=2, scaffolding="直角与两直角边已给出",
                          difficulty={"estimate": 1, "basis": "estimated", "reason": "公式直接应用；未作答校准。"})
    item["verification"] = {"status": "reviewed", "notes": "演示题，已核对 36+64=100。"}
    item["solution"] = r"\textbf{求解} " + item["solution"] + r"\ans{BC=10}" + "\n" + item["diagram"]["code"].replace(r"\end{tikzpicture}", r"\node[above right] at (4,3){$10$};\end{tikzpicture}")
    item["alternative_solutions"] = [{"title": "坐标法", "solution":
        r"以 $A$ 为原点，$AC$、$AB$ 所在直线分别为横轴、纵轴，则 $B(0,6)$、$C(8,0)$。"
        "\n\n" + r"由两点间距离公式，\[BC=\sqrt{(8-0)^2+(0-6)^2}=\sqrt{64+36}=\sqrt{100}=10.\]"
        "\n\n" + item["diagram"]["code"].replace(r"\end{tikzpicture}", r"\node[below] at (4,-.7){$B(0,6),\ C(8,0)$};\end{tikzpicture}")
        + "\n\n" + r"因此 $\boxed{BC=10}$，与解法一相同。"}]
    q3 = deepcopy(item)

    item = qb.example()
    item.update(title="二次函数的最小值", summary="从顶点式读取最值与对应自变量。",
                stem=r"已知函数 $y=(x-2)^2-1$，求函数的最小值及此时 $x$ 的值。",
                answer=r"最小值为 $-1$，此时 $x=2$。",
                solution=r"因为 $(x-2)^2\geq 0$，所以 $y\geq -1$；当且仅当 $x=2$ 时取等号。",
                family="quadratic-vertex-minimum")
    item["tags"].update(grades=["九年级"], topics=["二次函数"], types=["函数最值"], methods=["配方法", "非负性"])
    item["demand"].update(knowledge_span="二次函数顶点式、平方的非负性", reasoning_steps=2,
                          difficulty={"estimate": 1, "basis": "estimated", "reason": "由顶点式直接判断最小值；未作答校准。"})
    item["verification"] = {"status": "reviewed", "notes": "演示题，已用平方的非负性独立核对。"}
    return [q1, q2, q3, item]


def main():
    destination = ROOT / "docs/examples/bank-browser"
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mws-demo-") as tmp:
        work = Path(tmp)
        bank = qb.Bank(work / "synthetic-bank")
        for item in questions():
            proposal = work / "proposal.json"
            proposal.write_text(qb.encoded(item), encoding="utf-8")
            preview = bank.preview(proposal)
            bank.commit(proposal, preview["receipt"], "Synthetic documentation fixture; not personal archival consent")
        result = export_browser(bank, work / "browser.html", demo=True)
        output = destination / "browser.html"
        output.write_bytes(Path(result["html"]).read_bytes())
        print(json.dumps({"html": str(output), "bytes": result["bytes"], "questions": result["questions"]}))


if __name__ == "__main__":
    main()
