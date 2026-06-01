"""数学 / 作文批改共用的模型调用与解析逻辑。

把 essay_grader 和 math_grader 里重复的部分集中在这里：
ZhipuAI 客户端、JSON 解析、等级换算、带重试的请求。
客户端采用懒加载——导入本模块不需要安装 zhipuai，方便对纯函数做单元测试。
"""
import json
import os
import time

from dotenv import load_dotenv

load_dotenv()

MODEL = "glm-4.6v"

# 等级阈值：从高到低，第一个满足的即为结果
GRADE_THRESHOLDS = [(90, "优秀"), (75, "良好"), (60, "合格")]

_client = None


def _get_client():
    """懒加载 ZhipuAI 客户端，首次批改时才创建。"""
    global _client
    if _client is None:
        from zhipuai import ZhipuAI
        _client = ZhipuAI(api_key=os.environ.get("ZHIPUAI_API_KEY"))
    return _client


def score_to_grade(score: int) -> str:
    """根据分数换算等级，数学和作文共用同一套阈值。"""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "待改进"


def parse_json_response(raw: str):
    """剥掉 ```json 代码块包裹并解析，失败返回 None。"""
    text = raw
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def get_grading_json(image_b64: str, prompt: str,
                     media_type: str = "image/jpeg", retries: int = 2) -> dict:
    """调用视觉模型并解析 JSON，对网络错误和无法解析的输出都会重试。

    成功返回解析后的 dict；全部尝试失败时返回 {"_raw": <最后的文本或错误信息>}，
    由调用方决定如何兜底，保证不会向上抛异常导致整批崩溃。
    """
    last_raw = ""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    for attempt in range(retries + 1):
        try:
            response = _get_client().chat.completions.create(
                model=MODEL, messages=messages)
            last_raw = response.choices[0].message.content
        except Exception as e:  # 网络/接口错误
            if attempt == retries:
                return {"_raw": f"模型调用失败：{e}"}
            time.sleep(2 ** attempt)
            continue

        parsed = parse_json_response(last_raw)
        if parsed is not None:
            return parsed
        if attempt < retries:  # 输出无法解析，再试一次
            time.sleep(1)

    return {"_raw": last_raw}
