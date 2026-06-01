"""准确率评测的纯函数指标层。

刻意不依赖任何模型调用或文件 IO，方便单元测试，也方便在答辩里
直接讲清楚每个指标怎么算出来的：
- 分数 MAE：预测分与人工分的平均绝对误差（越小越好）
- 等级一致率：预测等级与人工等级一致的比例
- 逐题判对一致率（数学）：按题号对齐后，correct 判断一致的比例
"""


def score_mae(pairs: list[tuple[float, float]]) -> float | None:
    """pairs 为 (预测分, 人工分) 列表，返回平均绝对误差。空列表返回 None。"""
    valid = [(p, g) for p, g in pairs if p is not None and g is not None]
    if not valid:
        return None
    return round(sum(abs(p - g) for p, g in valid) / len(valid), 2)


def agreement_rate(pairs: list[tuple]) -> float | None:
    """pairs 为 (预测值, 人工值) 列表，返回完全一致的比例（0-1）。"""
    valid = [(p, g) for p, g in pairs if p is not None and g is not None]
    if not valid:
        return None
    hit = sum(1 for p, g in valid if p == g)
    return round(hit / len(valid), 4)


def problem_agreement(pred_problems: list, gold_problems: list) -> tuple[int, int]:
    """逐题对比 correct 判断（按题号顺序对齐）。

    返回 (一致题数, 可比较题数)。题数不一致时只比较较短的部分，
    多出来的题不计入分母（题目识别数量差异另行统计）。
    """
    n = min(len(pred_problems), len(gold_problems))
    hit = sum(
        1 for i in range(n)
        if bool(pred_problems[i].get("correct")) == bool(gold_problems[i].get("correct"))
    )
    return hit, n


def aggregate_problem_agreement(samples: list[tuple[list, list]]) -> float | None:
    """对多份数学样本汇总逐题判对一致率。

    samples 为 [(预测problems, 人工problems), ...]。返回总体一致率（0-1）。
    """
    total_hit = total_n = 0
    for pred, gold in samples:
        hit, n = problem_agreement(pred, gold)
        total_hit += hit
        total_n += n
    if total_n == 0:
        return None
    return round(total_hit / total_n, 4)


def summarize(records: list[dict]) -> dict:
    """把逐样本评测结果汇总成报告。

    每条 record 需含：
        subject, pred_score, gold_score, pred_grade, gold_grade
        数学还可含：pred_problems, gold_problems
    """
    n = len(records)
    score_pairs = [(r.get("pred_score"), r.get("gold_score")) for r in records]
    grade_pairs = [(r.get("pred_grade"), r.get("gold_grade")) for r in records]

    math_samples = [
        (r.get("pred_problems", []), r.get("gold_problems", []))
        for r in records
        if r.get("subject") == "数学" and r.get("gold_problems") is not None
    ]

    return {
        "样本数": n,
        "分数MAE": score_mae(score_pairs),
        "等级一致率": agreement_rate(grade_pairs),
        "逐题判对一致率": aggregate_problem_agreement(math_samples) if math_samples else None,
        "数学样本数": len(math_samples),
    }
