from grader._client import get_grading_json, score_to_grade
from grader.knowledge_points import format_for_prompt, normalize

ESSAY_PROMPT_TEMPLATE = """你是一位专业的{subject}老师，请批改这份学生的{subject}作文图片。

【薄弱点归类】weak_points 必须从下面的课标写作知识点列表中选择 1-3 个（必须与列表文字完全一致），不要自创：
{knowledge_points}

请严格按照以下JSON格式输出，不要输出任何其他内容：
{{
    "dimensions": {{
        "theme": {{
            "score": 数字(0-25),
            "comment": "主题相关性评价"
        }},
        "structure": {{
            "score": 数字(0-25),
            "comment": "段落结构评价"
        }},
        "language": {{
            "score": 数字(0-25),
            "comment": "语言表达评价，列举1-2个具体好句或问题句"
        }},
        "content": {{
            "score": 数字(0-25),
            "comment": "内容丰富度评价"
        }}
    }},
    "highlight": "作文中最好的一句话或一个亮点，直接引用原文",
    "comment": "针对该学生这篇作文的个性化总评，2-3句，引用具体内容，禁止套话",
    "weak_points": ["从上面列表中选择的薄弱知识点1", "薄弱知识点2"],
    "suggestions": "最重要的一条修改建议，具体可操作"
}}

批改要求：
1. 仔细识别手写内容，包括涂改和潦草字迹
2. 四个维度各25分，每个维度独立打分
3. 评语必须引用作文中的具体句子，体现个性化
4. weak_points 必须严格从给定列表中选择，不要自创"""


def _calculate_score(dimensions: dict) -> tuple[int, str]:
    """总分 = 四维之和，等级由代码统一判断。"""
    keys = ["theme", "structure", "language", "content"]
    total = sum(dimensions.get(k, {}).get("score", 0) for k in keys)
    score = min(100, max(0, total))
    return score, score_to_grade(score)


def grade_essay(image_b64: str, subject: str = "语文", media_type: str = "image/jpeg") -> dict:
    prompt = ESSAY_PROMPT_TEMPLATE.format(
        subject=subject, knowledge_points=format_for_prompt(subject))
    result = get_grading_json(image_b64, prompt, media_type)

    if "_raw" in result:
        return {
            "score": None,
            "grade": "解析失败",
            "dimensions": {},
            "highlight": "",
            "comment": result["_raw"],
            "weak_points": [],
            "suggestions": "",
        }

    # 把薄弱点对齐到课标列表，去重后保留顺序
    aligned, seen = [], set()
    for wp in result.get("weak_points", []):
        kp = normalize(subject, wp)
        if kp not in seen:
            seen.add(kp)
            aligned.append(kp)
    result["weak_points"] = aligned

    score, grade = _calculate_score(result.get("dimensions", {}))
    result["score"] = score
    result["grade"] = grade
    return result
