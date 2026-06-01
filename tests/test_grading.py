"""纯函数单元测试：分数换算、JSON 解析、数学/作文分数计算。

这些测试不触发任何模型调用（_client 的客户端是懒加载的），可离线运行：
    pytest
"""
from grader._client import score_to_grade, parse_json_response
from grader.math_grader import _calculate_score as math_score, _collect_weak_points
from grader.essay_grader import _calculate_score as essay_score


# ── 等级换算 ────────────────────────────────────────────
def test_score_to_grade_boundaries():
    assert score_to_grade(100) == "优秀"
    assert score_to_grade(90) == "优秀"
    assert score_to_grade(89) == "良好"
    assert score_to_grade(75) == "良好"
    assert score_to_grade(74) == "合格"
    assert score_to_grade(60) == "合格"
    assert score_to_grade(59) == "待改进"
    assert score_to_grade(0) == "待改进"


# ── JSON 解析 ───────────────────────────────────────────
def test_parse_plain_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_json_fenced():
    raw = 'some text\n```json\n{"a": 1}\n```\ntail'
    assert parse_json_response(raw) == {"a": 1}


def test_parse_json_bare_fence():
    raw = '```\n{"a": 2}\n```'
    assert parse_json_response(raw) == {"a": 2}


def test_parse_invalid_returns_none():
    assert parse_json_response("not json at all") is None
    assert parse_json_response("```json\n{broken}\n```") is None


# ── 数学分数计算 ────────────────────────────────────────
def test_math_all_correct():
    problems = [{"correct": True}, {"correct": True}]
    assert math_score(problems) == (100, "优秀")


def test_math_partial_credit():
    # 一题对(50) + 一题部分对(50*0.6=30) = 80
    problems = [{"correct": True}, {"partial_credit": True}]
    score, grade = math_score(problems)
    assert score == 80
    assert grade == "良好"


def test_math_all_wrong():
    problems = [{"correct": False}, {"correct": False}]
    assert math_score(problems) == (0, "待改进")


def test_math_empty():
    assert math_score([]) == (0, "待改进")


def test_collect_weak_points_dedup_and_normalize():
    problems = [
        {"correct": True, "knowledge_point": "分数运算"},        # 对的不计入
        {"correct": False, "knowledge_point": "分数运算"},       # 错
        {"correct": False, "knowledge_point": "分数运算错误"},   # 模糊→分数运算，去重
        {"partial_credit": True, "knowledge_point": "应用题"},   # 部分对也算薄弱
    ]
    weak = _collect_weak_points(problems)
    assert weak == ["分数运算", "应用题（数量关系理解）"]


# ── 作文分数计算 ────────────────────────────────────────
def test_essay_full_marks():
    dims = {k: {"score": 25} for k in ["theme", "structure", "language", "content"]}
    assert essay_score(dims) == (100, "优秀")


def test_essay_partial():
    dims = {
        "theme": {"score": 20}, "structure": {"score": 18},
        "language": {"score": 15}, "content": {"score": 12},
    }  # 总 65
    assert essay_score(dims) == (65, "合格")


def test_essay_missing_dimensions_default_zero():
    assert essay_score({}) == (0, "待改进")


def test_essay_caps_at_100():
    dims = {k: {"score": 30} for k in ["theme", "structure", "language", "content"]}
    score, grade = essay_score(dims)  # 120 → 截断到 100
    assert score == 100
    assert grade == "优秀"
