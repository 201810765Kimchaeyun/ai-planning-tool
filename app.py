import streamlit as st
from pptx import Presentation
import anthropic
import json
import pandas as pd

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI 기획 리뷰 툴",
    page_icon="🤖",
    layout="wide",
)

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
        st.warning("API 키를 입력해야 QA 생성이 가능합니다.", icon="⚠️")

    st.markdown("---")
    st.markdown("**API 키 발급 방법**")
    st.markdown("1. [console.anthropic.com](https://console.anthropic.com) 접속")
    st.markdown("2. **API Keys** 메뉴 → **Create Key**")
    st.markdown("3. 발급된 키를 위 입력란에 붙여넣기")

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🤖 AI 기획 리뷰 툴</h1>
    <p>PPT 기획안을 업로드하면 AI가 QA 테스트케이스를 자동으로 생성합니다.</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# File upload
# ─────────────────────────────────────────────
uploaded_file = st.file_uploader("📎 PPT 기획안 업로드 (.pptx)", type=["pptx"])

if uploaded_file:
    # ── PPT 텍스트 추출 ───────────────────────
    prs = Presentation(uploaded_file)
    all_text = ""
    slide_texts = []

    for i, slide in enumerate(prs.slides):
        text = ""
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                text += shape.text.strip() + "\n"
        slide_texts.append((i + 1, text))
        all_text += text + "\n"

    # ── 슬라이드 미리보기 ─────────────────────
    with st.expander("📄 추출된 PPT 내용 보기", expanded=False):
        for slide_num, text in slide_texts:
            if text.strip():
                st.markdown("**Slide " + str(slide_num) + "**")
                st.markdown(
                    '<div class="slide-card">' + text.replace("\n", "<br>") + '</div>',
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── QA 생성 버튼 ──────────────────────────
    st.markdown('<div class="section-title">🧪 QA 테스트케이스 자동 생성</div>', unsafe_allow_html=True)

    if st.button("✨ QA 테스트케이스 생성하기", type="primary", use_container_width=True):

        # API 키 미입력 시 중단
        if not api_key:
            st.error("왼쪽 사이드바에 Anthropic API 키를 먼저 입력해주세요.")
            st.stop()

        with st.spinner("Claude가 기획안을 분석 중입니다..."):

            # ── Claude API 호출 (api_key 명시 전달) ──
            client = anthropic.Anthropic(api_key=api_key)

            system_prompt = (
                "당신은 시니어 QA 엔지니어입니다.\n"
                "서비스 기획안을 분석하여 QA 테스트케이스를 생성하세요.\n\n"
                "반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.\n\n"
                '{\n'
                '  "test_cases": [\n'
                '    {\n'
                '      "id": "TC-001",\n'
                '      "test_case": "테스트 케이스 이름",\n'
                '      "description": "상세 테스트 시나리오 설명",\n'
                '      "expected_result": "기대 결과",\n'
                '      "priority": "High"\n'
                '    }\n'
                '  ]\n'
                '}\n\n'
                "priority는 반드시 High / Medium / Low 중 하나만 사용하세요.\n"
                "기획안의 핵심 기능, 경계값, 예외 상황을 중심으로 최소 15개 이상의 테스트케이스를 생성하세요."
            )

            user_prompt = (
                "다음 서비스 기획안을 분석하여 QA 테스트케이스를 JSON으로 생성하세요.\n\n"
                "기획안 내용:\n"
                + all_text[:8000]
            )

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw = response.content[0].text.strip()

            # ── JSON 파싱 ─────────────────────
            try:
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                data = json.loads(raw.strip())
                test_cases = data.get("test_cases", [])
            except Exception:
                st.error("JSON 파싱 오류가 발생했습니다. 다시 시도해주세요.")
                st.code(raw)
                st.stop()

        # ── 통계 요약 ─────────────────────────
        total  = len(test_cases)
        high   = sum(1 for t in test_cases if t.get("priority") == "High")
        medium = sum(1 for t in test_cases if t.get("priority") == "Medium")
        low    = sum(1 for t in test_cases if t.get("priority") == "Low")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                '<div class="stat-box"><div class="num">' + str(total) + '</div>'
                '<div class="lbl">전체 테스트케이스</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                '<div class="stat-box"><div class="num" style="color:#ef4444">' + str(high) + '</div>'
                '<div class="lbl">🔴 High Priority</div></div>',
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                '<div class="stat-box"><div class="num" style="color:#f59e0b">' + str(medium) + '</div>'
                '<div class="lbl">🟡 Medium Priority</div></div>',
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                '<div class="stat-box"><div class="num" style="color:#10b981">' + str(low) + '</div>'
                '<div class="lbl">🟢 Low Priority</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── 우선순위 필터 ─────────────────────
        priority_filter = st.multiselect(
            "우선순위 필터",
            options=["High", "Medium", "Low"],
            default=["High", "Medium", "Low"],
        )

        filtered = [t for t in test_cases if t.get("priority") in priority_filter]

        # ── 테이블 렌더링 ─────────────────────
        if filtered:
            df = pd.DataFrame([
                {
                    "TC #":            t.get("id", ""),
                    "Test Case":       t.get("test_case", ""),
                    "Description":     t.get("description", ""),
                    "Expected Result": t.get("expected_result", ""),
                    "Priority":        t.get("priority", ""),
                }
                for t in filtered
            ])

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "TC #":            st.column_config.TextColumn("TC #", width="small"),
                    "Test Case":       st.column_config.TextColumn("Test Case", width="medium"),
                    "Description":     st.column_config.TextColumn("Description", width="large"),
                    "Expected Result": st.column_config.TextColumn("Expected Result", width="large"),
                    "Priority":        st.column_config.SelectboxColumn(
                        "Priority",
                        options=["High", "Medium", "Low"],
                        width="small",
                    ),
                },
                height=min(80 + len(filtered) * 55, 700),
            )

            # ── CSV 다운로드 ──────────────────
            st.download_button(
                label="⬇️ CSV로 다운로드",
                data=df.to_csv(index=False, encoding="utf-8-sig"),
                file_name="qa_test_cases.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("선택된 우선순위에 해당하는 테스트케이스가 없습니다.")