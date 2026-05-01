import base64
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

from grader.essay_grader import grade_essay
from grader.math_grader import grade_math

load_dotenv()

st.set_page_config(page_title="AI作业批改系统", page_icon="📝", layout="wide")

st.markdown("""
<style>
/* ── 全局背景 ─────────────────────────────── */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #f0f4ff 0%, #fafaff 60%, #f5f0ff 100%);
    min-height: 100vh;
}
[data-testid="stHeader"] { background: transparent; }

/* ── 侧边栏 ───────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1f3c 0%, #2d3561 100%);
    border-right: none;
}
[data-testid="stSidebar"] * { color: #e8eaf6 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #ffffff !important; }
[data-testid="stSidebar"] .stSelectbox label { color: #b0b8e8 !important; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: #ffffff !important;
    border-radius: 10px;
}

/* ── 标题区 ───────────────────────────────── */
.hero {
    background: linear-gradient(135deg, #2d3561 0%, #4a5eb8 50%, #6c7dd4 100%);
    border-radius: 20px;
    padding: 2.2rem 2.5rem;
    margin-bottom: 1.8rem;
    box-shadow: 0 8px 32px rgba(45,53,97,0.18);
}
.hero h1 {
    color: #ffffff;
    font-size: 2rem;
    font-weight: 800;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.5px;
}
.hero p {
    color: rgba(255,255,255,0.75);
    font-size: 0.95rem;
    margin: 0;
}

/* ── 上传卡片 ─────────────────────────────── */
.card {
    background: #ffffff;
    border-radius: 16px;
    padding: 1.5rem;
    box-shadow: 0 2px 16px rgba(45,53,97,0.08);
    margin-bottom: 1rem;
}
.card-title {
    font-size: 1rem;
    font-weight: 700;
    color: #2d3561;
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* ── 上传组件 ─────────────────────────────── */
[data-testid="stFileUploader"] {
    background: #f7f8ff;
    border: 2px dashed #c5caee;
    border-radius: 14px;
    padding: 0.5rem;
    transition: border-color 0.2s;
}
[data-testid="stFileUploader"]:hover { border-color: #4a5eb8; }

/* ── 批改按钮 ─────────────────────────────── */
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #4a5eb8 0%, #6c7dd4 100%);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 1rem;
    font-weight: 700;
    padding: 0.7rem 1.5rem;
    box-shadow: 0 4px 16px rgba(74,94,184,0.35);
    transition: all 0.2s;
    letter-spacing: 0.3px;
}
[data-testid="stButton"] > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(74,94,184,0.4);
    background: linear-gradient(135deg, #3a4ea8 0%, #5c6dc4 100%);
}

/* ── 结果卡片 ─────────────────────────────── */
.result-header {
    background: linear-gradient(135deg, #1a1f3c 0%, #2d3561 100%);
    border-radius: 16px 16px 0 0;
    padding: 1.4rem 1.8rem;
}
.result-header h2 { color: #fff; margin: 0; font-size: 1.1rem; font-weight: 700; }

.score-block {
    background: #ffffff;
    border-radius: 0 0 16px 16px;
    padding: 1.5rem 1.8rem;
    box-shadow: 0 4px 24px rgba(45,53,97,0.1);
    margin-bottom: 1rem;
}
.score-number {
    font-size: 3.5rem;
    font-weight: 900;
    background: linear-gradient(135deg, #2d3561, #4a5eb8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1;
    margin-bottom: 0.3rem;
}
.grade-badge {
    display: inline-block;
    padding: 0.3rem 1rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 700;
    margin-top: 0.4rem;
}
.grade-excellent { background: #e8f5e9; color: #2e7d32; }
.grade-good      { background: #e3f2fd; color: #1565c0; }
.grade-pass      { background: #fff8e1; color: #e65100; }
.grade-fail      { background: #fce4ec; color: #c62828; }

/* ── 逐题 expander ────────────────────────── */
[data-testid="stExpander"] {
    background: #ffffff;
    border: 1px solid #e8eaf6;
    border-radius: 12px !important;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 6px rgba(45,53,97,0.06);
    overflow: hidden;
}
[data-testid="stExpander"] summary {
    font-weight: 600;
    color: #2d3561;
    padding: 0.8rem 1rem;
}
[data-testid="stExpander"] summary:hover { background: #f7f8ff; }

/* ── 评语 / 薄弱点 / 建议 ─────────────────── */
.comment-box {
    background: linear-gradient(135deg, #f7f8ff, #eef0ff);
    border-left: 4px solid #4a5eb8;
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem;
    color: #2d3561;
    font-size: 0.95rem;
    line-height: 1.7;
    margin: 0.5rem 0 1rem;
}
.weak-tag {
    display: inline-block;
    background: #fff0f0;
    color: #c62828;
    border: 1px solid #ffcdd2;
    border-radius: 20px;
    padding: 0.25rem 0.8rem;
    font-size: 0.82rem;
    font-weight: 600;
    margin: 0.25rem 0.25rem 0.25rem 0;
}
.suggest-box {
    background: linear-gradient(135deg, #f0fff4, #e8f5e9);
    border-left: 4px solid #43a047;
    border-radius: 0 12px 12px 0;
    padding: 0.9rem 1.2rem;
    color: #1b5e20;
    font-size: 0.92rem;
    font-weight: 500;
}

/* ── 分割线 ───────────────────────────────── */
hr { border-color: #e8eaf6; margin: 1.2rem 0; }

/* ── 图片容器 ─────────────────────────────── */
[data-testid="stImage"] img {
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}

/* ── metric ───────────────────────────────── */
[data-testid="stMetric"] {
    background: #f7f8ff;
    border-radius: 12px;
    padding: 0.8rem 1rem;
}
</style>
""", unsafe_allow_html=True)

# ── 侧边栏 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📚 批改设置")
    subject = st.selectbox(
        "选择学科",
        ["数学", "语文作文", "英语作文"],
        help="选择作业对应的学科",
    )
    st.divider()
    st.markdown("""
**使用说明**
1. 选择学科
2. 上传作业图片
3. 点击开始批改
""")
    st.divider()
    st.caption("Powered by ZhipuAI GLM-4V")

# ── Hero 标题 ────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>📝 AI 作业批改系统</h1>
  <p>支持数学、语文作文、英语作文的智能批改 · 逐步骤诊断 · 个性化评语</p>
</div>
""", unsafe_allow_html=True)

# ── 上传区域 ─────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "上传作业图片（支持 JPG / PNG）",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed",
)

if uploaded_file:
    col_img, col_result = st.columns([1, 1], gap="large")

    with col_img:
        st.markdown('<div class="card-title">🖼️ 作业原图</div>', unsafe_allow_html=True)
        st.image(uploaded_file, use_container_width=True)

    with col_result:
        if st.button("🚀 开始批改", type="primary", use_container_width=True):
            raw_bytes = uploaded_file.read()
            media_type = "image/png" if uploaded_file.type == "image/png" else "image/jpeg"
            image_b64 = base64.standard_b64encode(raw_bytes).decode("utf-8")

            with st.spinner("AI 正在批改中，请稍候…"):
                if subject == "数学":
                    result = grade_math(image_b64, media_type)
                else:
                    result = grade_essay(image_b64, subject, media_type)

            score = result.get("score")
            grade = result.get("grade", "")

            grade_class = {
                "优秀": "grade-excellent",
                "良好": "grade-good",
                "合格": "grade-pass",
                "待改进": "grade-fail",
            }.get(grade, "grade-pass")

            grade_emoji = {
                "优秀": "🏆",
                "良好": "🌟",
                "合格": "✅",
                "待改进": "📖",
            }.get(grade, "")

            # 得分卡片
            st.markdown('<div class="result-header"><h2>批改结果</h2></div>', unsafe_allow_html=True)
            st.markdown(f"""
<div class="score-block">
  <div style="color:#6b7280;font-size:0.85rem;margin-bottom:0.2rem">综合得分</div>
  <div class="score-number">{score if score is not None else "--"} <span style="font-size:1.5rem;-webkit-text-fill-color:#6b7280">分</span></div>
  <span class="grade-badge {grade_class}">{grade_emoji} {grade}</span>
</div>
""", unsafe_allow_html=True)

            # 数学：逐题分析
            if subject == "数学" and result.get("problems"):
                st.markdown("**逐题分析**")
                for p in result["problems"]:
                    if p.get("correct"):
                        icon = "✅"
                    elif p.get("partial_credit"):
                        icon = "🔶"
                    else:
                        icon = "❌"
                    with st.expander(f"{icon} {p.get('problem_num', '')}"):
                        if p.get("error_step"):
                            st.markdown(f"**出错步骤：** `{p['error_step']}`")
                        if p.get("error_reason"):
                            st.markdown(f"**原因：** {p['error_reason']}")
                        if p.get("correct"):
                            st.success("完全正确！", icon="🎉")

            # 作文：四维评分
            if subject != "数学" and result.get("dimensions"):
                st.markdown("**四维评分**")
                dims = result["dimensions"]
                dim_labels = {
                    "theme":     ("主题", "🎯"),
                    "structure": ("结构", "🏗️"),
                    "language":  ("语言", "✍️"),
                    "content":   ("内容", "💡"),
                }
                for key, (label, emoji) in dim_labels.items():
                    if key in dims:
                        d = dims[key]
                        s = d.get("score", 0)
                        with st.expander(f"{emoji} {label}  —  {s}/25 分"):
                            st.progress(s / 25)
                            st.write(d.get("comment", ""))
                if result.get("highlight"):
                    st.info(f"✨ **亮点句：** {result['highlight']}")

            st.divider()

            # 个性化评语
            st.markdown("**个性化评语**")
            st.markdown(f'<div class="comment-box">{result.get("comment", "")}</div>', unsafe_allow_html=True)

            # 薄弱知识点
            weak_points = result.get("weak_points", [])
            if weak_points:
                st.markdown("**薄弱知识点**")
                tags_html = "".join(f'<span class="weak-tag">⚠️ {wp}</span>' for wp in weak_points)
                st.markdown(tags_html, unsafe_allow_html=True)

            # 改进建议
            if result.get("suggestions"):
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(
                    f'<div class="suggest-box">💡 <strong>改进建议：</strong>{result["suggestions"]}</div>',
                    unsafe_allow_html=True,
                )
