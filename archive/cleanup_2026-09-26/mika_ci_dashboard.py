from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


# =============================================================================
# PATH SETUP
# =============================================================================

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# =============================================================================
# DATA + PHASE 3
# =============================================================================

from phase3_answer_composer import compose_answer


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="MIKA CI",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# SOFT GRAPHITE UI
# =============================================================================

st.markdown(
    """
    <style>

    /* =========================================================
       GLOBAL
       ========================================================= */

    .stApp {
        background-color: #1F2329;
        color: #E6E8EB;
    }

    [data-testid="stAppViewContainer"] {
        background-color: #1F2329;
    }

    [data-testid="stHeader"] {
        background-color: rgba(31, 35, 41, 0.94);
    }

    .main {
        background-color: #1F2329;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }


    /* =========================================================
       SIDEBAR
       ========================================================= */

    [data-testid="stSidebar"] {
        background-color: #252A31;
        border-right: 1px solid #3A414A;
    }

    [data-testid="stSidebar"] > div:first-child {
        background-color: #252A31;
    }

    .sidebar-brand {
        padding: 8px 6px 20px 6px;
        border-bottom: 1px solid #3A414A;
        margin-bottom: 18px;
    }

    .sidebar-title {
        font-size: 23px;
        font-weight: 700;
        color: #E6E8EB;
        letter-spacing: 0.4px;
    }

    .sidebar-subtitle {
        color: #AEB4BC;
        font-size: 11px;
        margin-top: 4px;
    }

    .nav-heading {
        color: #8D96A1;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin: 16px 0 8px 3px;
    }


    /* =========================================================
       PAGE HEADER
       ========================================================= */

    .page-title {
        font-size: 32px;
        font-weight: 700;
        color: #E6E8EB;
        letter-spacing: -0.5px;
        margin-bottom: 3px;
    }

    .page-subtitle {
        color: #AEB4BC;
        font-size: 14px;
        margin-bottom: 25px;
    }


    /* =========================================================
       SECTION CARDS
       ========================================================= */

    .section-card {
        background-color: #292E35;
        border: 1px solid #3A414A;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 17px;
    }

    .section-title {
        color: #E6E8EB;
        font-size: 18px;
        font-weight: 650;
        margin-bottom: 5px;
    }

    .section-description {
        color: #AEB4BC;
        font-size: 12px;
    }


    /* =========================================================
       COMMAND CENTER
       ========================================================= */

    .command-header {
        background-color: #292E35;
        border: 1px solid #3A414A;
        border-radius: 12px;
        padding: 22px;
        margin-bottom: 18px;
    }

    .command-title {
        color: #E6E8EB;
        font-size: 21px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .command-subtitle {
        color: #AEB4BC;
        font-size: 12px;
    }

    .metric-card {
        background-color: #292E35;
        border: 1px solid #3A414A;
        border-radius: 10px;
        padding: 17px;
        min-height: 112px;
        margin-bottom: 14px;
    }

    .metric-label {
        color: #8D96A1;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }

    .metric-value {
        color: #E6E8EB;
        font-size: 27px;
        font-weight: 700;
        line-height: 1.1;
    }

    .metric-note {
        color: #AEB4BC;
        font-size: 10px;
        margin-top: 7px;
    }


    /* =========================================================
       COLLAPSIBLE COVERAGE SECTIONS
       ========================================================= */

    [data-testid="stExpander"] {
        background-color: #292E35;
        border: 1px solid #3A414A;
        border-radius: 9px;
        margin-bottom: 12px;
    }

    [data-testid="stExpander"] summary {
        color: #E6E8EB;
        font-weight: 600;
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        text-align: center;
    }

    [data-testid="stExpander"] summary > div {
        justify-content: center;
        flex: 0 1 auto;
    }

    [data-testid="stExpander"] summary span[data-testid="stMarkdownContainer"] p {
        text-align: center;
        width: 100%;
    }

    [data-testid="stExpander"] summary:hover {
        color: #A9CBD8;
    }

    .catalogue-card {
        background-color: #252A31;
        border: 1px solid #3A414A;
        border-radius: 8px;
        padding: 14px;
        margin-top: 5px;
    }

    .catalogue-row {
        color: #AEB4BC;
        font-size: 12px;
        padding: 7px 0;
        border-bottom: 1px solid #323840;
    }

    .catalogue-row:last-child {
        border-bottom: none;
    }

    .catalogue-number {
        color: #E6E8EB;
        font-weight: 650;
        float: right;
    }


    /* =========================================================
       CHAT
       ========================================================= */

    .question-card {
        background-color: #292E35;
        border-left: 3px solid #5C8FA8;
        border-radius: 7px;
        padding: 13px 16px;
        margin: 15px 0 10px 0;
    }

    .question-label {
        color: #8D96A1;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }

    .answer-card {
        background-color: #292E35;
        border: 1px solid #3A414A;
        border-radius: 10px;
        padding: 19px;
        margin-bottom: 18px;
    }

    .answer-label {
        color: #8D96A1;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }


    /* =========================================================
       BADGES
       ========================================================= */

    .badge {
        display: inline-block;
        padding: 4px 9px;
        margin-right: 5px;
        border-radius: 20px;
        font-size: 10px;
        font-weight: 600;
    }

    .badge-blue {
        background-color: #283842;
        border: 1px solid #486C7E;
        color: #A9CBD8;
    }

    .badge-grey {
        background-color: #30353C;
        border: 1px solid #48505A;
        color: #C0C6CD;
    }


    /* =========================================================
       EVIDENCE
       ========================================================= */

    .evidence-card {
        background-color: #252A31;
        border: 1px solid #3A414A;
        border-radius: 7px;
        padding: 11px 13px;
        margin: 7px 0;
    }

    .evidence-title {
        color: #E0E4E8;
        font-size: 13px;
        font-weight: 600;
    }

    .evidence-meta {
        color: #AEB4BC;
        font-size: 11px;
        margin-top: 4px;
        line-height: 1.5;
    }


    /* =========================================================
       LIMITATIONS
       ========================================================= */

    .limitation-card {
        background-color: #292E35;
        border: 1px solid #3A414A;
        border-radius: 7px;
        padding: 11px 13px;
        margin: 7px 0;
        color: #AEB4BC;
        font-size: 12px;
        line-height: 1.5;
    }


    /* =========================================================
       BUTTONS
       ========================================================= */

    .stButton > button {
        background-color: #292E35;
        color: #E6E8EB;
        border: 1px solid #3A414A;
        border-radius: 7px;
        min-height: 38px;
    }

    .stButton > button:hover {
        background-color: #323840;
        border-color: #5C8FA8;
        color: #FFFFFF;
    }

    .stButton > button[kind="primary"] {
        background-color: #3A5968;
        border-color: #527D91;
        color: #F1F5F7;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: #456879;
        border-color: #6A98AC;
        color: #FFFFFF;
    }


    /* =========================================================
       INPUTS
       ========================================================= */

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div {
        background-color: #292E35;
        border-color: #3A414A;
    }

    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea {
        color: #E6E8EB;
    }

    div[data-baseweb="input"] input::placeholder,
    div[data-baseweb="textarea"] textarea::placeholder {
        color: #8D96A1;
    }


    /* =========================================================
       DIVIDERS
       ========================================================= */

    hr {
        border-color: #3A414A;
    }


    /* =========================================================
       FOOTER
       ========================================================= */

    .footer {
        color: #7F8994;
        text-align: center;
        font-size: 10px;
        padding: 28px 0 10px 0;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# APPLICATION HELPERS
# =============================================================================

def ask_mika(question: str):
    """
    Send a question to the verified Phase 3D answer composer.

    Phase 3D performs its own question routing internally.

    This dashboard layer performs no database writes.
    """
    clean_question = question.strip()

    if not clean_question:
        return None

    return compose_answer(clean_question)


def render_answer(answer):
    """Render a Phase 3D Answer object."""

    if answer is None:
        return

    # -------------------------------------------------------------------------
    # ANSWER
    # -------------------------------------------------------------------------

    st.markdown(
        """
        <div class="answer-card">
            <div class="answer-label">MIKA CI Answer</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(answer.answer)

    st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # CLASSIFICATION
    # -------------------------------------------------------------------------

    st.markdown("#### Query classification")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""
            <span class="badge badge-blue">
                {answer.intent}
            </span>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <span class="badge badge-grey">
                Confidence: {answer.confidence}
            </span>
            """,
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # EVIDENCE
    # -------------------------------------------------------------------------

    if answer.evidence:

        st.markdown("#### Evidence")

        for item in answer.evidence:

            if isinstance(item, dict):

                title = (
                    item.get("title")
                    or item.get("summary")
                    or item.get("campaign_name")
                    or item.get("product_name")
                    or item.get("alert_type")
                    or item.get("trend_type")
                    or "Evidence record"
                )

                metadata = []

                for field in (
                    "competitor_name",
                    "brand",
                    "category",
                    "observed_date",
                    "published_date",
                    "period_start",
                    "period_end",
                    "confidence",
                    "verification_status",
                    "coverage_status",
                ):
                    value = item.get(field)

                    if value not in (None, ""):
                        metadata.append(
                            f"{field}: {value}"
                        )

                meta_text = " · ".join(metadata)

                st.markdown(
                    f"""
                    <div class="evidence-card">
                        <div class="evidence-title">
                            {title}
                        </div>
                        <div class="evidence-meta">
                            {meta_text}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            else:

                st.markdown(
                    f"""
                    <div class="evidence-card">
                        <div class="evidence-title">
                            {item}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # -------------------------------------------------------------------------
    # LIMITATIONS
    # -------------------------------------------------------------------------

    if answer.limitations:

        with st.expander(
            "Evidence limitations",
            expanded=False,
        ):

            for limitation in answer.limitations:

                st.markdown(
                    f"""
                    <div class="limitation-card">
                        {limitation}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# =============================================================================
# SESSION STATE
# =============================================================================

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "Ask MIKA CI"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:

    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-title">MIKA CI</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # OVERVIEW
    # -------------------------------------------------------------------------

    navigation_overview = [
        "Ask MIKA CI",
    ]

    for page in navigation_overview:

        if st.button(
            page,
            key=f"nav_{page}",
            use_container_width=True,
        ):
            st.session_state.selected_page = page
            st.rerun()

    # -------------------------------------------------------------------------
    # INTELLIGENCE
    # -------------------------------------------------------------------------

    navigation_intelligence = [
        "Campaign Intelligence",
        "Product Intelligence",
        "Product Launches",
        "Market Trends",
        "Competitor Comparison",
        "Strategic Alerts",
    ]

    for page in navigation_intelligence:

        if st.button(
            page,
            key=f"nav_{page}",
            use_container_width=True,
        ):
            st.session_state.selected_page = page
            st.rerun()

    st.markdown("---")

    # -------------------------------------------------------------------------
    # REFRESH
    # -------------------------------------------------------------------------

    if st.button(
        "🔄 Refresh Data",
        key="refresh_data",
        use_container_width=True,
        type="primary",
    ):

        st.session_state.selected_page = "Ask MIKA CI"
        st.session_state.chat_history = []

        try:
            st.cache_data.clear()
        except Exception:
            pass

        try:
            st.cache_resource.clear()
        except Exception:
            pass

        st.toast("Data refreshed")
        st.rerun()




# =============================================================================
# HEADER
#
# Page title/subtitle intentionally hidden.
# =============================================================================


# =============================================================================
# ASK MIKA CI
# =============================================================================

if st.session_state.selected_page == "Ask MIKA CI":

    st.markdown(
        f'''
<div style="text-align:center; padding: 10px 0 20px 0;">
<img src="data:image/png;base64,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" width="240" alt="MIKA logo">
</div>
''',
        unsafe_allow_html=True,
    )

    question = st.text_input(
        "Question",
        placeholder="Example: What campaigns are active?",
        label_visibility="collapsed",
        key="main_question",
    )

    ask_col, clear_col = st.columns(2)

    with ask_col:

        ask_clicked = st.button(
            "Ask MIKA CI",
            key="main_ask",
            use_container_width=True,
            type="primary",
        )

    with clear_col:

        clear_clicked = st.button(
            "Clear conversation",
            key="clear_chat",
            use_container_width=True,
        )

    if clear_clicked:

        st.session_state.chat_history = []
        st.rerun()

    if ask_clicked and question.strip():

        answer = ask_mika(question)

        st.session_state.chat_history.append(
            {
                "question": question.strip(),
                "answer": answer,
            }
        )

    if st.session_state.chat_history:

        st.markdown("### Conversation")

        for item in reversed(
            st.session_state.chat_history
        ):

            st.markdown(
                f"""
                <div class="question-card">

                    <div class="question-label">
                        You
                    </div>

                    {item["question"]}

                </div>
                """,
                unsafe_allow_html=True,
            )

            render_answer(item["answer"])


# =============================================================================
# INTELLIGENCE PAGES
# =============================================================================

else:

    page_questions = {
        "Campaign Intelligence":
            "What campaigns are active?",

        "Product Intelligence":
            "What price movements have been detected?",

        "Product Launches":
            "What product launches have been detected?",

        "Market Trends":
            "What market trends are documented?",

        "Competitor Comparison":
            "Compare Hotpoint and Ramtons.",

        "Strategic Alerts":
            "What strategic alerts are open?",
    }

    current_page = st.session_state.selected_page

    # -------------------------------------------------------------------------
    # PAGE CONTENT
    #
    # The individual page title/description card has intentionally been
    # removed. The page now goes directly to the intelligence result.
    # -------------------------------------------------------------------------

    default_question = page_questions.get(current_page)

    if default_question:

        answer = ask_mika(default_question)

        render_answer(answer)

    st.markdown("### Ask a related question")

    follow_up = st.text_input(
        "Related question",
        placeholder="Ask another question about this area...",
        label_visibility="collapsed",
        key=f"followup_{current_page}",
    )

    if st.button(
        "Ask",
        key=f"page_ask_{current_page}",
        use_container_width=False,
    ):

        if follow_up.strip():

            answer = ask_mika(follow_up)

            st.markdown(
                f"""
                <div class="question-card">

                    <div class="question-label">
                        You
                    </div>

                    {follow_up.strip()}

                </div>
                """,
                unsafe_allow_html=True,
            )

            render_answer(answer)


# =============================================================================
# FOOTER
# =============================================================================

st.markdown(
    """
    <div class="footer">
        MIKA CI · Evidence-backed competitive intelligence ·
        SQLite source of truth
    </div>
    """,
    unsafe_allow_html=True,
)