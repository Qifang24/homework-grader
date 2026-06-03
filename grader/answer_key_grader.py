"""标准答案对照批改：同时输入「教师页（标准答案/批改）」和「学生页」，
逐题对比学生答案与标准答案。适用于选择题、填空题等客观题——
准确率来自「与标准答案比对」，而非「模型自行解题」，比让模型凭空判对错可靠得多。

这是对现有 math_grader / essay_grader 的增量补充，二者互不影响。
"""
from grader._client import get_grading_json_multi, score_to_grade

KEY_PROMPT = """你将看到两张图片：
- 第一张是【教师页】：标准答案或老师的批改，其中红色笔迹/批注通常就是正确答案。
- 第二张是【学生页】：学生本人的作答。

请按下面步骤批改这份{subject}作业：
1. 先逐题从【第一张·教师页】提取每道题的标准答案。
2. 再逐题从【第二张·学生页】提取学生填写的答案。
3. 按题号对齐，逐题比对：学生答案与标准答案一致记 correct=true，否则 false。
   - 选择题：选项字母一致才算对。
   - 填空/解答题：语义或数值一致即可算对，无需逐字相同。

请严格按以下 JSON 输出，不要输出任何其他内容：
{{
    "student_name": "学生页上手写的姓名，辨认不出就填空字符串",
    "class_name": "学生页上手写的班级，辨认不出就填空字符串",
    "problems": [
        {{
            "problem_num": "第X题",
            "question_type": "选择题/填空题/解答题",
            "student_answer": "学生写的答案",
            "correct_answer": "教师页上的标准答案",
            "correct": true或false
        }}
    ],
    "comment": "针对学生主要错题的个性化评语，2-3句，引用具体题号和答案，禁止套话",
    "suggestions": "一句话改进建议"
}}

要求：
1. 题号必须与图片实际一致，不要遗漏或编造题目。
2. 标准答案只能来自教师页；教师页上认不出的题，correct_answer 留空且该题 correct=false，禁止自己编造答案。
3. 学生未作答的题，student_answer 留空并记 correct=false。"""


def _score(problems: list) -> tuple[int, str]:
    """得分 = 答对题数 / 总题数 × 100，等级沿用全局阈值。"""
    if not problems:
        return 0, "待改进"
    correct = sum(1 for p in problems if p.get("correct"))
    score = round(100 * correct / len(problems))
    return score, score_to_grade(score)


def grade_with_key(student_b64: str, teacher_b64: str, subject: str = "数学",
                   student_mt: str = "image/jpeg",
                   teacher_mt: str = "image/jpeg") -> dict:
    """对照教师页批改学生页。教师页作为图 1、学生页作为图 2 传给模型。"""
    prompt = KEY_PROMPT.format(subject=subject)
    result = get_grading_json_multi(
        [(teacher_b64, teacher_mt), (student_b64, student_mt)], prompt)

    if "_raw" in result:
        return {
            "score": None,
            "grade": "解析失败",
            "problems": [],
            "comment": result["_raw"],
            "weak_points": [],
            "suggestions": "",
        }

    result["student_name"] = (result.get("student_name") or "").strip()
    result["class_name"] = (result.get("class_name") or "").strip()

    problems = result.get("problems", [])
    score, grade = _score(problems)
    result["score"] = score
    result["grade"] = grade
    result["weak_points"] = []  # 客观题对照暂不归类知识点
    result["grading_mode"] = "answer_key"  # 界面据此渲染"逐题对照"视图
    return result
