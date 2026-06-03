"""知识点体系：列表获取、prompt 格式化、模型返回值对齐。"""
from grader.knowledge_points import (
    get_knowledge_points, format_for_prompt, normalize, OTHER,
)


def test_get_knowledge_points():
    assert "整数四则运算" in get_knowledge_points("数学")
    assert "审题立意" in get_knowledge_points("语文作文")
    assert get_knowledge_points("未知学科") == []


def test_format_for_prompt_numbered():
    text = format_for_prompt("数学")
    assert text.startswith("1. 整数四则运算")
    assert "19. 锐角三角函数" in text


def test_normalize_exact_match():
    assert normalize("数学", "分数运算") == "分数运算"


def test_normalize_fuzzy_match():
    # 模型多写了字，包含式匹配应对齐到标准项
    assert normalize("数学", "分数运算错误") == "分数运算"
    assert normalize("数学", "应用题") == "应用题（数量关系理解）"


def test_normalize_unknown_to_other():
    assert normalize("数学", "量子力学") == OTHER
    assert normalize("数学", "") == OTHER
    assert normalize("数学", None) == OTHER
