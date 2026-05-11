import json
import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI

load_dotenv()
client = ZhipuAI(api_key=os.environ.get("ZHIPUAI_API_KEY"))

ESSAY_PROMPT_TEMPLATE = """你是一位专业的{subject}老师，请批改这份学生的{subject}作文图片。

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
    "weak_points": ["需要改进的方面1", "需要改进的方面2"],
    "suggestions": "最重要的一条修改建议，具体可操作"
}}

批改要求：
1. 仔细识别手写内容，包括涂改和潦草字迹
2. 四个维度各25分，每个维度独立打分
3. 评语必须引用作文中的具体句子，体现个性化"""


def _calculate_score(dimensions: dict) -> tuple[int, str]:
    """总分 = 四维之和，等级由代码统一判断。"""
    keys = ["theme", "structure", "language", "content"]
    total = sum(dimensions.get(k, {}).get("score", 0) for k in keys)
    score = min(100, max(0, total))

    if score >= 90:
        grade = "优秀"
    elif score >= 75:
        grade = "良好"
    elif score >= 60:
        grade = "合格"
    else:
        grade = "待改进"

    return score, grade


def grade_essay(image_b64: str, subject: str = "语文", media_type: str = "image/jpeg") -> dict:
    prompt = ESSAY_PROMPT_TEMPLATE.format(subject=subject)

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
                    {"type": "text", "text": prompt},
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
            "dimensions": {},
            "highlight": "",
            "comment": raw,
            "weak_points": [],
            "suggestions": "",
        }

    score, grade = _calculate_score(result.get("dimensions", {}))
    result["score"] = score
    result["grade"] = grade
    return result
