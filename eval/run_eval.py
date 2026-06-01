#!/usr/bin/env python3
"""离线准确率评测：用人工标注的样本集跑批改器，输出一致率 / MAE。

用法：
    1. 把样本图片放进 eval/gold/images/
    2. 在 eval/gold/labels.json 标注每张图的人工答案
       （格式见 eval/gold/labels.example.json）
    3. 运行：  python -m eval.run_eval
    4. 结果写入 eval/report.json 和 eval/report.md，
       app 侧边栏会自动读取 report.json 展示准确率看板。
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from grader.image_utils import encode_image_bytes
from grader.math_grader import grade_math
from grader.essay_grader import grade_essay
from eval.metrics import summarize, problem_agreement

EVAL_DIR = Path(__file__).parent
GOLD_DIR = EVAL_DIR / "gold"
LABELS = GOLD_DIR / "labels.json"


def _grade(subject: str, b64: str, mt: str) -> dict:
    if subject == "数学":
        return grade_math(b64, mt)
    return grade_essay(b64, subject, mt)


def _build_records(labels: list) -> list[dict]:
    records = []
    for item in labels:
        img_path = GOLD_DIR / item["file"]
        if not img_path.exists():
            print(f"  ⚠️  跳过：找不到图片 {img_path}")
            continue

        b64, mt = encode_image_bytes(img_path.read_bytes())
        pred = _grade(item["subject"], b64, mt)

        rec = {
            "file": item["file"],
            "subject": item["subject"],
            "pred_score": pred.get("score"),
            "gold_score": item.get("score"),
            "pred_grade": pred.get("grade"),
            "gold_grade": item.get("grade"),
        }
        if item["subject"] == "数学":
            rec["pred_problems"] = pred.get("problems", [])
            rec["gold_problems"] = item.get("problems")
        records.append(rec)
        print(f"  ✓ {item['file']}: 预测 {pred.get('score')}/{pred.get('grade')}"
              f"  ·  人工 {item.get('score')}/{item.get('grade')}")
    return records


def _to_markdown(report: dict, records: list[dict]) -> str:
    lines = [
        "# 准确率评测报告",
        "",
        f"生成时间：{report['生成时间']}",
        "",
        "## 总体指标",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| 样本数 | {report['样本数']} |",
        f"| 分数 MAE（越小越好） | {report['分数MAE']} |",
        f"| 等级一致率 | {_pct(report['等级一致率'])} |",
        f"| 逐题判对一致率（数学） | {_pct(report['逐题判对一致率'])} |",
        "",
        "## 逐样本明细",
        "",
        "| 文件 | 学科 | 预测分 | 人工分 | 预测等级 | 人工等级 | 逐题一致 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in records:
        if r["subject"] == "数学" and r.get("gold_problems") is not None:
            hit, total = problem_agreement(r.get("pred_problems", []), r["gold_problems"])
            pa = f"{hit}/{total}"
        else:
            pa = "—"
        lines.append(
            f"| {r['file']} | {r['subject']} | {r['pred_score']} | {r['gold_score']} "
            f"| {r['pred_grade']} | {r['gold_grade']} | {pa} |"
        )
    return "\n".join(lines) + "\n"


def _pct(x):
    return "—" if x is None else f"{round(x * 100, 1)}%"


def run():
    if not LABELS.exists():
        print(f"找不到标注文件：{LABELS}")
        print("请参考 eval/gold/labels.example.json 创建 eval/gold/labels.json。")
        sys.exit(1)

    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    print(f"开始评测，共 {len(labels)} 个样本…\n")

    records = _build_records(labels)
    if not records:
        print("没有可评测的样本。")
        sys.exit(1)

    report = summarize(records)
    report["生成时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    (EVAL_DIR / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVAL_DIR / "report.md").write_text(
        _to_markdown(report, records), encoding="utf-8")

    print("\n" + "=" * 40)
    print(f"样本数：{report['样本数']}")
    print(f"分数 MAE：{report['分数MAE']}")
    print(f"等级一致率：{_pct(report['等级一致率'])}")
    print(f"逐题判对一致率（数学）：{_pct(report['逐题判对一致率'])}")
    print("=" * 40)
    print("已写入 eval/report.json 与 eval/report.md")


if __name__ == "__main__":
    run()
