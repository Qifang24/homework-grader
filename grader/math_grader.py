"""数学批改：两阶段流程（先转录、再判分）。

把「认手写」和「判对错」拆成两次模型调用，是为了同时治住之前发现的两类错误：
- 阶段①只做 OCR，专心把学生写的步骤/答案忠实转录出来（高分辨率读图），
  不判对错、不替学生改对——解决「看错/漏读学生答案」。
- 阶段②拿到转录文本后再判分，明确以转录为准、不再重认笔迹，
  独立演算后逐题给分，并识别过程分——解决「自己算错」和「凭直觉判对错」。

对外签名与返回结构与单阶段版本完全一致，app / eval / 测试均无需改动。
"""
import json

from grader._client import get_grading_json, score_to_grade
from grader.knowledge_points import format_for_prompt, normalize

# ── 阶段①：转录（只做 OCR，绝不判分、不计算、不纠正）────────────────────
TRANSCRIBE_PROMPT = """你是一位严谨的 OCR 转录员。下面是一张学生数学作业图片。
你的唯一任务是【忠实转录】学生写的内容，绝对不要判断对错、不要纠正、不要替学生计算或补全。

按题型分别转录（student_answer 是必填的关键字段，只要学生写了任何作答就绝不能留空）：
- 选择题：把学生选的字母填进 student_answer（如 "B"），student_work 留空。
- 填空题：把横线上 / 括号里 / 空格中学生填的内容**完整**填进 student_answer；这类题通常没有过程，student_work 留空即可。一题有多个空，按顺序全部列进 student_answer（如 "30°；30°；60°；45°"）。
- 解答题 / 计算题：把完整解题过程逐步抄进 student_work，再把最终结果填进 student_answer。

通用要求：
1. 严格按试卷上**真实的题号**逐题转录（第1题、第2题…或 1、2…）。忽略"自主导学""易错点睛""核心知识点"这类印刷的栏目/版块标题，不要把栏目当成题目。
2. 分数必须连分子分母一起完整转录（如 (x+3)/(x-3)，不能只抄成 x+3）；正负号、根号、指数、±、以及多个并列答案都要逐一保留，一个都不能漏。
3. 看不清的字符用 "?" 占位，绝不猜成别的字符。只有该题学生确实空白未作答时，student_answer 才留空。
4. 学生写错的内容也要照原样抄下来，不要替他改对，也不要补全他没写的步骤。

请严格按以下 JSON 输出，不要输出任何其他内容：
{
    "student_name": "卷面手写的学生姓名，认不出就填空字符串",
    "class_name": "卷面手写的班级，认不出就填空字符串",
    "problems": [
        {
            "problem_num": "第X题",
            "student_work": "解答题的解题步骤，逐步忠实转录；选择/填空题留空",
            "student_answer": "学生的最终作答（选择题填字母 / 填空题填所填内容 / 解答题填最终结果），必填"
        }
    ]
}"""

# ── 阶段②：判分（以转录为准，独立演算，识别过程分）────────────────────
JUDGE_PROMPT_TEMPLATE = """你是一位专业的数学老师，正在批改一份数学作业。

学生的作答已由 OCR 逐字转录如下，这是【权威版本】，请直接采用，不要再去辨认图片上的学生笔迹：

{transcription}

图片只供你查看【题目原文与图形】。请按下面步骤逐题批改：

1. 完全独立地、不参考学生答案，把这道题自己算一遍：关键步骤写进 my_calculation，你算出的正确答案写进 my_computed_answer。哪怕最简单的运算也要独立验算。
2. 再对照转录中的 student_answer / student_work 判分（若 student_answer 为空但 student_work 有内容，就以 student_work 里学生写出的最终结果为准；只有两者都为空才算未作答）：
   - 最终答案与 my_computed_answer 在数值/语义上一致 → correct=true。
   - 最终答案错，但解题过程中有正确步骤（思路/方法对，只是某一步算错）→ correct=false 且 partial_credit=true（给过程分）。
   - 完全错误或方法方向就不对 → correct=false 且 partial_credit=false。
   - correct 必须由上面的比较得出，不允许凭直觉直接下结论。
3. 若判错，指出 student_work 中【第一处】出错的步骤(error_step)与原因(error_reason)；没有错误则填 null。
4. 给每道题归一个知识点(knowledge_point)，必须与下面列表中的文字完全一致：
{knowledge_points}

请严格按以下 JSON 输出，不要输出任何其他内容；problems 的题号与数量必须与上面转录完全一致：
{{
    "problems": [
        {{
            "problem_num": "第X题",
            "knowledge_point": "从上面列表中选一个最匹配的",
            "my_calculation": "你自己独立演算的关键步骤，简短",
            "my_computed_answer": "你独立算出的正确答案",
            "correct": true或false,
            "partial_credit": true或false,
            "error_step": "第一处出错的步骤（没有错误填null）",
            "error_reason": "错误原因（没有错误填null）"
        }}
    ],
    "comment": "针对该学生具体错误的个性化评语，2-3句，必须引用转录里学生写的具体数字/步骤，温暖鼓励但直接指出问题，禁止套话",
    "suggestions": "具体的下一步改进建议，一句话"
}}"""


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


def _failed(raw: str) -> dict:
    """任一阶段解析失败时的统一兜底，结构与正常返回一致，避免整批崩溃。"""
    return {
        "score": None,
        "grade": "解析失败",
        "problems": [],
        "comment": raw,
        "weak_points": [],
        "suggestions": "",
        "student_name": "",
        "class_name": "",
    }


def _transcribe(image_b64: str, media_type: str) -> dict:
    """阶段①：只做忠实 OCR 转录。"""
    return get_grading_json(image_b64, TRANSCRIBE_PROMPT, media_type)


def _judge(image_b64: str, media_type: str, transcription: dict) -> dict:
    """阶段②：以转录为准，独立演算后逐题判分。"""
    trans_text = json.dumps(
        {"problems": transcription.get("problems", [])},
        ensure_ascii=False, indent=2)
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        transcription=trans_text, knowledge_points=format_for_prompt("数学"))
    return get_grading_json(image_b64, prompt, media_type)


def _merge(transcription: dict, judged: dict) -> list[dict]:
    """按题号顺序对齐：判分结果为主，贴回转录的 student_answer / student_work。"""
    t_probs = transcription.get("problems", [])
    j_probs = judged.get("problems", [])
    merged = []
    for i, jp in enumerate(j_probs):
        tp = t_probs[i] if i < len(t_probs) else {}
        jp["student_answer"] = tp.get("student_answer", "")
        jp["student_work"] = tp.get("student_work", "")
        jp["knowledge_point"] = normalize("数学", jp.get("knowledge_point", ""))
        merged.append(jp)
    return merged


def grade_math(image_b64: str, media_type: str = "image/jpeg") -> dict:
    """两阶段批改：先转录（OCR），再判分（含过程分）。返回结构同单阶段版本。"""
    transcription = _transcribe(image_b64, media_type)
    if "_raw" in transcription:
        return _failed(transcription["_raw"])

    judged = _judge(image_b64, media_type, transcription)
    if "_raw" in judged:
        return _failed(judged["_raw"])

    # 学生身份来自转录阶段（认手写本就是 OCR 的职责）
    result = {
        "student_name": (transcription.get("student_name") or "").strip(),
        "class_name": (transcription.get("class_name") or "").strip(),
    }

    problems = _merge(transcription, judged)
    score, grade = _calculate_score(problems)
    result["problems"] = problems
    result["score"] = score
    result["grade"] = grade
    result["weak_points"] = _collect_weak_points(problems)
    result["comment"] = judged.get("comment", "")
    result["suggestions"] = judged.get("suggestions", "")
    return result
