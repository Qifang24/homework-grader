from grader._client import get_grading_json, score_to_grade
from grader.knowledge_points import format_for_prompt, normalize

MATH_PROMPT_TEMPLATE = """你是一位专业的数学老师，请批改这份学生的数学作业图片。

【核心要求】在判断每道题是否正确之前，你必须先亲自逐步计算出每一步的正确结果，然后与学生所写的数字逐一对比。哪怕是最简单的加减法，也必须独立验算，不能想当然。

例如：学生写"25 - 5 = 30"，你必须自己算出 25 - 5 = 20，发现学生答案 30 ≠ 20，因此判为错误。

【知识点归类】每道题都必须从下面的课标知识点列表中，选出最匹配的一个，填到 knowledge_point 字段（必须与列表文字完全一致）：
{knowledge_points}

请严格按照以下JSON格式输出，不要输出任何其他内容：
{{
    "problems": [
        {{
            "problem_num": "第X题",
            "knowledge_point": "从上面列表中选一个最匹配的知识点",
            "correct": true或false,
            "partial_credit": true或false,
            "error_step": "第一个出错的步骤描述（没有错误则填null）",
            "error_reason": "错误原因（没有错误则填null）"
        }}
    ],
    "comment": "针对该学生具体错误的个性化评语，2-3句，温暖鼓励但直接指出问题，禁止套话",
    "suggestions": "具体的下一步改进建议，一句话"
}}

批改要求：
1. 对每道题的每一步：先独立计算正确结果，再与学生写的数字比对，不一致即为出错
2. 部分正确也要标记（partial_credit: true），但最终答案错误不能标记 correct: true
3. 评语必须引用学生具体的错误数字，不能是通用模板
4. knowledge_point 必须严格从给定列表中选择，不要自创"""

MATH_PROMPT = MATH_PROMPT_TEMPLATE.format(knowledge_points=format_for_prompt("数学"))


def _calculate_score(problems: list) -> tuple[int, str]:
    """根据逐题结果计算总分和等级，不依赖 AI 猜测。"""
    if not problems:
        return 0, "待改进"

    per_problem = 100 / len(problems)
    total = 0.0
    for p in problems:
        if p.get("correct"):
            total += per_problem
        elif p.get("partial_credit"):
            total += per_problem * 0.6

    score = round(total)
    return score, score_to_grade(score)


def _collect_weak_points(problems: list) -> list[str]:
    """把答错 / 部分对题目的知识点去重，作为该生薄弱知识点（保持出现顺序）。"""
    weak = []
    for p in problems:
        if not p.get("correct"):
            kp = normalize("数学", p.get("knowledge_point", ""))
            if kp not in weak:
                weak.append(kp)
    return weak


def grade_math(image_b64: str, media_type: str = "image/jpeg") -> dict:
    result = get_grading_json(image_b64, MATH_PROMPT, media_type)

    if "_raw" in result:
        return {
            "score": None,
            "grade": "解析失败",
            "problems": [],
            "comment": result["_raw"],
            "weak_points": [],
            "suggestions": "",
        }

    # 把每道题的知识点对齐到课标列表，避免模型自创导致无法聚合
    problems = result.get("problems", [])
    for p in problems:
        p["knowledge_point"] = normalize("数学", p.get("knowledge_point", ""))

    score, grade = _calculate_score(problems)
    result["score"] = score
    result["grade"] = grade
    result["weak_points"] = _collect_weak_points(problems)
    return result
