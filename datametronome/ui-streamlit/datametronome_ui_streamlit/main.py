"""
Main Streamlit application for DataMetronome UI.
"""

import os
from pathlib import Path
import streamlit as st
import httpx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd

# Configuration
BACKEND_URL = os.getenv("DATAMETRONOME_BACKEND_URL", "http://localhost:8000")
APP_TITLE = os.getenv("DATAMETRONOME_UI_TITLE", "DataMetronome")
THEME = os.getenv("DATAMETRONOME_UI_THEME", "light")

# Page configuration
assets_dir = Path(__file__).resolve().parents[1] / "assets"
_page_icon = "🎵"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Branding toggle removed; show branding by default
SHOW_BRANDING = True

def _render_brand_logo(width: int = 320) -> None:
    """Render DataMetronome logo, preferring inline SVG with fallback to PNG."""
    variant = "light"
    svg_path = assets_dir / ("logo_datametronome_" + variant + ".svg")
    if not svg_path.exists():
        svg_path = assets_dir / "logo_datametronome.svg"
    png_path = assets_dir / "logo_datametronome.png"
    try:
        if svg_path.exists():
            svg = svg_path.read_text(encoding="utf-8")
            if "<svg" in svg:
                svg = svg.replace("<svg ", f"<svg style=\"width:{width}px;height:auto;\" ", 1)
            st.markdown(svg, unsafe_allow_html=True)
            return
    except Exception:
        pass
    if png_path.exists():
        st.image(str(png_path), width=width)


def _render_datapulse_badge(width: int = 160) -> None:
    """Render DataPulse secondary logo in the sidebar."""
    variant = "light"
    svg_path = assets_dir / ("logo_datapulse_" + variant + ".svg")
    if not svg_path.exists():
        svg_path = assets_dir / "logo_datapulse.svg"
    png_path = assets_dir / "logo_datapulse.png"
    with st.sidebar:
        st.markdown("---")
        try:
            if svg_path.exists():
                svg = svg_path.read_text(encoding="utf-8")
                if "<svg" in svg:
                    svg = svg.replace("<svg ", f"<svg style=\"width:{width}px;height:auto;\" ", 1)
                st.markdown(svg, unsafe_allow_html=True)
            elif png_path.exists():
                st.image(str(png_path), width=width)
        except Exception:
            pass
        st.caption("Powered by DataPulse")


def _render_footer_badge(width: int = 160) -> None:
    """Render a centered footer badge for DataPulse at the bottom of the page."""
    svg_path = assets_dir / "logo_datapulse.svg"
    png_path = assets_dir / "logo_datapulse.png"
    st.markdown("---")
    try:
        if svg_path.exists():
            svg = svg_path.read_text(encoding="utf-8")
            if "<svg" in svg:
                svg = svg.replace("<svg ", f"<svg style=\"width:{width}px;height:auto;\" ", 1)
            st.markdown(f"<div style='text-align:center'>{svg}<div style='color:#9aa4b2'>Powered by DataPulse</div></div>", unsafe_allow_html=True)
            return
    except Exception:
        pass
    if png_path.exists():
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            st.image(str(png_path), width=width)
            st.caption("Powered by DataPulse")

# Custom CSS for better styling with improved contrast
st.markdown("""
<style>
    /* Fix Streamlit's dark theme contrast issues */
    .stApp {
        background-color: #0e1117 !important;
    }
    
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #58a6ff !important;
        margin-bottom: 2rem;
        text-shadow: 0 0 10px rgba(88, 166, 255, 0.3);
    }
    
    .metric-card {
        background-color: #21262d !important;
        color: #f0f6fc !important;
        padding: 1.5rem;
        border-radius: 0.75rem;
        border-left: 4px solid #58a6ff;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        margin-bottom: 1rem;
    }
    
    .metric-card h3 {
        color: #f0f6fc !important;
        margin-bottom: 0.5rem;
    }
    
    .metric-card p {
        color: #8b949e !important;
        margin: 0;
    }
    
    .success-metric {
        border-left-color: #3fb950 !important;
    }
    
    .warning-metric {
        border-left-color: #d29922 !important;
    }
    
    .danger-metric {
        border-left-color: #f85149 !important;
    }
    
    /* Fix text visibility */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        color: #f0f6fc !important;
    }
    
    .stMarkdown p {
        color: #c9d1d9 !important;
    }
    
    /* Improve button contrast */
    .stButton > button {
        background-color: #238636 !important;
        color: #ffffff !important;
        border: 1px solid #238636 !important;
    }
    
    .stButton > button:hover {
        background-color: #2ea043 !important;
        border: 1px solid #2ea043 !important;
    }
    
    /* Fix metric values */
    .metric-value {
        color: #f0f6fc !important;
        font-weight: bold;
        font-size: 2rem;
    }
    
    /* Fix info boxes */
    .stInfo {
        background-color: #0969da !important;
        color: #ffffff !important;
    }
    
    /* Fix success boxes */
    .stSuccess {
        background-color: #238636 !important;
        color: #ffffff !important;
    }
    
    /* Fix warning boxes */
    .stWarning {
        background-color: #9e6a03 !important;
        color: #ffffff !important;
    }
    
    /* Fix error boxes */
    .stError {
        background-color: #da3633 !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "token" not in st.session_state:
        st.session_state.token = None
    if "username" not in st.session_state:
        st.session_state.username = None


def login_page():
    """Display login page."""
    if SHOW_BRANDING:
        _render_brand_logo(width=320)
    st.markdown('<div class="main-header">🎵 DataMetronome</div>', unsafe_allow_html=True)
    st.markdown("### Welcome to DataMetronome - Your Data Quality Maestro")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        st.markdown("**Login to continue**")
        
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password", value="admin")
        
        if st.button("Login", type="primary", use_container_width=True):
            if authenticate_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid credentials. Try admin/admin")
        
        st.markdown("---")
        st.info("**Demo Credentials:** admin / admin")
        st.markdown("This is a prototype - the backend will create a default user automatically.")


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user with backend.
    
    Args:
        username: Username.
        password: Password.
        
    Returns:
        True if authentication successful.
    """
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{BACKEND_URL}/api/v1/auth/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                st.session_state.token = data["access_token"]
                return True
            return False
    except Exception:
        return False


def get_dashboard_data() -> dict:
    """Get dashboard data from backend.
    
    Returns:
        Dashboard metrics data.
    """
    try:
        with httpx.Client() as client:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            response = client.get(
                f"{BACKEND_URL}/api/v1/metrics/dashboard",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            return {}
    except Exception:
        return {}
    
    # Fallback mock data
    return {
        "total_staves": 3,
        "total_clefs": 8,
        "checks_today": 24,
        "success_rate": 95.8,
        "active_checks": 6,
        "data_quality_score": 92.5,
        "recent_activity": [
            {"type": "check_executed", "message": "Row count check completed", "timestamp": "2025-01-01T12:00:00Z", "status": "success"},
            {"type": "stave_created", "message": "New PostgreSQL connection added", "timestamp": "2025-01-01T11:30:00Z", "status": "info"}
        ],
        "top_issues": [
            "Missing timestamps in 2 tables",
            "Schema drift detected in analytics schema",
            "Data freshness below threshold for 1 table"
        ]
    }


def create_metrics_charts(data: dict):
    """Create metrics visualization charts.
    
    Args:
        data: Dashboard data.
    """
    col1, col2 = st.columns(2)
    
    with col1:
        # Data Quality Score Gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=data.get("data_quality_score", 0),
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Data Quality Score", 'font': {'color': '#f0f6fc', 'size': 18}},
            number={'font': {'color': '#f0f6fc', 'size': 24}},
            delta={'reference': 90, 'font': {'color': '#f0f6fc'}},
            gauge={
                'axis': {'range': [None, 100], 'tickcolor': '#f0f6fc', 'tickfont': {'color': '#f0f6fc'}},
                'bar': {'color': "#58a6ff"},
                'steps': [
                    {'range': [0, 70], 'color': "#6e7681"},
                    {'range': [70, 90], 'color': "#d29922"},
                    {'range': [90, 100], 'color': "#3fb950"}
                ],
                'threshold': {
                    'line': {'color': "#f85149", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig_gauge.update_layout(
            height=300,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': '#f0f6fc'}
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col2:
        # Success Rate Chart
        success_rate = data.get("success_rate", 0)
        fig_pie = px.pie(
            values=[success_rate, 100 - success_rate],
            names=["Success", "Failure"],
            title="Check Success Rate",
            color_discrete_map={"Success": "#3fb950", "Failure": "#f85149"}
        )
        fig_pie.update_layout(
            height=300,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': '#f0f6fc'},
            title={'font': {'color': '#f0f6fc', 'size': 18}}
        )
        st.plotly_chart(fig_pie, use_container_width=True)


def create_activity_timeline(data: dict):
    """Create activity timeline visualization.
    
    Args:
        data: Dashboard data.
    """
    st.subheader("📊 Recent Activity Timeline")
    
    # Create mock timeline data for demonstration
    timeline_data = []
    base_time = datetime.now()
    
    for i, activity in enumerate(data.get("recent_activity", [])):
        time = base_time - timedelta(hours=i)
        timeline_data.append({
            "Time": time.strftime("%H:%M"),
            "Activity": activity.get("message", "Unknown activity"),
            "Type": activity.get("type", "unknown"),
            "Status": activity.get("status", "info")
        })
    
    if timeline_data:
        df = pd.DataFrame(timeline_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent activity to display")


def dashboard_page():
    """Display main dashboard."""
    if SHOW_BRANDING:
        _render_brand_logo(width=220)
    st.markdown('<div class="main-header">🎵 DataMetronome Dashboard</div>', unsafe_allow_html=True)
    
    # Welcome message
    st.markdown(f"### Welcome back, **{st.session_state.username}**! 👋")
    st.markdown("Here's your data quality overview:")
    
    # Get dashboard data
    data = get_dashboard_data()
    
    # Key metrics cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card success-metric">
            <h3>📊 Total Staves</h3>
            <h2>{data.get('total_staves', 0)}</h2>
            <p>Data sources</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card success-metric">
            <h3>🎼 Total Clefs</h3>
            <h2>{data.get('total_clefs', 0)}</h2>
            <p>Rule sets</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card success-metric">
            <h3>✅ Checks Today</h3>
            <h2>{data.get('checks_today', 0)}</h2>
            <p>Executed</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card success-metric">
            <h3>🎯 Success Rate</h3>
            <h2>{data.get('success_rate', 0)}%</h2>
            <p>Overall</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Charts section
    st.subheader("📈 Data Quality Metrics")
    create_metrics_charts(data)
    
    st.markdown("---")
    
    # Activity timeline
    create_activity_timeline(data)
    
    st.markdown("---")
    
    # Call to action
    st.subheader("🚀 Ready to Create Your First Data Pulse?")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        **DataMetronome** helps you monitor data quality across all your data sources. 
        Start by creating your first **Stave** (data source) and then add **Clefs** (rule sets) 
        to monitor data quality automatically.
        """)
    
    with col2:
        if st.button("Create Your First Stave", type="primary", use_container_width=True):
            st.info("This feature will be implemented in the next iteration!")
    
    # Top issues
    if data.get("top_issues"):
        st.markdown("---")
        st.subheader("⚠️ Top Data Quality Issues")
        
        for issue in data["top_issues"]:
            st.markdown(f"• {issue}")


def sidebar():
    """Display sidebar navigation."""
    with st.sidebar:
        st.markdown("## 🎵 DataMetronome")
        st.markdown("---")
        
        if st.session_state.authenticated:
            st.markdown(f"**User:** {st.session_state.username}")
            st.markdown("---")
            
            if st.button("Dashboard", use_container_width=True):
                st.rerun()
            
            if st.button("Manage Staves", use_container_width=True):
                st.info("Stave management coming soon!")
            
            if st.button("Manage Clefs", use_container_width=True):
                st.info("Clef management coming soon!")
            
            if st.button("Check History", use_container_width=True):
                st.info("Check history coming soon!")
            
            st.markdown("---")
            
            if st.button("Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.token = None
                st.session_state.username = None
                st.rerun()
        else:
            st.markdown("Please log in to continue.")


def main():
    """Main application function."""
    init_session_state()
    sidebar()
    
    if not st.session_state.authenticated:
        login_page()
    else:
        dashboard_page()
    if SHOW_BRANDING:
        _render_footer_badge(width=160)


if __name__ == "__main__":
    main()
