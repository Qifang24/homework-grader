import base64
import os
from pathlib import Path
from collections import Counter

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
.hero h1 { color:#fff; font-size:2rem; font-weight:800; margin:0 0 .3rem 0; }
.hero p  { color:rgba(255,255,255,.75); font-size:.95rem; margin:0; }

/* ── 按钮 ─────────────────────────────────── */
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #4a5eb8 0%, #6c7dd4 100%);
    color: white; border: none; border-radius: 12px;
    font-size: 1rem; font-weight: 700; padding: .7rem 1.5rem;
    box-shadow: 0 4px 16px rgba(74,94,184,.35);
    transition: all .2s;
}
[data-testid="stButton"] > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(74,94,184,.4);
}

/* ── 上传组件 ─────────────────────────────── */
[data-testid="stFileUploader"] {
    background: #f7f8ff;
    border: 2px dashed #c5caee;
    border-radius: 14px; padding: .5rem;
}
[data-testid="stFileUploader"]:hover { border-color: #4a5eb8; }

/* ── 结果卡片 ─────────────────────────────── */
.result-header {
    background: linear-gradient(135deg, #1a1f3c 0%, #2d3561 100%);
    border-radius: 16px 16px 0 0; padding: 1.4rem 1.8rem;
}
.result-header h2 { color:#fff; margin:0; font-size:1.1rem; font-weight:700; }
.score-block {
    background:#fff; border-radius:0 0 16px 16px;
    padding:1.5rem 1.8rem;
    box-shadow:0 4px 24px rgba(45,53,97,.1); margin-bottom:1rem;
}
.score-number {
    font-size:3.5rem; font-weight:900;
    background:linear-gradient(135deg,#2d3561,#4a5eb8);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    line-height:1; margin-bottom:.3rem;
}
.grade-badge {
    display:inline-block; padding:.3rem 1rem;
    border-radius:20px; font-size:.85rem; font-weight:700; margin-top:.4rem;
}
.grade-excellent { background:#e8f5e9; color:#2e7d32; }
.grade-good      { background:#e3f2fd; color:#1565c0; }
.grade-pass      { background:#fff8e1; color:#e65100; }
.grade-fail      { background:#fce4ec; color:#c62828; }

/* ── Expander ─────────────────────────────── */
[data-testid="stExpander"] {
    background:#fff; border:1px solid #e8eaf6;
    border-radius:12px !important; margin-bottom:.5rem;
    box-shadow:0 1px 6px rgba(45,53,97,.06);
}
[data-testid="stExpander"] summary { font-weight:600; color:#2d3561; padding:.8rem 1rem; }
[data-testid="stExpander"] summary:hover { background:#f7f8ff; }

/* ── 评语 / 建议 ──────────────────────────── */
.comment-box {
    background:linear-gradient(135deg,#f7f8ff,#eef0ff);
    border-left:4px solid #4a5eb8;
    border-radius:0 12px 12px 0; padding:1rem 1.2rem;
    color:#2d3561; font-size:.95rem; line-height:1.7; margin:.5rem 0 1rem;
}
.weak-tag {
    display:inline-block; background:#fff0f0; color:#c62828;
    border:1px solid #ffcdd2; border-radius:20px;
    padding:.25rem .8rem; font-size:.82rem; font-weight:600;
    margin:.25rem .25rem .25rem 0;
}
.suggest-box {
    background:linear-gradient(135deg,#f0fff4,#e8f5e9);
    border-left:4px solid #43a047; border-radius:0 12px 12px 0;
    padding:.9rem 1.2rem; color:#1b5e20; font-size:.92rem; font-weight:500;
}

/* ── 班级报告卡片 ─────────────────────────── */
.report-section {
    background:#fff; border-radius:16px;
    padding:1.4rem 1.8rem; margin-bottom:1rem;
    box-shadow:0 2px 16px rgba(45,53,97,.08);
}
.report-title {
    font-size:1rem; font-weight:700; color:#2d3561;
    border-left:4px solid #4a5eb8; padding-left:.7rem;
    margin-bottom:1rem;
}
.stat-card {
    background:linear-gradient(135deg,#f0f4ff,#e8ecff);
    border-radius:12px; padding:1rem 1.2rem; text-align:center;
}
.stat-number { font-size:2rem; font-weight:900; color:#2d3561; }
.stat-label  { font-size:.8rem; color:#6b7280; margin-top:.2rem; }
.weak-rank-item {
    display:flex; align-items:center; gap:.8rem;
    padding:.6rem .8rem; border-radius:8px; margin-bottom:.4rem;
    background:#f7f8ff;
}
.weak-rank-bar {
    height:8px; border-radius:4px;
    background:linear-gradient(90deg,#4a5eb8,#6c7dd4);
    transition:width .3s;
}
.rank-num {
    font-size:.85rem; font-weight:700; color:#fff;
    background:#4a5eb8; border-radius:50%;
    width:22px; height:22px; display:inline-flex;
    align-items:center; justify-content:center; flex-shrink:0;
}

/* ── 图片 ─────────────────────────────────── */
[data-testid="stImage"] img { border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,.1); }
hr { border-color:#e8eaf6; margin:1.2rem 0; }
</style>
""", unsafe_allow_html=True)

# ── 侧边栏 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📚 批改设置")
    subject = st.selectbox("选择学科", ["数学", "语文作文", "英语作文"])
    st.divider()
    st.markdown("**使用说明**\n1. 选择学科\n2. 选择批改模式\n3. 上传作业图片\n4. 点击开始批改")
    st.divider()
    st.caption("Powered by ZhipuAI GLM-4V")

# ── Hero ─────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>📝 AI 作业批改系统</h1>
  <p>支持数学、语文作文、英语作文的智能批改 · 逐步骤诊断 · 个性化评语 · 班级学情分析</p>
</div>
""", unsafe_allow_html=True)

# ── 标签页 ───────────────────────────────────────────────
tab_single, tab_class = st.tabs(["📄 单份批改", "👥 班级学情分析"])


# ═══════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════
def encode_image(file):
    raw = file.read()
    media_type = "image/png" if file.type == "image/png" else "image/jpeg"
    return base64.standard_b64encode(raw).decode(), media_type


def show_grade_badge(grade):
    cls = {"优秀":"grade-excellent","良好":"grade-good","合格":"grade-pass","待改进":"grade-fail"}.get(grade,"grade-pass")
    emoji = {"优秀":"🏆","良好":"🌟","合格":"✅","待改进":"📖"}.get(grade,"")
    return cls, emoji


def render_result(result, subject):
    score = result.get("score")
    grade = result.get("grade", "")
    cls, emoji = show_grade_badge(grade)

    st.markdown('<div class="result-header"><h2>批改结果</h2></div>', unsafe_allow_html=True)
    st.markdown(f"""
<div class="score-block">
  <div style="color:#6b7280;font-size:.85rem;margin-bottom:.2rem">综合得分</div>
  <div class="score-number">{score if score is not None else "--"} <span style="font-size:1.5rem;-webkit-text-fill-color:#6b7280">分</span></div>
  <span class="grade-badge {cls}">{emoji} {grade}</span>
</div>""", unsafe_allow_html=True)

    if subject == "数学" and result.get("problems"):
        st.markdown("**逐题分析**")
        for p in result["problems"]:
            icon = "✅" if p.get("correct") else ("🔶" if p.get("partial_credit") else "❌")
            with st.expander(f"{icon} {p.get('problem_num','')}"):
                if p.get("error_step"):
                    st.markdown(f"**出错步骤：** `{p['error_step']}`")
                if p.get("error_reason"):
                    st.markdown(f"**原因：** {p['error_reason']}")
                if p.get("correct"):
                    st.success("完全正确！", icon="🎉")

    if subject != "数学" and result.get("dimensions"):
        st.markdown("**四维评分**")
        dims = result["dimensions"]
        dim_labels = {"theme":("主题","🎯"),"structure":("结构","🏗️"),"language":("语言","✍️"),"content":("内容","💡")}
        for key,(label,emoji2) in dim_labels.items():
            if key in dims:
                d = dims[key]
                s = d.get("score",0)
                with st.expander(f"{emoji2} {label}  —  {s}/25 分"):
                    st.progress(s/25)
                    st.write(d.get("comment",""))
        if result.get("highlight"):
            st.info(f"✨ **亮点句：** {result['highlight']}")

    st.divider()
    st.markdown("**个性化评语**")
    st.markdown(f'<div class="comment-box">{result.get("comment","")}</div>', unsafe_allow_html=True)

    weak_points = result.get("weak_points",[])
    if weak_points:
        st.markdown("**薄弱知识点**")
        tags = "".join(f'<span class="weak-tag">⚠️ {wp}</span>' for wp in weak_points)
        st.markdown(tags, unsafe_allow_html=True)

    if result.get("suggestions"):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div class="suggest-box">💡 <strong>改进建议：</strong>{result["suggestions"]}</div>', unsafe_allow_html=True)


def generate_class_report(results, subject):
    scores = [r.get("score") for r in results if r.get("score") is not None]
    if not scores:
        return None

    avg   = round(sum(scores)/len(scores), 1)
    high  = max(scores)
    low   = min(scores)
    pass_ = sum(1 for s in scores if s >= 60)
    pass_rate = round(pass_/len(scores)*100, 1)

    grade_cnt = Counter(r.get("grade","") for r in results)

    weak_all = []
    for r in results:
        weak_all.extend(r.get("weak_points",[]))
    weak_rank = Counter(weak_all).most_common(6)

    error_rank = []
    if subject == "数学":
        errors = []
        for r in results:
            for p in r.get("problems",[]):
                if p.get("error_step"):
                    errors.append(p["error_step"])
        error_rank = Counter(errors).most_common(5)

    dim_avgs = {}
    if subject != "数学":
        dim_keys = ["theme","structure","language","content"]
        dim_labels = {"theme":"主题","structure":"结构","language":"语言","content":"内容"}
        for k in dim_keys:
            vals = [r["dimensions"][k]["score"] for r in results if r.get("dimensions",{}).get(k,{}).get("score") is not None]
            if vals:
                dim_avgs[dim_labels[k]] = round(sum(vals)/len(vals),1)

    return dict(avg=avg, high=high, low=low, pass_rate=pass_rate,
                grade_cnt=grade_cnt, weak_rank=weak_rank,
                error_rank=error_rank, dim_avgs=dim_avgs, total=len(results))


def render_class_report(report, subject):
    n = report["total"]

    st.markdown("---")
    st.markdown("## 📊 班级学情报告")

    # 概况指标
    st.markdown('<div class="report-title">班级概况</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{report["avg"]}</div><div class="stat-label">班级平均分</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{report["pass_rate"]}%</div><div class="stat-label">及格率（≥60分）</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{report["high"]}</div><div class="stat-label">最高分</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{report["low"]}</div><div class="stat-label">最低分</div></div>', unsafe_allow_html=True)

    # 成绩分布
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="report-title">成绩分布</div>', unsafe_allow_html=True)
    g = report["grade_cnt"]
    gc1,gc2,gc3,gc4 = st.columns(4)
    with gc1: st.metric("🏆 优秀", f'{g.get("优秀",0)} 人', f'{round(g.get("优秀",0)/n*100)}%')
    with gc2: st.metric("🌟 良好", f'{g.get("良好",0)} 人', f'{round(g.get("良好",0)/n*100)}%')
    with gc3: st.metric("✅ 合格", f'{g.get("合格",0)} 人', f'{round(g.get("合格",0)/n*100)}%')
    with gc4: st.metric("📖 待改进", f'{g.get("待改进",0)} 人', f'{round(g.get("待改进",0)/n*100)}%')

    # 作文四维平均分
    if report["dim_avgs"]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="report-title">四维平均得分（满分25）</div>', unsafe_allow_html=True)
        cols = st.columns(len(report["dim_avgs"]))
        for i,(label,avg) in enumerate(report["dim_avgs"].items()):
            with cols[i]:
                st.metric(label, f"{avg} 分")
                st.progress(avg/25)

    # 薄弱知识点排行
    if report["weak_rank"]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="report-title">⚠️ 全班薄弱知识点排行</div>', unsafe_allow_html=True)
        max_cnt = report["weak_rank"][0][1]
        for i,(wp,cnt) in enumerate(report["weak_rank"],1):
            pct = round(cnt/n*100)
            bar_w = round(cnt/max_cnt*100)
            st.markdown(f"""
<div class="weak-rank-item">
  <span class="rank-num">{i}</span>
  <div style="flex:1">
    <div style="display:flex;justify-content:space-between;margin-bottom:4px">
      <span style="font-weight:600;color:#2d3561">{wp}</span>
      <span style="color:#6b7280;font-size:.85rem">{cnt} 人 · {pct}%</span>
    </div>
    <div style="background:#e8eaf6;border-radius:4px;height:8px">
      <div class="weak-rank-bar" style="width:{bar_w}%"></div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # 数学高频错误步骤
    if report["error_rank"]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="report-title">❌ 高频错误步骤（数学）</div>', unsafe_allow_html=True)
        for step,cnt in report["error_rank"]:
            st.markdown(f"- `{step}` —— **{cnt} 人次**出现此错误")

    # 给老师的教学建议
    if report["weak_rank"]:
        st.markdown("<br>", unsafe_allow_html=True)
        top3 = "、".join(wp for wp,_ in report["weak_rank"][:3])
        st.markdown(f'<div class="suggest-box">💡 <strong>教学建议：</strong>本次作业全班集中薄弱点为「{top3}」，建议在下次课重点复习相关内容，并针对得分低于60分的学生进行个别辅导。</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# Tab 1：单份批改
# ═══════════════════════════════════════════════════════
with tab_single:
    uploaded_file = st.file_uploader(
        "上传作业图片（支持 JPG / PNG）",
        type=["jpg","jpeg","png"], key="single",
        label_visibility="collapsed",
    )
    if uploaded_file:
        col_img, col_result = st.columns([1,1], gap="large")
        with col_img:
            st.markdown('<div style="font-weight:700;color:#2d3561;margin-bottom:.5rem">🖼️ 作业原图</div>', unsafe_allow_html=True)
            st.image(uploaded_file, use_container_width=True)
        with col_result:
            if st.button("🚀 开始批改", type="primary", use_container_width=True, key="btn_single"):
                b64, mt = encode_image(uploaded_file)
                with st.spinner("AI 正在批改中，请稍候…"):
                    result = grade_math(b64,mt) if subject=="数学" else grade_essay(b64,subject,mt)
                render_result(result, subject)


# ═══════════════════════════════════════════════════════
# Tab 2：班级学情分析
# ═══════════════════════════════════════════════════════
with tab_class:
    st.markdown("上传全班同学的作业图片，系统将逐一批改并生成班级学情报告。")

    uploaded_files = st.file_uploader(
        "上传多份作业图片（支持批量选择）",
        type=["jpg","jpeg","png"],
        accept_multiple_files=True, key="batch",
        label_visibility="collapsed",
    )

    if uploaded_files:
        st.info(f"已选择 **{len(uploaded_files)}** 份作业，点击下方按钮开始批量批改。")

        if st.button("🚀 开始批量批改", type="primary", use_container_width=True, key="btn_batch"):
            results = []
            names   = []
            progress_bar = st.progress(0, text="正在批改中…")

            for i, f in enumerate(uploaded_files):
                progress_bar.progress((i+1)/len(uploaded_files), text=f"正在批改第 {i+1}/{len(uploaded_files)} 份…")
                b64, mt = encode_image(f)
                r = grade_math(b64,mt) if subject=="数学" else grade_essay(b64,subject,mt)
                results.append(r)
                names.append(f.name)

            progress_bar.empty()
            st.success(f"批改完成！共处理 {len(results)} 份作业。")

            # 班级学情报告
            report = generate_class_report(results, subject)
            if report:
                render_class_report(report, subject)

            # 逐份详情（折叠）
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("## 📋 逐份批改详情")
            for i,(name,result) in enumerate(zip(names,results)):
                score = result.get("score","—")
                grade = result.get("grade","")
                _,emoji = show_grade_badge(grade)
                with st.expander(f"{emoji} {name}  ·  {score}分  ·  {grade}"):
                    render_result(result, subject)
