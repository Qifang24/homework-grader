import json
import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI

load_dotenv()
client = ZhipuAI(api_key=os.environ.get("ZHIPUAI_API_KEY"))

MATH_PROMPT = """你是一位专业的数学老师，请批改这份学生的数学作业图片。

【核心要求】在判断每道题是否正确之前，你必须先亲自逐步计算出每一步的正确结果，然后与学生所写的数字逐一对比。哪怕是最简单的加减法，也必须独立验算，不能想当然。

例如：学生写"25 - 5 = 30"，你必须自己算出 25 - 5 = 20，发现学生答案 30 ≠ 20，因此判为错误。

请严格按照以下JSON格式输出，不要输出任何其他内容：
{
    "problems": [
        {
            "problem_num": "第X题",
            "correct": true或false,
            "partial_credit": true或false,
            "error_step": "第一个出错的步骤描述（没有错误则填null）",
            "error_reason": "错误原因（没有错误则填null）"
        }
    ],
    "comment": "针对该学生具体错误的个性化评语，2-3句，温暖鼓励但直接指出问题，禁止套话",
    "weak_points": ["薄弱知识点1", "薄弱知识点2"],
    "suggestions": "具体的下一步改进建议，一句话"
}

批改要求：
1. 对每道题的每一步：先独立计算正确结果，再与学生写的数字比对，不一致即为出错
2. 部分正确也要标记（partial_credit: true），但最终答案错误不能标记 correct: true
3. 评语必须引用学生具体的错误数字，不能是通用模板"""


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

    if score >= 90:
        grade = "优秀"
    elif score >= 75:
        grade = "良好"
    elif score >= 60:
        grade = "合格"
    else:
        grade = "待改进"

    return score, grade


def grade_math(image_b64: str, media_type: str = "image/jpeg") -> dict:
    response = client.chat.completions.create(
        model="glm-4.6v",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{image_b64}"},
                    },
                    {"type": "text", "text": MATH_PROMPT},
                ],
            }
        ],
    )

    raw = response.choices[0].message.content
    try:
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "score": None,
            "grade": "解析失败",
            "problems": [],
            "comment": raw,
            "weak_points": [],
            "suggestions": "",
        }

    score, grade = _calculate_score(result.get("problems", []))
    result["score"] = score
    result["grade"] = grade
    return result
