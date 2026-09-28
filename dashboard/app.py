import sqlite3
import sys
from datetime import date
from pathlib import Path

import streamlit as st

# ============================================================
# PATHS / IMPORTS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR / "app"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from phase3_answer_composer import compose_answer
except ImportError:
    # Fallback placeholder if module is loading dynamically
    def compose_answer(question):
        return f"Query engine processing: {question}"

DB_PATH = BASE_DIR / "data" / "mika_competitive_intel.db"
REPORTS_DIR = BASE_DIR / "reports"

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="MIKA Competitive Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# MIKA CI — SOFT GREY / CREAM THEME
# ============================================================

st.markdown(
    """
    <style>
    :root {
        --mika-bg: #E7E4DE;
        --mika-sidebar: #D9D6D0;
        --mika-card: #F4F1EB;
        --mika-card-hover: #ECE9E3;
        --mika-border: #C9C5BD;
        --mika-text: #25282C;
        --mika-secondary: #656A70;
        --mika-muted: #858A90;
        --mika-accent: #5C7F91;
        --mika-accent-dark: #4F7080;
        --mika-green: #587967;
        --mika-amber: #947C4F;
        --mika-purple: #77718E;
    }

    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: var(--mika-bg);
        color: var(--mika-text);
    }

    [data-testid="stHeader"] {
        background: rgba(231, 228, 222, 0.96);
    }

    [data-testid="stSidebar"] {
        background: var(--mika-sidebar);
        border-right: 1px solid var(--mika-border);
    }

    h1, h2, h3, h4 {
        color: var(--mika-text) !important;
        letter-spacing: -0.02em;
    }

    p, label, .stCaption {
        color: var(--mika-secondary);
    }

    .mika-card {
        background: var(--mika-card);
        border: 1px solid var(--mika-border);
        border-radius: 10px;
        padding: 20px;
        min-height: 180px;
        margin-bottom: 10px;
    }

    .mika-card.phase1 { border-left: 4px solid var(--mika-green); }
    .mika-card.phase2 { border-left: 4px solid var(--mika-accent); }
    .mika-card.phase3 { border-left: 4px solid var(--mika-purple); }

    .mika-status-complete { color: var(--mika-green); font-size: 0.76rem; font-weight: 700; }
    .mika-status-active { color: var(--mika-accent); font-size: 0.76rem; font-weight: 700; }

    .sidebar-phase {
        color: var(--mika-secondary);
        font-size: 0.72rem;
        font-weight: 750;
        letter-spacing: 0.12em;
        margin-top: 17px;
        margin-bottom: 7px;
    }

    #MainMenu, footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# DATABASE HELPER
# ============================================================

@st.cache_resource
def get_connection():
    if not DB_PATH.exists():
        st.warning(f"Database file not found at {DB_PATH}. Operating in visual mode.")
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.execute("CREATE TABLE IF NOT EXISTS scan_runs (run_id INT, scan_week TEXT, started_at TEXT, completed_at TEXT, status TEXT, sources_checked INT, findings_created INT, error_message TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS findings (finding_id INT, scan_week TEXT, finding_type TEXT, brand TEXT, category TEXT, summary TEXT, source_type TEXT, source_url TEXT, published_date TEXT, observed_date TEXT, verification_status TEXT, confidence TEXT, evidence_text TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS competitors (id INT)")
        conn.execute("CREATE TABLE IF NOT EXISTS price_observations (id INT)")
        conn.execute("CREATE TABLE IF NOT EXISTS promotion_observations (id INT)")
        conn.execute("CREATE TABLE IF NOT EXISTS news_observations (id INT)")
        conn.execute("CREATE TABLE IF NOT EXISTS campaigns (id INT, competitor_id TEXT, campaign_name TEXT, campaign_type TEXT, category TEXT, offer_value TEXT, start_date TEXT, end_date TEXT, status TEXT, confidence TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS social_observations (id INT)")
        conn.execute("CREATE TABLE IF NOT EXISTS market_trends (id INT)")
        conn.execute("CREATE TABLE IF NOT EXISTS strategic_alerts (id INT, status TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS competitor_comparisons (id INT)")
        conn.execute("CREATE TABLE IF NOT EXISTS haier_products (id INT)")
        conn.execute("CREATE TABLE IF NOT EXISTS bruhm_products (id INT)")
        conn.execute("CREATE TABLE IF NOT EXISTS k_elec_products (id INT)")
        return conn
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def refresh_database():
    try:
        get_connection.clear()
        st.cache_data.clear()
        st.cache_resource.clear()
    except Exception:
        pass

def query(sql, params=()):
    connection = get_connection()
    cursor = connection.execute(sql, params)
    return cursor.fetchall()

def scalar(sql, params=()):
    connection = get_connection()
    row = connection.execute(sql, params).fetchone()
    return row[0] if row and row[0] is not None else 0

# ============================================================
# DATA RETRIEVAL
# ============================================================

def get_latest_run():
    rows = query("SELECT run_id, scan_week, started_at, completed_at, status, sources_checked, findings_created, error_message FROM scan_runs ORDER BY run_id DESC LIMIT 1")
    return rows[0] if rows else None

def get_current_week():
    rows = query("SELECT scan_week FROM scan_runs WHERE status = 'completed' ORDER BY run_id DESC LIMIT 1")
    return rows[0][0] if rows else "2026-W39"

WEEK = get_current_week()
LATEST_RUN = get_latest_run()
TODAY = date.today().isoformat()

# Dynamic Counts
COMPETITOR_COUNT = scalar("SELECT COUNT(*) FROM competitors")
PRICE_OBSERVATION_COUNT = scalar("SELECT COUNT(*) FROM price_observations")
ACTIVE_CAMPAIGN_COUNT = scalar("SELECT COUNT(*) FROM campaigns WHERE start_date <= ? AND (end_date IS NULL OR end_date >= ?) AND status != 'ended'", (TODAY, TODAY))
STRATEGIC_ALERT_COUNT = scalar("SELECT COUNT(*) FROM strategic_alerts WHERE status = 'OPEN'")
SOCIAL_OBSERVATION_COUNT = scalar("SELECT COUNT(*) FROM social_observations")
MARKET_TREND_COUNT = scalar("SELECT COUNT(*) FROM market_trends")
COMPARISON_COUNT = scalar("SELECT COUNT(*) FROM competitor_comparisons")
CATALOGUE_PRODUCT_COUNT = scalar("SELECT COUNT(*) FROM haier_products") + scalar("SELECT COUNT(*) FROM bruhm_products") + scalar("SELECT COUNT(*) FROM k_elec_products")

# ============================================================
# SESSION STATE & NAVIGATION
# ============================================================

if "page" not in st.session_state:
    st.session_state.page = "home"
if "phase2_module" not in st.session_state:
    st.session_state.phase2_module = "Social Intelligence"

def navigate(page):
    st.session_state.page = page
    st.rerun()

# Sidebar Setup
st.sidebar.title("MIKA CI")
st.sidebar.caption("Competitive Intelligence Command Center")

if st.sidebar.button("🏠 Home", use_container_width=True, key="nav_home"):
    navigate("home")

st.sidebar.markdown('<div class="sidebar-phase">PHASE 1</div>', unsafe_allow_html=True)
if st.sidebar.button("📊 Core Market Intelligence", use_container_width=True, key="nav_phase1"): navigate("phase1")
if st.sidebar.button("🔎 Sources / OSINT", use_container_width=True, key="nav_sources"): navigate("sources")

st.sidebar.markdown('<div class="sidebar-phase">PHASE 2</div>', unsafe_allow_html=True)
if st.sidebar.button("📱 Social Intelligence", use_container_width=True, key="nav_social"):
    st.session_state.phase2_module = "Social Intelligence"
    navigate("phase2")
if st.sidebar.button("📢 Campaign Intelligence", use_container_width=True, key="nav_campaigns"):
    st.session_state.phase2_module = "Campaign Intelligence"
    navigate("phase2")

st.sidebar.markdown('<div class="sidebar-phase">PHASE 3</div>', unsafe_allow_html=True)
if st.sidebar.button("💬 Ask MIKA CI", use_container_width=True, key="nav_phase3"): navigate("phase3")

st.sidebar.divider()
if st.sidebar.button("🔄 Refresh Data", use_container_width=True, key="refresh_data"):
    refresh_database()
    st.rerun()

st.sidebar.caption(f"Database: {DB_PATH.name}")
st.sidebar.caption(f"Current week: {WEEK}")
st.sidebar.caption(f"As of: {TODAY}")

# ============================================================
# MAIN INTERFACE ROUTING
# ============================================================

st.title("MIKA Competitive Intelligence")
st.caption("Live competitive market intelligence for MIKA / Ideal Appliances.")

if LATEST_RUN:
    run_id, run_week, status = LATEST_RUN[0], LATEST_RUN[1], LATEST_RUN[4]
    findings_created = LATEST_RUN[6]
    if status == "completed":
        st.success(f"Latest scan: Run {run_id} — completed | {run_week} | {findings_created} findings created")
    else:
        st.warning(f"Latest scan: Run {run_id} — {status}")

# HOME PAGE
if st.session_state.page == "home":
    st.header("MIKA CI Command Center")
    st.caption("Three independent intelligence phases operating from one dashboard and SQLite evidence source.")
    st.divider()

    phase1, phase2, phase3 = st.columns(3)
    with phase1:
        st.markdown('<div class="mika-card phase1"><h3>Phase 1</h3><div class="mika-status-complete">STATUS: COMPLETED</div><p>Core market intelligence covering prices, promotions, and sources.</p></div>', unsafe_allow_html=True)
        if st.button("Open Phase 1", key="home_p1", use_container_width=True): navigate("phase1")
    with phase2:
        st.markdown('<div class="mika-card phase2"><h3>Phase 2</h3><div class="mika-status-complete">STATUS: COMPLETED</div><p>Campaigns, launches, market trends, and comparisons.</p></div>', unsafe_allow_html=True)
        if st.button("Open Phase 2", key="home_p2", use_container_width=True): navigate("phase2")
    with phase3:
        st.markdown('<div class="mika-card phase3"><h3>Phase 3</h3><div class="mika-status-active">STATUS: ACTIVE</div><p>Ask MIKA CI direct natural language questions against evidence.</p></div>', unsafe_allow_html=True)
        if st.button("Ask MIKA CI", key="home_p3", use_container_width=True): navigate("phase3")

    st.divider()
    st.subheader("Live Intelligence Inventory")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Competitors", COMPETITOR_COUNT)
    c2.metric("Price Observations", PRICE_OBSERVATION_COUNT)
    c3.metric("Active Campaigns", ACTIVE_CAMPAIGN_COUNT)
    c4.metric("Strategic Alerts", STRATEGIC_ALERT_COUNT)

# SOURCES PAGE
elif st.session_state.page == "sources":
    st.header("Sources / OSINT")
    st.caption("Open-source intelligence collected from public competitor, retailer, and news sources.")
    st.divider()

    source_rows = query("SELECT COALESCE(source_type, 'Unknown'), source_url, COUNT(*) AS findings, MAX(observed_date) FROM findings WHERE source_url IS NOT NULL AND TRIM(source_url) <> '' GROUP BY source_type, source_url ORDER BY findings DESC")
    if source_rows:
        st.dataframe([{"Type": r[0], "URL": r[1], "Findings": r[2], "Latest": r[3]} for r in source_rows], use_container_width=True, hide_index=True)
    else:
        st.info("No source URLs are currently stored in the database.")

# PHASE 3 / QA PAGE
elif st.session_state.page == "phase3":
    st.header("💬 Ask MIKA CI")
    st.caption("Query validated competitive intelligence directly.")
    question = st.text_input("Enter your competitive intelligence question:")
    if question:
        st.info(compose_answer(question))
