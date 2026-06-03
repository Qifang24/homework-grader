"""课标知识点体系（学情诊断的地基）。

把"薄弱点"从大模型自由发挥的文本，约束成一套固定的、可聚合的课标知识点：
- 模型批改时必须把每个错误归类到下面列表中的某一项；
- 班级学情就能按课标知识点统计排行，而不是杂乱字符串。

每科一份列表，按学段可继续扩展。先覆盖最有把握的小学数学，
语文/英语作文按常见写作维度归类。
"""

KNOWLEDGE_POINTS = {
    "数学": [
        # 小学
        "整数四则运算",
        "小数运算",
        "分数运算",
        "四则混合运算与运算顺序",
        "应用题（数量关系理解）",
        "几何图形认识",
        "周长与面积",
        "单位换算",
        "统计与图表",
        # 初中
        "有理数运算",
        "整式运算与乘法公式",
        "因式分解",
        "分式运算",
        "二次根式与实数",
        "方程与不等式",
        "函数（一次/二次/反比例）",
        "三角形与全等",
        "四边形与圆",
        "锐角三角函数",
        "解直角三角形及其应用",
        "概率与统计",
    ],
    "语文作文": [
        "审题立意",
        "篇章结构",
        "语言表达与修辞",
        "内容充实与细节",
        "详略安排",
        "过渡与衔接",
        "标点使用",
        "错别字与书写规范",
    ],
    "英语作文": [
        "主题契合",
        "篇章结构与连贯",
        "语法与时态",
        "词汇拼写",
        "句式多样性",
        "标点与大小写",
        "书写规范",
    ],
}

# 模型偶尔会归错类时的兜底标签，保证统计不丢数据
OTHER = "其他"


def get_knowledge_points(subject: str) -> list[str]:
    """返回某学科的知识点列表（未知学科返回空列表）。"""
    return KNOWLEDGE_POINTS.get(subject, [])


def format_for_prompt(subject: str) -> str:
    """把知识点列表格式化成可放进 prompt 的带序号文本。"""
    kps = get_knowledge_points(subject)
    return "\n".join(f"{i}. {kp}" for i, kp in enumerate(kps, 1))


def normalize(subject: str, label: str) -> str:
    """把模型返回的知识点对齐到固定列表；对不上就归到「其他」。

    先精确匹配，再做包含式模糊匹配，尽量不丢数据。
    """
    if not label:
        return OTHER
    kps = get_knowledge_points(subject)
    label = label.strip()
    if label in kps:
        return label
    for kp in kps:
        if kp in label or label in kp:
            return kp
    return OTHER
