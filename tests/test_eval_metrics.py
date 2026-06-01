"""准确率评测指标的纯函数测试。"""
from eval.metrics import (
    score_mae, agreement_rate, problem_agreement,
    aggregate_problem_agreement, summarize,
)


def test_score_mae():
    # (|90-88| + |60-65|) / 2 = (2 + 5) / 2 = 3.5
    assert score_mae([(90, 88), (60, 65)]) == 3.5
    assert score_mae([]) is None
    # None 值应被忽略
    assert score_mae([(90, None), (80, 80)]) == 0.0


def test_agreement_rate():
    assert agreement_rate([("优秀", "优秀"), ("良好", "合格")]) == 0.5
    assert agreement_rate([]) is None
    assert agreement_rate([("优秀", "优秀"), ("优秀", "优秀")]) == 1.0


def test_problem_agreement_aligned():
    pred = [{"correct": True}, {"correct": False}, {"correct": True}]
    gold = [{"correct": True}, {"correct": True}, {"correct": True}]
    assert problem_agreement(pred, gold) == (2, 3)


def test_problem_agreement_length_mismatch():
    # 只比较较短部分
    pred = [{"correct": True}]
    gold = [{"correct": True}, {"correct": False}]
    assert problem_agreement(pred, gold) == (1, 1)


def test_aggregate_problem_agreement():
    samples = [
        ([{"correct": True}, {"correct": False}], [{"correct": True}, {"correct": False}]),
        ([{"correct": True}], [{"correct": False}]),
    ]
    # 2/2 + 0/1 = 2/3
    assert aggregate_problem_agreement(samples) == round(2 / 3, 4)
    assert aggregate_problem_agreement([]) is None


def test_summarize_mixed_subjects():
    records = [
        {"subject": "数学", "pred_score": 50, "gold_score": 50,
         "pred_grade": "待改进", "gold_grade": "待改进",
         "pred_problems": [{"correct": True}, {"correct": False}],
         "gold_problems": [{"correct": True}, {"correct": False}]},
        {"subject": "语文作文", "pred_score": 80, "gold_score": 85,
         "pred_grade": "良好", "gold_grade": "良好"},
    ]
    out = summarize(records)
    assert out["样本数"] == 2
    assert out["分数MAE"] == 2.5
    assert out["等级一致率"] == 1.0
    assert out["逐题判对一致率"] == 1.0
    assert out["数学样本数"] == 1
