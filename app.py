import streamlit as st
from pptx import Presentation
import anthropic
import json
import pandas as pd
import os
from datetime import datetime

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI 기획 리뷰 툴",
    page_icon="🤖",
    layout="wide",
)

RESULT_JSON_PATH = "latest_review_result.json"
RESULT_HTML_PATH = "latest_review_result.html"

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600&family=IBM+Plex+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans KR', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        border-left: 4px solid #6366f1;
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 600; }
    .main-header p  { margin: 0.4rem 0 0; color: #94a3b8; font-size: 0.9rem; }

    .section-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #1e293b;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
        margin-top: 1.5rem;
    }

    .slide-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        font-size: 0.85rem;
        line-height: 1.7;
    }

    .stat-box {
        background: #f1f5f9;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .stat-box .num { font-size: 2rem; font-weight: 700; color: #6366f1; }
    .stat-box .lbl { font-size: 0.8rem; color: #64748b; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def load_saved_result():
    if os.path.exists(RESULT_JSON_PATH):
        try:
            with open(RESULT_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_result_json(data):
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def dataframe_to_html_table(df: pd.DataFrame, title: str) -> str:
    if df.empty:
        return f"<h2>{title}</h2><p>결과 없음</p>"

    return f"""
    <h2>{title}</h2>
    {df.to_html(index=False, escape=False, border=0)}
    """

def build_html_report(result_data):
    generated_at = result_data.get("generated_at", "")
    source_file_name = result_data.get("source_file_name", "")

    ux_df = pd.DataFrame(result_data.get("ux_issues", []))
    if not ux_df.empty:
        ux_df = ux_df.rename(columns={
            "title": "Title",
            "description": "Description",
            "impact": "Impact",
        })

    policy_df = pd.DataFrame(result_data.get("policy_gaps", []))
    if not policy_df.empty:
        policy_df = policy_df.rename(columns={
            "title": "Title",
            "description": "Description",
            "recommendation": "Recommendation",
        })

    edge_df = pd.DataFrame(result_data.get("edge_cases", []))
    if not edge_df.empty:
        edge_df = edge_df.rename(columns={
            "title": "Title",
            "scenario": "Scenario",
            "expected_behavior": "Expected Behavior",
        })

    tc_df = pd.DataFrame(result_data.get("test_cases", []))
    if not tc_df.empty:
        tc_df = tc_df.rename(columns={
            "id": "TC #",
            "test_case": "Test Case",
            "description": "Description",
            "expected_result": "Expected Result",
            "priority": "Priority",
        })

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>AI Planning Review Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 32px;
                color: #1e293b;
                line-height: 1.6;
            }}
            h1 {{
                margin-bottom: 8px;
            }}
            .meta {{
                color: #64748b;
                margin-bottom: 24px;
            }}
            h2 {{
                margin-top: 32px;
                padding-bottom: 8px;
                border-bottom: 2px solid #e2e8f0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 12px;
                margin-bottom: 24px;
                table-layout: fixed;
                word-wrap: break-word;
            }}
            th, td {{
                border: 1px solid #cbd5e1;
                padding: 10px;
                text-align: left;
                vertical-align: top;
                font-size: 14px;
            }}
            th {{
                background: #f1f5f9;
            }}
        </style>
    </head>
    <body>
        <h1>AI 기획 리뷰 결과</h1>
        <div class="meta">
            <div><strong>생성 시각:</strong> {generated_at}</div>
            <div><strong>원본 파일:</strong> {source_file_name}</div>
        </div>

        {dataframe_to_html_table(ux_df, "1. UX Issues")}
        {dataframe_to_html_table(policy_df, "2. Policy Gaps")}
        {dataframe_to_html_table(edge_df, "3. Edge Cases")}
        {dataframe_to_html_table(tc_df, "4. QA Test Cases")}
    </body>
    </html>
    """
    return html

def save_html_report(html: str):
    with open(RESULT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

def render_saved_results():
    if "review_result" not in st.session_state:
        return

    result_data = st.session_state["review_result"]

    ux_issues = result_data.get("ux_issues", [])
    policy_gaps = result_data.get("policy_gaps", [])
    edge_cases = result_data.get("edge_cases", [])
    test_cases = result_data.get("test_cases", [])
    html_report = result_data.get("html_report", "")

    st.markdown("### 📌 저장된 AI 리뷰 결과")

    generated_at = result_data.get("generated_at", "-")
    source_file_name = result_data.get("source_file_name", "-")
    st.caption(f"생성 시각: {generated_at} | 원본 파일: {source_file_name}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="stat-box"><div class="num">{len(ux_issues)}</div><div class="lbl">UX Issues</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="stat-box"><div class="num">{len(policy_gaps)}</div><div class="lbl">Policy Gaps</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="stat-box"><div class="num">{len(edge_cases)}</div><div class="lbl">Edge Cases</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="stat-box"><div class="num">{len(test_cases)}</div><div class="lbl">QA Test Cases</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">1. UX Issues</div>', unsafe_allow_html=True)
    if ux_issues:
        ux_df = pd.DataFrame([
            {
                "Title": item.get("title", ""),
                "Description": item.get("description", ""),
                "Impact": item.get("impact", ""),
            }
            for item in ux_issues
        ])
        st.dataframe(ux_df, use_container_width=True, hide_index=True)
    else:
        st.info("UX Issues 결과가 없습니다.")

    st.markdown('<div class="section-title">2. Policy Gaps</div>', unsafe_allow_html=True)
    if policy_gaps:
        policy_df = pd.DataFrame([
            {
                "Title": item.get("title", ""),
                "Description": item.get("description", ""),
                "Recommendation": item.get("recommendation", ""),
            }
            for item in policy_gaps
        ])
        st.dataframe(policy_df, use_container_width=True, hide_index=True)
    else:
        st.info("Policy Gaps 결과가 없습니다.")

    st.markdown('<div class="section-title">3. Edge Cases</div>', unsafe_allow_html=True)
    if edge_cases:
        edge_df = pd.DataFrame([
            {
                "Title": item.get("title", ""),
                "Scenario": item.get("scenario", ""),
                "Expected Behavior": item.get("expected_behavior", ""),
            }
            for item in edge_cases
        ])
        st.dataframe(edge_df, use_container_width=True, hide_index=True)
    else:
        st.info("Edge Cases 결과가 없습니다.")

    st.markdown('<div class="section-title">4. QA Test Cases</div>', unsafe_allow_html=True)

    total = len(test_cases)
    high = sum(1 for t in test_cases if t.get("priority") == "High")
    medium = sum(1 for t in test_cases if t.get("priority") == "Medium")
    low = sum(1 for t in test_cases if t.get("priority") == "Low")

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        st.markdown(
            f'<div class="stat-box"><div class="num">{total}</div><div class="lbl">전체 테스트케이스</div></div>',
            unsafe_allow_html=True,
        )
    with q2:
        st.markdown(
            f'<div class="stat-box"><div class="num" style="color:#ef4444">{high}</div><div class="lbl">🔴 High Priority</div></div>',
            unsafe_allow_html=True,
        )
    with q3:
        st.markdown(
            f'<div class="stat-box"><div class="num" style="color:#f59e0b">{medium}</div><div class="lbl">🟡 Medium Priority</div></div>',
            unsafe_allow_html=True,
        )
    with q4:
        st.markdown(
            f'<div class="stat-box"><div class="num" style="color:#10b981">{low}</div><div class="lbl">🟢 Low Priority</div></div>',
            unsafe_allow_html=True,
        )

    priority_filter = st.multiselect(
        "우선순위 필터",
        options=["High", "Medium", "Low"],
        default=["High", "Medium", "Low"],
        key="saved_priority_filter",
    )

    filtered = [t for t in test_cases if t.get("priority") in priority_filter]

    if filtered:
        df = pd.DataFrame([
            {
                "TC #": t.get("id", ""),
                "Test Case": t.get("test_case", ""),
                "Description": t.get("description", ""),
                "Expected Result": t.get("expected_result", ""),
                "Priority": t.get("priority", ""),
            }
            for t in filtered
        ])

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=min(80 + len(filtered) * 55, 700),
        )

        st.download_button(
            label="⬇️ QA CSV 다운로드",
            data=df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="qa_test_cases.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("선택된 우선순위에 해당하는 테스트케이스가 없습니다.")

    if html_report:
        st.download_button(
            label="🌐 HTML 리포트 다운로드",
            data=html_report,
            file_name="ai_review_report.html",
            mime="text/html",
            use_container_width=True,
        )

# ─────────────────────────────────────────────
# Session restore
# ─────────────────────────────────────────────
if "review_result" not in st.session_state:
    saved = load_saved_result()
    if saved:
        st.session_state["review_result"] = saved

# ─────────────────────────────────────────────
# Sidebar – API Key 입력
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 API 설정")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-api03-...",
        help="https://console.anthropic.com 에서 발급받은 API 키를 입력하세요.",
    )
    if api_key:
        st.success("API 키 입력 완료", icon="✅")
    else:
        st.warning("API 키를 입력해야 리뷰 결과 생성이 가능합니다.", icon="⚠️")

    st.markdown("---")
    st.markdown("**API 키 발급 방법**")
    st.markdown("1. [console.anthropic.com](https://console.anthropic.com) 접속")
    st.markdown("2. **API Keys** 메뉴 → **Create Key**")
    st.markdown("3. 발급된 키를 위 입력란에 붙여넣기")

    if st.button("🗑 저장된 결과 초기화", use_container_width=True):
        if "review_result" in st.session_state:
            del st.session_state["review_result"]
        if os.path.exists(RESULT_JSON_PATH):
            os.remove(RESULT_JSON_PATH)
        if os.path.exists(RESULT_HTML_PATH):
            os.remove(RESULT_HTML_PATH)
        st.success("저장된 결과를 초기화했습니다.")
        st.rerun()

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🤖 AI 기획 리뷰 툴</h1>
    <p>PPT 기획안을 업로드하면 AI가 UX Issues, Policy Gaps, Edge Cases, QA Test Cases를 자동으로 생성합니다.</p>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📎 PPT 기획안 업로드 (.pptx)", type=["pptx"])

if uploaded_file:
    prs = Presentation(uploaded_file)
    all_text = ""
    slide_texts = []

    for i, slide in enumerate(prs.slides):
        text = ""
        for shape in slide.shapes:
            if shape.shape_type == 19:
                table = shape.table
                for row in table.rows:
                    row_texts = []
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        if cell_text:
                            row_texts.append(cell_text)
                    if row_texts:
                        text += " | ".join(row_texts) + "\n"
            elif hasattr(shape, "text") and shape.text.strip():
                text += shape.text.strip() + "\n"

        slide_texts.append((i + 1, text))
        all_text += text + "\n"

    with st.expander("📄 추출된 PPT 내용 보기", expanded=False):
        for slide_num, text in slide_texts:
            if text.strip():
                st.markdown(f"**Slide {slide_num}**")
                st.markdown(
                    '<div class="slide-card">' + text.replace("\n", "<br>") + '</div>',
                    unsafe_allow_html=True,
                )

    st.divider()

    prompt = (
        "다음은 서비스 기획안이다.\n\n"
        "이 내용을 분석해서 다음을 작성하라.\n\n"
        "1. UX Issues\n"
        "2. Policy Gaps\n"
        "3. Edge Cases\n"
        "4. QA Test Cases\n\n"
        "기획안 내용:\n"
        + all_text
    )

    st.markdown('<div class="section-title">🧠 Claude 채팅에 붙여넣을 프롬프트</div>', unsafe_allow_html=True)
    col_prompt, col_btn = st.columns([5, 1])
    with col_prompt:
        st.text_area(
            "프롬프트",
            value=prompt,
            height=220,
            label_visibility="collapsed",
        )
    with col_btn:
        st.link_button(
            "💬 claude.ai\n열기",
            url="https://claude.ai",
            use_container_width=True,
        )

    st.divider()
    st.markdown('<div class="section-title">🧪 AI 리뷰 결과 생성 (API 키 필요)</div>', unsafe_allow_html=True)

    if st.button("✨ 리뷰 결과 생성하기", type="primary", use_container_width=True):
        if not api_key:
            st.error("왼쪽 사이드바에 Anthropic API 키를 먼저 입력해주세요.")
            st.stop()

        with st.spinner("Claude가 기획안을 분석 중입니다..."):
            client = anthropic.Anthropic(api_key=api_key)

            system_prompt = (
                "당신은 시니어 QA 엔지니어이자 서비스 기획 리뷰어입니다.\n"
                "서비스 기획안을 분석하여 아래 4개 항목을 모두 도출하세요.\n\n"
                "1. UX Issues\n"
                "2. Policy Gaps\n"
                "3. Edge Cases\n"
                "4. QA Test Cases\n\n"
                "반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.\n\n"
                '{\n'
                '  "ux_issues": [{"title": "", "description": "", "impact": ""}],\n'
                '  "policy_gaps": [{"title": "", "description": "", "recommendation": ""}],\n'
                '  "edge_cases": [{"title": "", "scenario": "", "expected_behavior": ""}],\n'
                '  "test_cases": [{"id": "TC-001", "test_case": "", "description": "", "expected_result": "", "priority": "High"}]\n'
                '}\n\n'
                "priority는 반드시 High / Medium / Low 중 하나만 사용하세요.\n"
                "ux_issues는 최소 5개 이상, policy_gaps는 최소 5개 이상, edge_cases는 최소 8개 이상, test_cases는 최소 15개 이상 생성하세요."
            )

            user_prompt = (
                "다음 서비스 기획안을 분석하여 아래 4개 항목을 모두 JSON으로 생성하세요.\n\n"
                "기획안 내용:\n" + all_text[:12000]
            )

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=7000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw = response.content[0].text.strip()

            try:
                if "```" in raw:
                    parts = raw.split("```")
                    if len(parts) > 1:
                        raw = parts[1]
                    if raw.startswith("json"):
                        raw = raw[4:]

                data = json.loads(raw.strip())
            except Exception:
                st.error("JSON 파싱 오류가 발생했습니다. 다시 시도해주세요.")
                st.code(raw)
                st.stop()

            result_data = {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_file_name": uploaded_file.name,
                "ux_issues": data.get("ux_issues", []),
                "policy_gaps": data.get("policy_gaps", []),
                "edge_cases": data.get("edge_cases", []),
                "test_cases": data.get("test_cases", []),
            }

            html_report = build_html_report(result_data)
            result_data["html_report"] = html_report

            st.session_state["review_result"] = result_data
            save_result_json(result_data)
            save_html_report(html_report)

            st.success("리뷰 결과가 저장되었습니다. 새로고침 후에도 유지됩니다.")
            st.rerun()

# 저장된 결과 렌더링
render_saved_results()