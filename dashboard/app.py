import sqlite3
import sys
import urllib.request
from datetime import date
from pathlib import Path
import streamlit as st


# ============================================================
# PATHS / IMPORTS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

DB_PATH = DATA_DIR / "mika_competitive_intel.db"

GITHUB_DB_URL = (
    "https://raw.githubusercontent.com/"
    "ogutujane27-debug/mika_ci/main/"
    "data/mika_competitive_intel.db"
)


def ensure_database_from_github(force=False):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists() and DB_PATH.is_file() and not force:
        return True

    try:
        urllib.request.urlretrieve(
            GITHUB_DB_URL,
            str(DB_PATH)
        )

        return (
            DB_PATH.exists()
            and DB_PATH.is_file()
            and DB_PATH.stat().st_size > 0
        )

    except Exception:
        try:
            if DB_PATH.exists():
                DB_PATH.unlink()
        except Exception:
            pass

        return False


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
# MIKA CI — WHITE / HIGH VISIBILITY THEME
# ============================================================

st.markdown(
    """
    <style>

    :root {
        --mika-bg: #FFFFFF;
        --mika-sidebar: #F3F5F7;

        --mika-card: #FFFFFF;
        --mika-card-hover: #F7F9FA;

        --mika-border: #C7CED4;

        --mika-text: #17212B;
        --mika-secondary: #42505C;
        --mika-muted: #66737E;

        --mika-blue: #0B5E75;
        --mika-blue-dark: #08485A;
        --mika-blue-soft: #D9EDF3;

        --mika-green: #176B4D;
        --mika-green-dark: #104A36;
        --mika-green-soft: #DDEFE7;

        --mika-amber: #8A5A00;
        --mika-amber-dark: #694400;
        --mika-amber-soft: #F7EBD0;

        --mika-red: #8B2E2E;
        --mika-red-dark: #692020;
        --mika-red-soft: #F5E0E0;

        --mika-purple: #5B4B7A;
        --mika-purple-soft: #ECE7F5;

        --mika-cyan: #087E8B;
        --mika-cyan-soft: #E1F3F5;
    }


    /* ========================================================
       MAIN APP
       ======================================================== */

    .stApp {
        background: #FFFFFF;
        color: var(--mika-text);
    }

    [data-testid="stAppViewContainer"] {
        background: #FFFFFF;
    }

    [data-testid="stMain"] {
        background: #FFFFFF;
    }

    [data-testid="stHeader"] {
        background: #FFFFFF;
        border-bottom: 1px solid var(--mika-border);
    }


    /* ========================================================
       SIDEBAR
       ======================================================== */

    [data-testid="stSidebar"] {
        background: var(--mika-sidebar);
        border-right: 1px solid var(--mika-border);
    }

    [data-testid="stSidebarContent"] {
        padding-top: 1rem;
    }

    [data-testid="stSidebar"] * {
        color: var(--mika-text);
    }

    [data-testid="stSidebar"] .stCaption {
        color: var(--mika-secondary);
    }


    /* ========================================================
       TYPOGRAPHY
       ======================================================== */

    h1,
    h2,
    h3,
    h4 {
        color: var(--mika-text) !important;
        letter-spacing: -0.02em;
    }

    h1 {
        font-weight: 700 !important;
    }

    h2,
    h3 {
        font-weight: 650 !important;
    }

    p,
    label,
    .stCaption {
        color: var(--mika-secondary);
    }

    [data-testid="stMarkdownContainer"] p {
        color: var(--mika-secondary);
    }


    /* ========================================================
       BUTTONS
       ======================================================== */

    .stButton > button,
    .stLinkButton > a {
        background: #FFFFFF;
        color: var(--mika-text);
        border: 1px solid var(--mika-border);
        border-radius: 7px;
        min-height: 40px;
        font-weight: 600;
        transition: all 0.15s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }

    .stButton > button:hover,
    .stLinkButton > a:hover {
        background: var(--mika-blue-soft);
        color: var(--mika-blue-dark);
        border-color: var(--mika-blue);
    }

    .stButton > button[kind="primary"] {
        background: var(--mika-blue);
        color: #FFFFFF;
        border-color: var(--mika-blue);
    }

    .stButton > button[kind="primary"]:hover {
        background: var(--mika-blue-dark);
        color: #FFFFFF;
        border-color: var(--mika-blue-dark);
    }


    /* ========================================================
       SIDEBAR BUTTONS
       ======================================================== */

    [data-testid="stSidebar"] .stButton > button {
        text-align: left;
        justify-content: flex-start;

        background: #FFFFFF;
        color: var(--mika-text);

        border: 1px solid var(--mika-border);
        border-radius: 7px;

        margin-bottom: 5px;
        min-height: 38px;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: var(--mika-blue-soft);
        border-color: var(--mika-blue);
        color: var(--mika-blue-dark);
    }


    /* ========================================================
       METRICS
       ======================================================== */

    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid var(--mika-border);
        border-radius: 9px;
        padding: 14px 16px;

        box-shadow:
            0 1px 3px rgba(0, 0, 0, 0.06);
    }

    [data-testid="stMetricLabel"] {
        color: var(--mika-secondary) !important;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: var(--mika-text) !important;
        font-weight: 700;
    }

    [data-testid="stMetricDelta"] {
        color: var(--mika-secondary) !important;
    }


    /* ========================================================
       DATAFRAMES
       ======================================================== */

    [data-testid="stDataFrame"] {
        background: #FFFFFF;
        border: 1px solid var(--mika-border);
        border-radius: 8px;
        overflow: hidden;
    }


    /* ========================================================
       SELECTBOX
       ======================================================== */

    [data-baseweb="select"] > div {
        background: #FFFFFF;
        border-color: var(--mika-border);
        color: var(--mika-text);
    }

    [data-baseweb="select"] input {
        color: var(--mika-text) !important;
    }


    /* ========================================================
       TEXT INPUTS
       ======================================================== */

    [data-baseweb="textarea"] {
        background: #FFFFFF;
        border-color: var(--mika-border);
    }

    textarea,
    input {
        color: var(--mika-text) !important;
        background: #FFFFFF !important;
    }

    textarea::placeholder,
    input::placeholder {
        color: var(--mika-muted) !important;
    }


    /* ========================================================
       EXPANDERS
       ======================================================== */

    [data-testid="stExpander"] {
        background: #FFFFFF;
        border: 1px solid var(--mika-border);
        border-radius: 8px;
    }

    [data-testid="stExpander"] summary {
        color: var(--mika-text);
        font-weight: 600;
    }


    /* ========================================================
       ALERTS
       ======================================================== */

    [data-testid="stAlert"] {
        border-radius: 8px;
    }


    /* ========================================================
       DIVIDERS
       ======================================================== */

    hr {
        border-color: var(--mika-border);
    }


    /* ========================================================
       SECTION LABELS
       ======================================================== */

    .sidebar-phase {
        color: var(--mika-blue-dark);
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        margin-top: 17px;
        margin-bottom: 7px;
    }


    /* ========================================================
       CARDS
       ======================================================== */

    .mika-card {
        background: #FFFFFF;

        border: 1px solid var(--mika-border);
        border-radius: 10px;

        padding: 20px;

        min-height: 190px;

        margin-bottom: 10px;

        box-shadow:
            0 1px 3px rgba(0, 0, 0, 0.05);
    }

    .mika-card.phase1 {
        border-left: 5px solid var(--mika-green);
    }

    .mika-card.phase2 {
        border-left: 5px solid var(--mika-blue);
    }

    .mika-card.phase3 {
        border-left: 5px solid var(--mika-purple);
    }


    /* ========================================================
       STATUS LABELS
       ======================================================== */

    .mika-status-complete {
        color: var(--mika-green-dark);

        font-size: 0.76rem;
        font-weight: 800;

        letter-spacing: 0.08em;
    }

    .mika-status-active {
        color: var(--mika-blue-dark);

        font-size: 0.76rem;
        font-weight: 800;

        letter-spacing: 0.08em;
    }

    .mika-status-progress {
        color: var(--mika-amber-dark);

        font-size: 0.76rem;
        font-weight: 800;

        letter-spacing: 0.08em;
    }


    /* ========================================================
       DATABASE STATUS
       ======================================================== */

    .db-connected {
        display: inline-block;

        background: var(--mika-green-soft);
        color: var(--mika-green-dark);

        border: 1px solid #B9DCC5;

        border-radius: 6px;

        padding: 5px 9px;

        font-size: 0.78rem;
        font-weight: 800;
    }

    .db-missing {
        display: inline-block;

        background: var(--mika-red-soft);
        color: var(--mika-red-dark);

        border: 1px solid #E9B9B4;

        border-radius: 6px;

        padding: 5px 9px;

        font-size: 0.78rem;
        font-weight: 800;
    }


    /* ========================================================
       DATABASE PATH
       ======================================================== */

    .db-path-box {
        background: #F7F9FA;

        border: 1px solid var(--mika-border);
        border-radius: 8px;

        padding: 12px 14px;

        font-family: monospace;
        font-size: 0.85rem;

        color: var(--mika-text);

        overflow-x: auto;
    }


    /* ========================================================
       HIDE STREAMLIT CHROME
       ======================================================== */

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }


    /* ========================================================
       MOBILE
       ======================================================== */

    @media (max-width: 800px) {

        .mika-card {
            min-height: auto;
        }

    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE AVAILABILITY
# ============================================================

def database_available():
    return ensure_database_from_github()


# ============================================================
# PHASE 3 IMPORT
# ============================================================


def get_phase3_composer():
    """
    Load Phase 3 safely.

    A Phase 3 import problem must never prevent
    the rest of the dashboard from loading.
    """

    try:
        from phase3_answer_composer import compose_answer

        return compose_answer, None

    except Exception as exc:
        return None, exc


# ============================================================
# DATABASE CONNECTION
# ============================================================

@st.cache_resource
def get_connection():
    if not ensure_database_from_github():
        raise FileNotFoundError(
            "The real MIKA CI database could not be loaded from GitHub."
        )

    connection = sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False,
        timeout=30,
    )

    return connection

# ============================================================
# DATABASE REFRESH
# ============================================================

def refresh_database():
    """
    Refresh the dashboard SQLite connection and caches.

    Does not modify SQLite records or schema.
    """

    try:
        connection = get_connection()
        connection.close()
    except Exception:
        pass

    try:
        get_connection.clear()
    except Exception:
        pass

    try:
        st.cache_data.clear()
    except Exception:
        pass

    try:
        st.cache_resource.clear()
    except Exception:
        pass


# ============================================================
# DATABASE QUERY HELPERS
# ============================================================

def query(sql, params=()):
    """
    Execute a query against the real SQLite database.
    """

    connection = get_connection()

    cursor = connection.execute(
        sql,
        params,
    )

    return cursor.fetchall()


def scalar(sql, params=(), default=0):
    """
    Execute a scalar query safely.
    """

    try:
        connection = get_connection()

        row = connection.execute(
            sql,
            params,
        ).fetchone()

        if row and row[0] is not None:
            return row[0]

        return default

    except Exception:
        return default


def safe_query(sql, params=(), default=None):
    """
    Safe dashboard query.
    """

    if default is None:
        default = []

    try:
        return query(
            sql,
            params,
        )

    except Exception:
        return default


# ============================================================
# DATABASE INFORMATION
# ============================================================

def get_latest_run():

    rows = safe_query(
        """
        SELECT
            run_id,
            scan_week,
            started_at,
            completed_at,
            status,
            sources_checked,
            findings_created,
            error_message
        FROM scan_runs
        ORDER BY run_id DESC
        LIMIT 1
        """
    )

    return rows[0] if rows else None


def get_current_week():

    rows = safe_query(
        """
        SELECT
            scan_week
        FROM scan_runs
        WHERE status = 'completed'
        ORDER BY run_id DESC
        LIMIT 1
        """
    )

    return rows[0][0] if rows else "N/A"


# ============================================================
# CURRENT DATA
# ============================================================

TODAY = date.today().isoformat()

if database_available():
    WEEK = get_current_week()
    LATEST_RUN = get_latest_run()
else:
    WEEK = "N/A"
    LATEST_RUN = None


# ============================================================
# PHASE 1 COUNTS
# ============================================================

TOTAL_FINDINGS = scalar(
    """
    SELECT COUNT(*)
    FROM findings
    WHERE scan_week = ?
    """,
    (WEEK,),
)

PRICE_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM findings
    WHERE scan_week = ?
      AND finding_type = 'price'
    """,
    (WEEK,),
)

PROMOTION_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM findings
    WHERE scan_week = ?
      AND finding_type = 'promotion'
    """,
    (WEEK,),
)

NEWS_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM findings
    WHERE scan_week = ?
      AND finding_type = 'news'
    """,
    (WEEK,),
)

COMPETITOR_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM competitors
    """
)

PRICE_OBSERVATION_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM price_observations
    """
)

PROMOTION_OBSERVATION_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM promotion_observations
    """
)

NEWS_OBSERVATION_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM news_observations
    """
)


# ============================================================
# PHASE 2 COUNTS
# ============================================================

ACTIVE_CAMPAIGN_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM campaigns
    WHERE start_date IS NOT NULL
      AND start_date <= ?
      AND (
          end_date IS NULL
          OR end_date >= ?
      )
      AND status != 'ended'
    """,
    (
        TODAY,
        TODAY,
    ),
)

UPCOMING_CAMPAIGN_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM campaigns
    WHERE start_date IS NOT NULL
      AND start_date > ?
      AND status = 'upcoming'
    """,
    (TODAY,),
)

SOCIAL_OBSERVATION_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM social_observations
    """
)

MARKET_TREND_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM market_trends
    """
)

STRATEGIC_ALERT_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM strategic_alerts
    WHERE status = 'OPEN'
    """
)

COMPARISON_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM competitor_comparisons
    """
)

HAIER_PRODUCT_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM haier_products
    """
)

BRUHM_PRODUCT_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM bruhm_products
    """
)

K_ELEC_PRODUCT_COUNT = scalar(
    """
    SELECT COUNT(*)
    FROM k_elec_products
    """
)

CATALOGUE_PRODUCT_COUNT = (
    HAIER_PRODUCT_COUNT
    + BRUHM_PRODUCT_COUNT
    + K_ELEC_PRODUCT_COUNT
)


# ============================================================
# SESSION STATE
# ============================================================

if "page" not in st.session_state:
    st.session_state.page = "home"

if "phase2_module" not in st.session_state:
    st.session_state.phase2_module = "Social Intelligence"

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = 0


# ============================================================
# NAVIGATION
# ============================================================

def navigate(page):

    st.session_state.page = page

    st.rerun()


# ============================================================
# SIDEBAR
# ============================================================

# Clean text only.
# No raw HTML branding is used here.

st.sidebar.title("MIKA CI")

st.sidebar.caption(
    "Competitive Intelligence"
)


# ============================================================
# HOME NAVIGATION
# ============================================================

if st.sidebar.button(
    "🏠 Home",
    use_container_width=True,
    key="nav_home",
):
    navigate("home")


# ============================================================
# PHASE 1
# ============================================================

st.sidebar.markdown(
    "### PHASE 1"
)

if st.sidebar.button(
    "📊 Core Market Intelligence",
    use_container_width=True,
    key="nav_phase1",
):
    navigate("phase1")


if st.sidebar.button(
    "🔎 Sources / OSINT",
    use_container_width=True,
    key="nav_sources",
):
    navigate("sources")


# ============================================================
# PHASE 2
# ============================================================

st.sidebar.markdown(
    "### PHASE 2"
)

if st.sidebar.button(
    "📱 Social Intelligence",
    use_container_width=True,
    key="nav_social",
):
    st.session_state.phase2_module = "Social Intelligence"
    navigate("phase2")


if st.sidebar.button(
    "📢 Campaign Intelligence",
    use_container_width=True,
    key="nav_campaigns",
):
    st.session_state.phase2_module = "Campaign Intelligence"
    navigate("phase2")


if st.sidebar.button(
    "📦 Product Intelligence",
    use_container_width=True,
    key="nav_products",
):
    st.session_state.phase2_module = "Product Intelligence"
    navigate("phase2")


if st.sidebar.button(
    "🚀 Product Launches",
    use_container_width=True,
    key="nav_launches",
):
    st.session_state.phase2_module = "Product Launches"
    navigate("phase2")


if st.sidebar.button(
    "📈 Market Trends",
    use_container_width=True,
    key="nav_trends",
):
    st.session_state.phase2_module = "Market Trends"
    navigate("phase2")


if st.sidebar.button(
    "⚖️ Competitor Comparison",
    use_container_width=True,
    key="nav_comparison",
):
    st.session_state.phase2_module = "Competitor Comparison"
    navigate("phase2")


if st.sidebar.button(
    "🚨 Strategic Alerts",
    use_container_width=True,
    key="nav_alerts",
):
    st.session_state.phase2_module = "Strategic Alerts"
    navigate("phase2")


# ============================================================
# PHASE 3
# ============================================================

st.sidebar.markdown(
    "### PHASE 3"
)

if st.sidebar.button(
    "💬 Ask MIKA CI",
    use_container_width=True,
    key="nav_phase3",
):
    navigate("phase3")


# ============================================================
# SYSTEM
# ============================================================

st.sidebar.markdown(
    "### SYSTEM"
)

if st.sidebar.button(
    "📄 Reports",
    use_container_width=True,
    key="nav_reports",
):
    navigate("reports")


if st.sidebar.button(
    "🧩 Schema & Database",
    use_container_width=True,
    key="nav_database",
):
    navigate("database")


# ============================================================
# REFRESH
# ============================================================

st.sidebar.divider()

if st.sidebar.button(
    "🔄 Refresh Data",
    use_container_width=True,
    key="refresh_data",
):

    refresh_database()

    st.session_state.last_refresh += 1
    st.session_state.page = "home"

    st.rerun()


if st.session_state.last_refresh > 0:

    st.sidebar.success(
        "Data refreshed"
    )


# ============================================================
# SIDEBAR DATABASE STATUS
# ============================================================

if database_available():

    st.sidebar.success(
        "● DATABASE CONNECTED"
    )

else:

    st.sidebar.error(
        "● DATABASE NOT FOUND"
    )


st.sidebar.caption(
    f"Database: {DB_PATH.name}"
)

st.sidebar.caption(
    f"Current week: {WEEK}"
)

st.sidebar.caption(
    f"As of: {TODAY}"
)


# ============================================================
# MAIN HEADER
# ============================================================

# Clean Streamlit header.
# No raw HTML.

st.title(
    "MIKA Competitive Intelligence"
)

st.caption(
    "Live market intelligence for MIKA / Ideal Appliances"
)


if LATEST_RUN:

    run_id = LATEST_RUN[0]
    run_week = LATEST_RUN[1]
    status = LATEST_RUN[4]
    findings_created = LATEST_RUN[6]

    if status == "completed":

        st.success(
            f"Latest scan: Run {run_id} — completed | "
            f"{run_week} | {findings_created} findings created"
        )

    else:

        st.warning(
            f"Latest scan: Run {run_id} — {status}"
        )


# ============================================================
# HOME
# ============================================================

if st.session_state.page == "home":

    st.image(
        str(BASE_DIR / "assets" / "mika_logo.png"),
        width=150,
    )

    st.header(
        "MIKA CI Command Center"
    )

    st.caption(
        "Three independent intelligence phases operating "
        "from one dashboard and one SQLite evidence source."
    )

    st.divider()

    st.subheader(
        "Intelligence Phases"
    )

    phase1, phase2, phase3 = st.columns(3)


    # --------------------------------------------------------
    # PHASE 1
    # --------------------------------------------------------

    with phase1:

        st.markdown(
            """
            <div class="mika-card phase1">

                <h3>Phase 1</h3>

                <div class="mika-status-complete">
                    STATUS: COMPLETED
                </div>

                <p>
                    Core market intelligence covering prices,
                    promotions, products, competitor activity,
                    news, sources and reporting.
                </p>

            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open Phase 1",
            key="home_phase1",
            use_container_width=True,
        ):
            navigate("phase1")


    # --------------------------------------------------------
    # PHASE 2
    # --------------------------------------------------------

    with phase2:

        st.markdown(
            """
            <div class="mika-card phase2">

                <h3>Phase 2</h3>

                <div class="mika-status-complete">
                    STATUS: COMPLETED
                </div>

                <p>
                    Campaigns, product intelligence, launches,
                    market trends, competitor comparison,
                    strategic alerts and social evidence.
                </p>

            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open Phase 2",
            key="home_phase2",
            use_container_width=True,
        ):
            navigate("phase2")


    # --------------------------------------------------------
    # PHASE 3
    # --------------------------------------------------------

    with phase3:

        st.markdown(
            """
            <div class="mika-card phase3">

                <h3>Phase 3</h3>

                <div class="mika-status-active">
                    STATUS: ACTIVE
                </div>

                <p>
                    Ask MIKA CI questions and retrieve answers
                    directly from validated SQLite evidence.
                </p>

            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Ask MIKA CI",
            key="home_phase3",
            use_container_width=True,
        ):
            navigate("phase3")


    st.divider()


    # --------------------------------------------------------
    # LIVE INVENTORY
    # --------------------------------------------------------

    st.subheader(
        "Live Intelligence Inventory"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Competitors",
            COMPETITOR_COUNT,
        )

    with c2:
        st.metric(
            "Price Observations",
            PRICE_OBSERVATION_COUNT,
        )

    with c3:
        st.metric(
            "Active Campaigns",
            ACTIVE_CAMPAIGN_COUNT,
        )

    with c4:
        st.metric(
            "Strategic Alerts",
            STRATEGIC_ALERT_COUNT,
        )


    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Social Evidence",
            SOCIAL_OBSERVATION_COUNT,
        )

    with c2:
        st.metric(
            "Market Trends",
            MARKET_TREND_COUNT,
        )

    with c3:
        st.metric(
            "Comparisons",
            COMPARISON_COUNT,
        )

    with c4:
        st.metric(
            "Tracked Catalogue",
            CATALOGUE_PRODUCT_COUNT,
        )


    st.divider()


    # --------------------------------------------------------
    # CURRENT COMPETITIVE ACTIVITY
    # --------------------------------------------------------

    st.subheader(
        "Current Competitive Activity"
    )

    campaign_rows = safe_query(
        """
        SELECT
            competitor_id,
            campaign_name,
            campaign_type,
            category,
            offer_value,
            start_date,
            end_date,
            status,
            confidence
        FROM campaigns
        WHERE
            (
                start_date IS NOT NULL
                AND start_date <= ?
                AND (
                    end_date IS NULL
                    OR end_date >= ?
                )
                AND status != 'ended'
            )
            OR
            (
                start_date > ?
                AND status = 'upcoming'
            )
        ORDER BY
            start_date,
            competitor_id
        """,
        (
            TODAY,
            TODAY,
            TODAY,
        ),
    )

    if campaign_rows:

        st.dataframe(
            [
                {
                    "Campaign": row[1],
                    "Type": row[2],
                    "Category": row[3],
                    "Offer": row[4],
                    "Start": row[5],
                    "End": row[6],
                    "Status": row[7],
                    "Confidence": row[8],
                }
                for row in campaign_rows
            ],
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No active or upcoming campaigns are currently recorded."
        )


# ============================================================
# SOURCES / OSINT
# ============================================================

elif st.session_state.page == "sources":

    st.header(
        "Sources / OSINT"
    )

    st.caption(
        "Open-source intelligence collected from public "
        "competitor, retailer and news sources."
    )

    st.divider()

    source_count = scalar(
        """
        SELECT COUNT(DISTINCT source_url)
        FROM findings
        WHERE source_url IS NOT NULL
          AND TRIM(source_url) <> ''
        """
    )

    source_findings = scalar(
        """
        SELECT COUNT(*)
        FROM findings
        WHERE source_url IS NOT NULL
          AND TRIM(source_url) <> ''
        """
    )

    verified_count = scalar(
        """
        SELECT COUNT(*)
        FROM findings
        WHERE LOWER(
            COALESCE(verification_status, '')
        ) = 'verified'
        """
    )

    high_confidence_count = scalar(
        """
        SELECT COUNT(*)
        FROM findings
        WHERE LOWER(
            COALESCE(confidence, '')
        ) = 'high'
        """
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Unique Sources",
            source_count,
        )

    with c2:
        st.metric(
            "Source Findings",
            source_findings,
        )

    with c3:
        st.metric(
            "Verified Findings",
            verified_count,
        )

    with c4:
        st.metric(
            "High Confidence",
            high_confidence_count,
        )

    st.divider()

    st.subheader(
        "Source Types"
    )

    source_type_rows = safe_query(
        """
        SELECT
            COALESCE(source_type, 'Unknown') AS source_type,
            COUNT(*) AS findings,
            COUNT(DISTINCT source_url) AS sources
        FROM findings
        GROUP BY COALESCE(source_type, 'Unknown')
        ORDER BY findings DESC
        """
    )

    if source_type_rows:

        st.dataframe(
            [
                {
                    "Source Type": row[0],
                    "Findings": row[1],
                    "Unique Sources": row[2],
                }
                for row in source_type_rows
            ],
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No source data available."
        )

    st.divider()

    st.subheader(
        "Source Register"
    )

    source_rows = safe_query(
        """
        SELECT
            COALESCE(
                f.source_type,
                'Unknown'
            ) AS source_type,

            f.source_url,

            COUNT(*) AS findings,

            COUNT(
                DISTINCT f.brand
            ) AS brands,

            MAX(
                f.observed_date
            ) AS latest_observation,

            SUM(
                CASE
                    WHEN LOWER(
                        COALESCE(
                            f.verification_status,
                            ''
                        )
                    ) = 'verified'
                    THEN 1
                    ELSE 0
                END
            ) AS verified_findings,

            SUM(
                CASE
                    WHEN LOWER(
                        COALESCE(
                            f.confidence,
                            ''
                        )
                    ) = 'high'
                    THEN 1
                    ELSE 0
                END
            ) AS high_confidence

        FROM findings f

        WHERE f.source_url IS NOT NULL
          AND TRIM(f.source_url) <> ''

        GROUP BY
            f.source_type,
            f.source_url

        ORDER BY
            findings DESC,
            latest_observation DESC
        """
    )

    if source_rows:

        st.dataframe(
            [
                {
                    "Source Type": row[0],
                    "Source URL": row[1],
                    "Findings": row[2],
                    "Brands": row[3],
                    "Latest Observation": row[4],
                    "Verified": row[5],
                    "High Confidence": row[6],
                }
                for row in source_rows
            ],
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No source URLs are currently stored."
        )

    st.divider()

    st.subheader(
        "Source Detail"
    )

    source_options = [
        "Select a source"
    ]

    for row in source_rows:

        if row[1] and row[1] not in source_options:

            source_options.append(
                row[1]
            )

    selected_source = st.selectbox(
        "Choose a source",
        source_options,
    )

    if selected_source != "Select a source":

        source_detail = safe_query(
            """
            SELECT
                f.finding_id,
                f.brand,
                f.category,
                f.finding_type,
                f.summary,
                f.source_type,
                f.source_url,
                f.published_date,
                f.observed_date,
                f.verification_status,
                f.confidence,
                f.evidence_text
            FROM findings f
            WHERE f.source_url = ?
            ORDER BY
                f.observed_date DESC,
                f.finding_id DESC
            """,
            (selected_source,),
        )

        if source_detail:

            first = source_detail[0]

            st.markdown(
                f"**Source URL:** {selected_source}"
            )

            d1, d2, d3 = st.columns(3)

            with d1:
                st.metric(
                    "Findings",
                    len(source_detail),
                )

            with d2:
                st.metric(
                    "Brands",
                    len(
                        {
                            row[1]
                            for row in source_detail
                            if row[1]
                        }
                    ),
                )

            with d3:

                dates = [
                    row[8]
                    for row in source_detail
                    if row[8]
                ]

                latest_date = (
                    max(dates)
                    if dates
                    else "N/A"
                )

                st.metric(
                    "Latest Observation",
                    latest_date,
                )

            st.write(
                f"**Source type:** {first[5]}"
            )

            st.divider()

            st.subheader(
                "Findings from this source"
            )

            st.dataframe(
                [
                    {
                        "Finding ID": row[0],
                        "Brand": row[1],
                        "Category": row[2],
                        "Type": row[3],
                        "Summary": row[4],
                        "Observed": row[8],
                        "Verification": row[9],
                        "Confidence": row[10],
                    }
                    for row in source_detail
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.divider()

            st.subheader(
                "Evidence"
            )

            for row in source_detail[:10]:

                label = (
                    f"{row[1]} — "
                    f"{row[3]} — "
                    f"{row[8]}"
                )

                with st.expander(label):

                    st.write(
                        row[4]
                    )

                    if row[7]:

                        st.caption(
                            f"Published: {row[7]}"
                        )

                    if row[11]:

                        st.markdown(
                            "**Evidence**"
                        )

                        st.write(
                            row[11]
                        )

                    st.write(
                        f"Verification: {row[9]}"
                    )

                    st.write(
                        f"Confidence: {row[10]}"
                    )

                    if row[6]:

                        st.link_button(
                            "Open Original Source",
                            row[6],
                        )

        else:

            st.info(
                "No findings are associated with this source."
            )


# ============================================================
# PHASE 1
# ============================================================

elif st.session_state.page == "phase1":

    st.header(
        "Phase 1 — Core Market Intelligence"
    )

    st.success(
        "STATUS: COMPLETED"
    )

    st.caption(
        f"Current reporting week: {WEEK}"
    )

    st.divider()

    st.subheader(
        "Phase 1 Overview"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Total Findings",
            TOTAL_FINDINGS,
        )

    with c2:
        st.metric(
            "Prices",
            PRICE_COUNT,
        )

    with c3:
        st.metric(
            "Promotions",
            PROMOTION_COUNT,
        )

    with c4:
        st.metric(
            "News",
            NEWS_COUNT,
        )

    st.divider()

    st.subheader(
        "Competitor Activity"
    )

    activity_rows = safe_query(
        """
        SELECT
            brand,
            finding_type,
            COUNT(*) AS total
        FROM findings
        WHERE scan_week = ?
        GROUP BY
            brand,
            finding_type
        ORDER BY
            total DESC,
            brand
        """,
        (WEEK,),
    )

    if activity_rows:

        st.dataframe(
            [
                {
                    "Brand": row[0],
                    "Signal": row[1],
                    "Findings": row[2],
                }
                for row in activity_rows
            ],
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No current-week findings."
        )

    st.divider()

    st.subheader(
        "Price Intelligence"
    )

    price_rows = safe_query(
        """
        SELECT
            f.brand,
            po.product_name,
            po.model,
            po.price_kes,
            po.promotion_note,
            po.observed_date,
            f.source_url

        FROM findings f

        JOIN price_observations po
            ON po.finding_id = f.finding_id

        WHERE f.scan_week = ?

        ORDER BY
            po.observed_date DESC,
            f.finding_id DESC

        LIMIT 100
        """,
        (WEEK,),
    )

    if price_rows:

        st.dataframe(
            [
                {
                    "Brand": row[0],
                    "Product": row[1],
                    "Model": row[2],
                    "Price (KSh)": row[3],
                    "Promotion Note": row[4],
                    "Observed": row[5],
                    "Source": row[6],
                }
                for row in price_rows
            ],
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No price observations available."
        )

    st.divider()

    st.subheader(
        "Promotion Intelligence"
    )

    promotion_rows = safe_query(
        """
        SELECT
            f.brand,
            po.promotion_type,
            po.offer_value,
            po.start_date,
            po.end_date,
            po.target_segment,
            f.source_url,
            f.observed_date

        FROM findings f

        JOIN promotion_observations po
            ON po.finding_id = f.finding_id

        WHERE f.scan_week = ?

        ORDER BY
            f.observed_date DESC,
            f.finding_id DESC

        LIMIT 100
        """,
        (WEEK,),
    )

    if promotion_rows:

        st.dataframe(
            [
                {
                    "Brand": row[0],
                    "Promotion": row[1],
                    "Offer": row[2],
                    "Start": row[3],
                    "End": row[4],
                    "Target": row[5],
                    "Source": row[6],
                    "Observed": row[7],
                }
                for row in promotion_rows
            ],
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No promotion observations available."
        )

    st.divider()

    st.subheader(
        "News Intelligence"
    )

    news_rows = safe_query(
        """
        SELECT
            f.brand,
            no.headline,
            no.news_type,
            f.summary,
            f.source_url,
            f.published_date

        FROM findings f

        JOIN news_observations no
            ON no.finding_id = f.finding_id

        WHERE f.scan_week = ?

        ORDER BY
            f.published_date DESC
        """,
        (WEEK,),
    )

    if news_rows:

        for row in news_rows:

            st.markdown(
                f"### {row[1]}"
            )

            st.write(
                row[3]
            )

            st.caption(
                f"{row[0]} · {row[2]} · {row[5]}"
            )

            if row[4]:

                st.link_button(
                    "Open source",
                    row[4],
                )

    else:

        st.info(
            "No current-week news findings."
        )


# ============================================================
# PHASE 2
# ============================================================

elif st.session_state.page == "phase2":

    st.header(
        "Phase 2 — Deep Competitive Intelligence"
    )

    st.success(
        "STATUS: COMPLETED"
    )

    st.caption(
        "Phase 2 contains the completed deep competitive "
        "intelligence layers."
    )

    st.divider()

    modules = [
        "Social Intelligence",
        "Campaign Intelligence",
        "Product Intelligence",
        "Product Launches",
        "Market Trends",
        "Competitor Comparison",
        "Strategic Alerts",
    ]

    if st.session_state.phase2_module not in modules:

        st.session_state.phase2_module = (
            "Social Intelligence"
        )

    selected = st.selectbox(
        "Select an intelligence area",
        modules,
        index=modules.index(
            st.session_state.phase2_module
        ),
    )

    st.session_state.phase2_module = selected

    st.divider()


    # ========================================================
    # SOCIAL INTELLIGENCE
    # ========================================================

    if selected == "Social Intelligence":

        st.header(
            "📱 Social Intelligence"
        )

        st.success(
            "MODULE STATUS: ACTIVE"
        )

        st.write(
            "Validated public competitor social evidence "
            "and structured social activity history."
        )

        st.divider()

        verified_social_sources = scalar(
            """
            SELECT COUNT(*)
            FROM social_sources
            WHERE active = 1
              AND verification_status = 'VERIFIED'
              AND source_url IS NOT NULL
              AND TRIM(source_url) <> ''
            """
        )

        total_social_sources = scalar(
            """
            SELECT COUNT(*)
            FROM social_sources
            WHERE active = 1
            """
        )

        social_finding_count = scalar(
            """
            SELECT COUNT(*)
            FROM findings
            WHERE finding_type = 'social'
            """
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Social Observations",
                SOCIAL_OBSERVATION_COUNT,
            )

        with c2:

            st.metric(
                "Social Findings",
                social_finding_count,
            )

        with c3:

            st.metric(
                "Verified Sources",
                verified_social_sources,
            )

        with c4:

            st.metric(
                "Active Sources",
                total_social_sources,
            )

        st.divider()

        st.subheader(
            "Verified Social Source Register"
        )

        source_rows = safe_query(
            """
            SELECT
                competitor_name,
                platform,
                account_name,
                source_url,
                verification_status,
                last_checked,
                verification_source
            FROM social_sources
            WHERE active = 1
            ORDER BY
                competitor_name,
                platform
            """
        )

        if source_rows:

            st.dataframe(
                [
                    {
                        "Competitor": row[0],
                        "Platform": row[1],
                        "Account": row[2],
                        "Source URL": (
                            row[3]
                            or "Not available"
                        ),
                        "Verification": row[4],
                        "Last Checked": (
                            row[5]
                            or "Not checked"
                        ),
                        "Verification Source": (
                            row[6]
                            or "Not recorded"
                        ),
                    }
                    for row in source_rows
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No social sources are registered."
            )

        st.divider()

        st.subheader(
            "Validated Social Observations"
        )

        social_rows = safe_query(
            """
            SELECT
                so.observation_id,
                f.brand,
                so.platform,
                so.account_name,
                so.social_type,
                so.post_text,
                so.post_url,
                so.published_date,
                so.observed_date,
                so.verification_status,
                so.confidence
            FROM social_observations so
            JOIN findings f
                ON f.finding_id = so.finding_id
            ORDER BY
                so.observed_date DESC,
                so.observation_id DESC
            LIMIT 100
            """
        )

        if social_rows:

            st.dataframe(
                [
                    {
                        "ID": row[0],
                        "Brand": row[1],
                        "Platform": row[2],
                        "Account": row[3],
                        "Type": row[4],
                        "Evidence": row[5],
                        "Source": row[6],
                        "Published": row[7],
                        "Observed": row[8],
                        "Verification": row[9],
                        "Confidence": row[10],
                    }
                    for row in social_rows
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No validated social observations have been collected."
            )

        st.divider()

        st.subheader(
            "Social Breakdown"
        )

        platform_rows = safe_query(
            """
            SELECT
                platform,
                COUNT(*) AS observations
            FROM social_observations
            GROUP BY platform
            ORDER BY observations DESC
            """
        )

        type_rows = safe_query(
            """
            SELECT
                social_type,
                COUNT(*) AS observations
            FROM social_observations
            GROUP BY social_type
            ORDER BY observations DESC
            """
        )

        col1, col2 = st.columns(2)

        with col1:

            st.markdown(
                "**By Platform**"
            )

            st.dataframe(
                [
                    {
                        "Platform": row[0],
                        "Observations": row[1],
                    }
                    for row in platform_rows
                ],
                use_container_width=True,
                hide_index=True,
            )

        with col2:

            st.markdown(
                "**By Activity Type**"
            )

            st.dataframe(
                [
                    {
                        "Activity": row[0],
                        "Observations": row[1],
                    }
                    for row in type_rows
                ],
                use_container_width=True,
                hide_index=True,
            )


    # ========================================================
    # CAMPAIGN INTELLIGENCE
    # ========================================================

    elif selected == "Campaign Intelligence":

        st.header(
            "📢 Campaign Intelligence"
        )

        st.success(
            "MODULE STATUS: COMPLETED"
        )

        st.write(
            "Verified competitor campaigns and promotional "
            "activity stored in the campaign evidence layer."
        )

        st.divider()

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Total Campaigns",
                scalar(
                    "SELECT COUNT(*) FROM campaigns"
                ),
            )

        with c2:

            st.metric(
                "Active",
                ACTIVE_CAMPAIGN_COUNT,
            )

        with c3:

            st.metric(
                "Upcoming",
                UPCOMING_CAMPAIGN_COUNT,
            )

        st.divider()

        st.subheader(
            "Active and Upcoming Campaigns"
        )

        rows = safe_query(
            """
            SELECT
                campaign_name,
                campaign_type,
                category,
                offer_value,
                start_date,
                end_date,
                status,
                verification_status,
                confidence,
                source_url,
                evidence_text
            FROM campaigns
            WHERE
                (
                    start_date IS NOT NULL
                    AND start_date <= ?
                    AND (
                        end_date IS NULL
                        OR end_date >= ?
                    )
                    AND status != 'ended'
                )
                OR
                (
                    start_date > ?
                    AND status = 'upcoming'
                )
            ORDER BY
                start_date,
                campaign_name
            """,
            (
                TODAY,
                TODAY,
                TODAY,
            ),
        )

        if rows:

            st.dataframe(
                [
                    {
                        "Campaign": row[0],
                        "Type": row[1],
                        "Category": row[2],
                        "Offer": row[3],
                        "Start": row[4],
                        "End": row[5],
                        "Status": row[6],
                        "Verification": row[7],
                        "Confidence": row[8],
                    }
                    for row in rows
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.divider()

            st.subheader(
                "Campaign Evidence"
            )

            for row in rows:

                with st.expander(
                    f"{row[0]} — {row[6]}"
                ):

                    st.write(
                        row[10]
                        or "No evidence text recorded."
                    )

                    if row[9]:

                        st.link_button(
                            "Open source",
                            row[9],
                        )

        else:

            st.info(
                "No active or upcoming campaigns recorded."
            )


    # ========================================================
    # PRODUCT INTELLIGENCE
    # ========================================================

    elif selected == "Product Intelligence":

        st.header(
            "📦 Product Intelligence"
        )

        st.success(
            "MODULE STATUS: COMPLETED"
        )

        st.write(
            "Observed competitor product pricing and tracked "
            "catalogue evidence."
        )

        st.divider()

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Price Observations",
                PRICE_OBSERVATION_COUNT,
            )

        with c2:

            st.metric(
                "Tracked Catalogue",
                CATALOGUE_PRODUCT_COUNT,
            )

        with c3:

            st.metric(
                "Competitors",
                COMPETITOR_COUNT,
            )

        st.divider()

        st.subheader(
            "Observed Price Coverage"
        )

        price_coverage = safe_query(
            """
            SELECT
                c.competitor_name,
                c.brand_name,
                COUNT(po.observation_id) AS observations,
                COUNT(DISTINCT po.model) AS models,
                MIN(po.observed_date) AS first_observed,
                MAX(po.observed_date) AS last_observed
            FROM price_observations po
            JOIN findings f
                ON f.finding_id = po.finding_id
            JOIN competitors c
                ON c.competitor_id = f.competitor_id
            GROUP BY
                c.competitor_name,
                c.brand_name
            ORDER BY
                observations DESC
            """
        )

        if price_coverage:

            st.dataframe(
                [
                    {
                        "Competitor": row[0],
                        "Brand": row[1],
                        "Observations": row[2],
                        "Models": row[3],
                        "First Observed": row[4],
                        "Last Observed": row[5],
                    }
                    for row in price_coverage
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No price coverage records are available."
            )

        st.divider()

        st.subheader(
            "Latest Price Observations"
        )

        rows = safe_query(
            """
            SELECT
                c.competitor_name,
                c.brand_name,
                po.product_name,
                po.model,
                po.price_kes,
                po.promotion_note,
                po.observed_date
            FROM price_observations po
            JOIN findings f
                ON f.finding_id = po.finding_id
            JOIN competitors c
                ON c.competitor_id = f.competitor_id
            ORDER BY
                po.observed_date DESC,
                po.observation_id DESC
            LIMIT 150
            """
        )

        if rows:

            st.dataframe(
                [
                    {
                        "Competitor": row[0],
                        "Brand": row[1],
                        "Product": row[2],
                        "Model": row[3],
                        "Price (KSh)": row[4],
                        "Promotion": row[5],
                        "Observed": row[6],
                    }
                    for row in rows
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No price observations available."
            )


    # ========================================================
    # PRODUCT LAUNCHES
    # ========================================================

    elif selected == "Product Launches":

        st.header(
            "🚀 Product Launch Intelligence"
        )

        st.success(
            "MODULE STATUS: COMPLETED"
        )

        st.write(
            "Tracked catalogue first-seen evidence used to "
            "identify potential post-baseline product activity."
        )

        st.divider()

        st.info(
            "Launch detection is evidence-based. An ordinary "
            "catalogue listing is not automatically treated as "
            "a product launch."
        )

        catalogue_rows = []

        catalogue_definitions = [
            (
                "Haier",
                "haier_products",
            ),
            (
                "Bruhm",
                "bruhm_products",
            ),
            (
                "K-Elec",
                "k_elec_products",
            ),
        ]

        for brand, table_name in catalogue_definitions:

            try:

                row = query(
                    f"""
                    SELECT
                        COUNT(*) AS products,
                        MIN(first_seen_date),
                        MAX(last_seen_date)
                    FROM "{table_name}"
                    """
                )

                if row:

                    catalogue_rows.append(
                        {
                            "Catalogue": brand,
                            "Tracked Products": row[0][0],
                            "First Seen": row[0][1],
                            "Last Seen": row[0][2],
                        }
                    )

            except Exception:

                continue

        if catalogue_rows:

            st.dataframe(
                catalogue_rows,
                use_container_width=True,
                hide_index=True,
            )

        st.divider()

        st.subheader(
            "Phase 2E Launch Baseline"
        )

        st.markdown(
            """
            **Baseline date:** `2026-09-22`

            The tracked Phase 2E catalogues contain:

            - Haier: 128 tracked catalogue rows
            - Bruhm: 289 tracked catalogue rows
            - K-Elec: 10 tracked catalogue rows
            - Total tracked catalogue rows: 427

            The launch engine distinguishes:

            `BASELINE → FIRST_OBSERVED → LAUNCH_CANDIDATE → CONFIRMED_LAUNCH`

            Current launch evidence is not stored in a dedicated
            SQLite launch table, so this dashboard does not invent
            launch records from ordinary catalogue rows.
            """
        )


    # ========================================================
    # MARKET TRENDS
    # ========================================================

    elif selected == "Market Trends":

        st.header(
            "📈 Market Trends"
        )

        st.success(
            "STATUS: COMPLETED"
        )

        st.write(
            "Persisted market signals derived from validated "
            "price, campaign and catalogue evidence."
        )

        st.divider()

        high_confidence = scalar(
            """
            SELECT COUNT(*)
            FROM market_trends
            WHERE LOWER(
                COALESCE(confidence, '')
            ) = 'high'
            """
        )

        concurrent_signals = scalar(
            """
            SELECT COUNT(*)
            FROM market_trends
            WHERE signal_type =
                'PRICE_CAMPAIGN_CONCURRENCY'
            """
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Persisted Trends",
                MARKET_TREND_COUNT,
            )

        with c2:

            st.metric(
                "High Confidence",
                high_confidence,
            )

        with c3:

            st.metric(
                "Concurrent Signals",
                concurrent_signals,
            )

        st.divider()

        rows = safe_query(
            """
            SELECT
                signal_type,
                status,
                competitor_name,
                category,
                title,
                description,
                start_date,
                end_date,
                evidence_count,
                confidence
            FROM market_trends
            ORDER BY
                start_date DESC,
                trend_id DESC
            """
        )

        if rows:

            st.dataframe(
                [
                    {
                        "Signal": row[0],
                        "Status": row[1],
                        "Competitor": row[2],
                        "Category": row[3],
                        "Title": row[4],
                        "Description": row[5],
                        "Start": row[6],
                        "End": row[7],
                        "Evidence": row[8],
                        "Confidence": row[9],
                    }
                    for row in rows
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No persisted market trends are available."
            )


    # ========================================================
    # COMPETITOR COMPARISON
    # ========================================================

    elif selected == "Competitor Comparison":

        st.header(
            "⚖️ Competitor Comparison"
        )

        st.success(
            "STATUS: COMPLETED"
        )

        st.write(
            "Structured competitor-to-competitor comparison "
            "using documented evidence coverage."
        )

        st.divider()

        st.info(
            "Comparison records show documented evidence coverage. "
            "They are not market-share scores, rankings or overall "
            "competitor ratings."
        )

        competitor_options = [
            row[0]
            for row in safe_query(
                """
                SELECT DISTINCT
                    competitor_name
                FROM competitor_comparisons
                ORDER BY competitor_name
                """
            )
        ]

        selected_competitor = st.selectbox(
            "Filter by competitor",
            [
                "All competitors"
            ]
            + competitor_options,
        )

        if selected_competitor == "All competitors":

            rows = safe_query(
                """
                SELECT
                    competitor_name,
                    brand,
                    dimension,
                    comparison_type,
                    metric_name,
                    metric_value,
                    observation_count,
                    period_start,
                    period_end,
                    evidence_summary,
                    confidence,
                    coverage_status
                FROM competitor_comparisons
                ORDER BY
                    competitor_name,
                    dimension,
                    metric_name
                """
            )

        else:

            rows = safe_query(
                """
                SELECT
                    competitor_name,
                    brand,
                    dimension,
                    comparison_type,
                    metric_name,
                    metric_value,
                    observation_count,
                    period_start,
                    period_end,
                    evidence_summary,
                    confidence,
                    coverage_status
                FROM competitor_comparisons
                WHERE competitor_name = ?
                ORDER BY
                    dimension,
                    metric_name
                """,
                (selected_competitor,),
            )

        st.metric(
            "Comparison Records",
            len(rows),
        )

        if rows:

            st.dataframe(
                [
                    {
                        "Competitor": row[0],
                        "Brand": row[1],
                        "Dimension": row[2],
                        "Type": row[3],
                        "Metric": row[4],
                        "Value": row[5],
                        "Observations": row[6],
                        "Period Start": row[7],
                        "Period End": row[8],
                        "Evidence": row[9],
                        "Confidence": row[10],
                        "Coverage": row[11],
                    }
                    for row in rows
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No comparison evidence matches the selected filter."
            )


    # ========================================================
    # STRATEGIC ALERTS
    # ========================================================

    elif selected == "Strategic Alerts":

        st.header(
            "🚨 Strategic Alerts"
        )

        st.success(
            "STATUS: COMPLETED"
        )

        st.write(
            "Persisted alerts generated from documented "
            "competitive signals."
        )

        st.divider()

        high_alerts = scalar(
            """
            SELECT COUNT(*)
            FROM strategic_alerts
            WHERE status = 'OPEN'
              AND priority = 'HIGH'
            """
        )

        medium_alerts = scalar(
            """
            SELECT COUNT(*)
            FROM strategic_alerts
            WHERE status = 'OPEN'
              AND priority = 'MEDIUM'
            """
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Open Alerts",
                STRATEGIC_ALERT_COUNT,
            )

        with c2:

            st.metric(
                "High",
                high_alerts,
            )

        with c3:

            st.metric(
                "Medium",
                medium_alerts,
            )

        st.divider()

        rows = safe_query(
            """
            SELECT
                alert_type,
                priority,
                competitor_name,
                brand,
                category,
                title,
                description,
                evidence_source,
                evidence_reference,
                evidence_count,
                period_start,
                period_end,
                confidence,
                status,
                created_at
            FROM strategic_alerts
            WHERE status = 'OPEN'
            ORDER BY
                CASE priority
                    WHEN 'HIGH' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'LOW' THEN 3
                    ELSE 4
                END,
                created_at DESC
            """
        )

        if rows:

            st.dataframe(
                [
                    {
                        "Type": row[0],
                        "Priority": row[1],
                        "Competitor": row[2],
                        "Brand": row[3],
                        "Category": row[4],
                        "Title": row[5],
                        "Description": row[6],
                        "Evidence": row[7],
                        "Reference": row[8],
                        "Evidence Count": row[9],
                        "Period Start": row[10],
                        "Period End": row[11],
                        "Confidence": row[12],
                        "Status": row[13],
                        "Created": row[14],
                    }
                    for row in rows
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No open strategic alerts."
            )


# ============================================================
# PHASE 3 — ASK MIKA CI
# ============================================================

elif st.session_state.page == "phase3":

    st.header(
        "Phase 3 — Ask MIKA CI"
    )

    st.success(
        "STATUS: ACTIVE"
    )

    st.caption(
        "Ask questions using the verified MIKA CI evidence "
        "retrieval and answer-composition layer."
    )

    st.divider()

    st.subheader(
        "Ask MIKA CI Anything"
    )

    question = st.text_area(
        "Your question",
        placeholder=(
            "Examples:\n"
            "What campaigns are active?\n"
            "What is happening with JTC?\n"
            "What strategic alerts are open?\n"
            "Show me Hotpoint social activity.\n"
            "What products does Haier have in the tracked catalogue?\n"
            "Compare Hotpoint and Ramtons."
        ),
        height=140,
        key="phase3_question",
    )

    if st.button(
        "Ask MIKA CI",
        type="primary",
        key="phase3_ask",
    ):

        if not question.strip():

            st.warning(
                "Enter a question first."
            )

        else:

            with st.spinner(
                "Retrieving verified MIKA CI evidence..."
            ):

                compose_answer, composer_error = (
                    get_phase3_composer()
                )

                if composer_error:

                    st.error(
                        "The Phase 3 answer engine could not be loaded."
                    )

                    st.code(
                        str(composer_error),
                        language="text",
                    )

                    result = None

                else:

                    try:

                        result = compose_answer(
                            question.strip()
                        )

                    except Exception as exc:

                        st.error(
                            f"MIKA CI could not answer the question: {exc}"
                        )

                        result = None

            if result:

                st.divider()

                st.subheader(
                    "Answer"
                )

                st.write(
                    result.answer
                )

                st.divider()

                st.subheader(
                    "Evidence"
                )

                if result.evidence:

                    for index, evidence in enumerate(
                        result.evidence,
                        start=1,
                    ):

                        with st.expander(
                            f"Evidence {index}"
                        ):

                            if isinstance(
                                evidence,
                                dict,
                            ):

                                for key, value in evidence.items():

                                    st.markdown(
                                        f"**{key}:** {value}"
                                    )

                            else:

                                st.write(
                                    evidence
                                )

                else:

                    st.info(
                        "No supporting evidence was returned."
                    )

                if result.limitations:

                    st.divider()

                    st.subheader(
                        "Limitations"
                    )

                    for limitation in result.limitations:

                        st.markdown(
                            f"- {limitation}"
                        )

                st.divider()

                c1, c2 = st.columns(2)

                with c1:

                    st.caption(
                        f"Intent: {result.intent}"
                    )

                with c2:

                    st.caption(
                        f"Confidence: {result.confidence}"
                    )


# ============================================================
# REPORTS
# ============================================================

elif st.session_state.page == "reports":

    st.header(
        "MIKA CI Reports"
    )

    st.caption(
        "Generated competitive intelligence reports."
    )

    st.divider()

    reports = sorted(
        REPORTS_DIR.glob("MIKA_CI_*.md"),
        reverse=True,
    )

    if reports:

        st.metric(
            "Reports Available",
            len(reports),
        )

        for report in reports:

            with st.expander(
                report.name
            ):

                try:

                    content = report.read_text(
                        encoding="utf-8"
                    )

                    st.code(
                        content,
                        language="markdown",
                    )

                except Exception as exc:

                    st.error(
                        f"Could not read report: {exc}"
                    )

    else:

        st.info(
            "No MIKA CI reports found."
        )


# ============================================================
# SCHEMA & DATABASE
# ============================================================

elif st.session_state.page == "database":

    st.header(
        "🧩 Schema & Database"
    )

    st.caption(
        "Live read-only inspection of the actual MIKA Competitive "
        "Intelligence SQLite project database."
    )

    st.divider()


    # ========================================================
    # DATABASE STATUS
    # ========================================================

    st.subheader(
        "Database Status"
    )

    if not database_available():

        st.error(
            "DATABASE NOT FOUND"
        )

        st.write(
            "SQLite database was not found at:"
        )

        st.code(
            str(DB_PATH),
            language="text",
        )

        st.info(
            "The dashboard expects the actual project database "
            "inside the project's data folder."
        )

    else:

        try:

            database_size = DB_PATH.stat().st_size

            with sqlite3.connect(
                str(DB_PATH)
            ) as db:

                integrity = db.execute(
                    "PRAGMA integrity_check"
                ).fetchone()

                table_rows = db.execute(
                    """
                    SELECT
                        name
                    FROM sqlite_master
                    WHERE type = 'table'
                      AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                ).fetchall()

            integrity_status = (
                integrity[0]
                if integrity
                else "unknown"
            )

            st.success(
                "DATABASE CONNECTED"
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:

                st.metric(
                    "Database",
                    "CONNECTED",
                )

            with c2:

                st.metric(
                    "Tables",
                    len(table_rows),
                )

            with c3:

                if database_size >= 1024 * 1024:

                    size_text = (
                        f"{database_size / (1024 * 1024):.2f} MB"
                    )

                else:

                    size_text = (
                        f"{database_size / 1024:.1f} KB"
                    )

                st.metric(
                    "File Size",
                    size_text,
                )

            with c4:

                st.metric(
                    "Integrity",
                    str(
                        integrity_status
                    ).upper(),
                )

            st.caption(
                "Actual SQLite file"
            )

            st.code(
                str(DB_PATH),
                language="text",
            )

        except Exception as exc:

            st.error(
                f"Database inspection failed: {exc}"
            )


    st.divider()


    # ========================================================
    # ACTUAL SCHEMA OVERVIEW
    # ========================================================

    st.subheader(
        "Actual SQLite Schema"
    )

    st.caption(
        "This section reads the schema directly from "
        "sqlite_master and PRAGMA table_info()."
    )

    if database_available():

        try:

            with sqlite3.connect(
                str(DB_PATH)
            ) as db:

                tables = db.execute(
                    """
                    SELECT
                        name
                    FROM sqlite_master
                    WHERE type = 'table'
                      AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                ).fetchall()

                schema_overview = []

                for table_row in tables:

                    table_name = table_row[0]

                    columns = db.execute(
                        f'PRAGMA table_info("{table_name}")'
                    ).fetchall()

                    row_count = db.execute(
                        f'SELECT COUNT(*) FROM "{table_name}"'
                    ).fetchone()[0]

                    schema_overview.append(
                        {
                            "Table": table_name,
                            "Columns": len(columns),
                            "Records": row_count,
                        }
                    )

            if schema_overview:

                st.dataframe(
                    schema_overview,
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info(
                    "No application tables were found."
                )

        except Exception as exc:

            st.error(
                f"Could not read database schema: {exc}"
            )

    else:

        st.info(
            "Schema will appear here when the SQLite database "
            "is available."
        )


    st.divider()


    # ========================================================
    # TABLE EXPLORER
    # ========================================================

    st.subheader(
        "Table Explorer"
    )

    st.caption(
        "Select any actual SQLite table to inspect its "
        "columns and real stored records."
    )

    if database_available():

        try:

            with sqlite3.connect(
                str(DB_PATH)
            ) as db:

                table_names = [
                    row[0]
                    for row in db.execute(
                        """
                        SELECT
                            name
                        FROM sqlite_master
                        WHERE type = 'table'
                          AND name NOT LIKE 'sqlite_%'
                        ORDER BY name
                        """
                    ).fetchall()
                ]

            if table_names:

                selected_table = st.selectbox(
                    "Select a table",
                    table_names,
                    key="database_table_selector",
                )

                st.markdown(
                    f"### `{selected_table}`"
                )

                with sqlite3.connect(
                    str(DB_PATH)
                ) as db:

                    columns = db.execute(
                        f'PRAGMA table_info("{selected_table}")'
                    ).fetchall()

                    selected_count = db.execute(
                        f'SELECT COUNT(*) FROM "{selected_table}"'
                    ).fetchone()[0]

                st.metric(
                    "Records in selected table",
                    selected_count,
                )

                st.divider()

                st.markdown(
                    "**Table Schema**"
                )

                column_data = []

                for column in columns:

                    column_data.append(
                        {
                            "Column": column[1],
                            "Type": (
                                column[2]
                                or "ANY"
                            ),
                            "Not Null": (
                                "YES"
                                if column[3]
                                else "NO"
                            ),
                            "Primary Key": (
                                "YES"
                                if column[5]
                                else "NO"
                            ),
                            "Default": (
                                column[4]
                                if column[4] is not None
                                else ""
                            ),
                        }
                    )

                if column_data:

                    st.dataframe(
                        column_data,
                        use_container_width=True,
                        hide_index=True,
                    )

                else:

                    st.info(
                        "No columns were returned for this table."
                    )

                st.divider()

                st.markdown(
                    "**Actual Database Records**"
                )

                with sqlite3.connect(
                    str(DB_PATH)
                ) as db:

                    cursor = db.execute(
                        f"""
                        SELECT *
                        FROM "{selected_table}"
                        LIMIT 200
                        """
                    )

                    records = cursor.fetchall()

                    column_names = [
                        description[0]
                        for description in cursor.description
                    ]

                if records:

                    record_data = [
                        dict(
                            zip(
                                column_names,
                                record,
                            )
                        )
                        for record in records
                    ]

                    st.dataframe(
                        record_data,
                        use_container_width=True,
                        hide_index=True,
                    )

                    if selected_count > 200:

                        st.caption(
                            f"Showing the first 200 records "
                            f"of {selected_count}."
                        )

                else:

                    st.info(
                        "This table currently contains no records."
                    )

            else:

                st.info(
                    "No application tables are available."
                )

        except Exception as exc:

            st.error(
                f"Table explorer error: {exc}"
            )

    else:

        st.info(
            "Table Explorer is unavailable because the "
            "SQLite database is not present."
        )


    st.divider()


    # ========================================================
    # DATABASE ARCHITECTURE
    # ========================================================

    st.subheader(
        "Database Architecture"
    )

    st.caption(
        "Generated directly from the actual SQLite database. "
        "No table names are hard-coded here."
    )

    if database_available():

        try:

            with sqlite3.connect(
                str(DB_PATH)
            ) as db:

                actual_tables = [
                    row[0]
                    for row in db.execute(
                        """
                        SELECT
                            name
                        FROM sqlite_master
                        WHERE type = 'table'
                          AND name NOT LIKE 'sqlite_%'
                        ORDER BY name
                        """
                    ).fetchall()
                ]

            if actual_tables:

                architecture_text = (
                    "MIKA Competitive Intelligence\n\n"
                    "SQLite Project Database\n"
                    "│\n"
                )

                for index, table_name in enumerate(
                    actual_tables
                ):

                    is_last = (
                        index
                        == len(actual_tables) - 1
                    )

                    connector = (
                        "└──"
                        if is_last
                        else "├──"
                    )

                    architecture_text += (
                        f"{connector} {table_name}\n"
                    )

                st.code(
                    architecture_text,
                    language="text",
                )

                st.caption(
                    "The architecture above is generated from "
                    "the actual SQLite tables currently present."
                )

            else:

                st.info(
                    "No application tables exist in the database."
                )

        except Exception as exc:

            st.error(
                f"Could not build database architecture: {exc}"
            )

    else:

        st.info(
            "Database architecture will be displayed when "
            "the SQLite database is available."
        )


    st.divider()


    # ========================================================
    # DATABASE SAFETY NOTICE
    # ========================================================

    st.info(
        "The dashboard opens the project SQLite database for "
        "read-only inspection. Schema & Database does not "
        "create, delete, rename or modify database records."
    )
