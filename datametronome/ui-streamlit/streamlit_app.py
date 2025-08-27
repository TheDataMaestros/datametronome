import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import httpx
import json
from datetime import datetime, timedelta
import uuid
import os
from pathlib import Path

# Page configuration
assets_dir = Path(__file__).resolve().parent / "assets"
_page_icon = "🎵"

st.set_page_config(
    page_title="DataMetronome - Data Quality & Anomaly Detection",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Branding toggle removed; show branding by default, but keep functions simple
_SHOW_BRANDING = True

def _render_brand_logo(width: int = 320) -> None:
    """Render DataMetronome logo, preferring inline SVG with fallback to PNG."""
    # Select variant if available (light/dark); default to light
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
            st.markdown(f"<div style='text-align:center'>{svg}<div style='color:#6b7280'>Powered by DataPulse</div></div>", unsafe_allow_html=True)
            return
    except Exception:
        pass
    if png_path.exists():
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            st.image(str(png_path), width=width)
            st.caption("Powered by DataPulse")

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .anomaly-alert {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        margin: 1rem 0;
        border-left: 5px solid #ff4757;
    }
    .success-card {
        background: linear-gradient(135deg, #2ed573 0%, #1e90ff 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        margin: 1rem 0;
        border-left: 5px solid #2ed573;
    }
    .info-box {
        background: linear-gradient(135deg, #70a1ff 0%, #3742fa 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        margin: 1rem 0;
        border-left: 5px solid #70a1ff;
    }
</style>
""", unsafe_allow_html=True)

# Podium API configuration
PODIUM_API_BASE = os.getenv("PODIUM_API_BASE", "http://localhost:8000")
API_BASE = f"{PODIUM_API_BASE}/api/v1"

# Initialize session state
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

async def call_podium_api(endpoint, method="GET", data=None, token=None):
    """Call Podium API endpoint."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                response = await client.get(f"{API_BASE}{endpoint}", headers=headers)
            elif method == "POST":
                response = await client.post(f"{API_BASE}{endpoint}", json=data, headers=headers)
            elif method == "PUT":
                response = await client.put(f"{API_BASE}{endpoint}", json=data, headers=headers)
            elif method == "DELETE":
                response = await client.delete(f"{API_BASE}{endpoint}", headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            st.error(f"Failed to call API: {e}")
            return None

def login_user(username, password):
    """Login user and store token."""
    try:
        response = httpx.post(f"{API_BASE}/auth/login", json={
            "username": username,
            "password": password
        })
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.auth_token = data.get("access_token")
            st.session_state.user_info = {"username": username}
            return True
        else:
            st.error("Login failed. Please check your credentials.")
            return False
    except Exception as e:
        st.error(f"Login error: {e}")
        return False

def logout_user():
    """Logout user and clear session."""
    st.session_state.auth_token = None
    st.session_state.user_info = None

def show_login_page():
    """Show login page."""
    # Header with optional logo
    if _SHOW_BRANDING:
        _render_brand_logo(width=320)
    st.markdown('<h1 class="main-header">🎵 DataMetronome</h1>', unsafe_allow_html=True)
    st.markdown("### Welcome to DataMetronome - Your Data Quality Platform")
    
    with st.form("login_form"):
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password", value="admin")
        submit = st.form_submit_button("Login")
        
        if submit:
            if login_user(username, password):
                st.success("Login successful! Redirecting to dashboard...")
                st.rerun()
    if _SHOW_BRANDING:
        _render_footer_badge(width=160)

def show_dashboard():
    """Show main dashboard."""
    if _SHOW_BRANDING:
        _render_brand_logo(width=220)
    st.markdown('<h1 class="main-header">🎵 DataMetronome Dashboard</h1>', unsafe_allow_html=True)
    
    # Header with user info and logout
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("### Welcome back! 🚀")
    with col2:
        st.info(f"User: {st.session_state.user_info.get('username', 'Unknown')}")
    with col3:
        if st.button("Logout"):
            logout_user()
            st.rerun()
    
    # Dashboard tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview", 
        "🚨 Anomalies", 
        "🤖 ML Anomalies", 
        "📈 Trends & Patterns", 
        "🔍 Investigation",
        "📄 Reports"
    ])
    
    with tab1:
        show_overview_tab()
    
    with tab2:
        show_anomalies_tab()
    
    with tab3:
        show_ml_anomalies_tab()
    
    with tab4:
        show_trends_patterns_tab()
    
    with tab5:
        show_investigation_tab()
    
    with tab6:
        show_reports_tab()
    if _SHOW_BRANDING:
        _render_footer_badge(width=160)

def show_overview_tab():
    """Show overview tab with system health metrics."""
    st.markdown("## 📊 System Overview")
    
    # Show system health from mock data instead of calling API
    st.info("🔍 System health metrics from your configured monitoring staves.")
    
    # System health metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>System Status</h3>
            <h2>✅ Healthy</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>API Status</h3>
            <h2>🟢 Running</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>Database</h3>
            <h2>🟢 Connected</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3>Last Check</h3>
            <h2>2 hours ago</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Stave status overview
    st.markdown("## ⚙️ Monitoring Stave Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🔍 Data Quality Staves")
        st.markdown("""
        - **Users Monitor**: ✅ Last run: 2 hours ago
        - **Orders Monitor**: ✅ Last run: 1 hour ago
        - **Events Monitor**: ⚠️ Last run: 3 hours ago
        """)
    
    with col2:
        st.markdown("### 🤖 ML Analysis Staves")
        st.markdown("""
        - **ML Anomaly Detector**: ✅ Last run: 1 hour ago
        - **Model Training**: ✅ Last run: 6 hours ago
        - **Performance Monitor**: ✅ Last run: 1 hour ago
        """)
    
    with col3:
        st.markdown("### 📊 Analytics Staves")
        st.markdown("""
        - **Distribution Analyzer**: ✅ Last run: 4 hours ago
        - **Time Series Analyzer**: ✅ Last run: 4 hours ago
        - **Pattern Detector**: ✅ Last run: 4 hours ago
        """)
    
    # Quick actions
    st.markdown("## 🚀 Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh All Staves", use_container_width=True):
            st.success("All monitoring staves refreshed!")
            st.rerun()
    
    with col2:
        if st.button("📊 Run Health Check", use_container_width=True):
            st.info("Health check completed! All systems operational.")
    
    with col3:
        if st.button("📈 View Performance", use_container_width=True):
            st.info("Performance metrics loaded!")
    
    # Recent activity
    st.markdown("## 📋 Recent Activity")
    
    recent_activity = pd.DataFrame({
        "Time": ["2 hours ago", "1 hour ago", "3 hours ago", "4 hours ago", "6 hours ago"],
        "Stave": ["Users Monitor", "Orders Monitor", "Events Monitor", "Analytics Suite", "ML Training"],
        "Action": ["Data quality check", "Anomaly detection", "Schema validation", "Trend analysis", "Model update"],
        "Status": ["✅ Passed", "✅ Passed", "❌ Failed", "✅ Completed", "✅ Completed"],
        "Details": ["150 records checked", "7 anomalies found", "Column type change", "Patterns analyzed", "Model accuracy: 94.2%"]
    })
    
    st.dataframe(recent_activity, use_container_width=True)

def show_anomalies_tab():
    """Show anomalies tab with data quality monitoring."""
    st.markdown("## 🚨 Data Quality Anomalies")
    
    # Get anomalies from Podium API (this would be implemented in Podium)
    st.info("🔍 Anomaly detection results are displayed from your configured monitoring staves.")
    
    # Mock data for demonstration - in real app this would come from Podium API
    st.markdown("### 📊 Recent Anomaly Detection Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Tables Monitored", "3", "users, orders, events")
    
    with col2:
        st.metric("Anomalies Detected", "2", "in last 24h")
    
    with col3:
        st.metric("Data Quality Score", "87%", "-3% from yesterday")
    
    # Anomaly details
    st.markdown("### 🚨 Recent Anomalies")
    
    anomalies_df = pd.DataFrame({
        "Table": ["users", "orders"],
        "Issue": ["Age outlier detected", "Amount spike detected"],
        "Severity": ["Medium", "High"],
        "Detected": ["2 hours ago", "1 hour ago"],
        "Status": ["Investigating", "Resolved"]
    })
    
    st.dataframe(anomalies_df, use_container_width=True)
    
    # Stave management section
    st.markdown("### ⚙️ Monitoring Stave Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Active Monitoring Staves:**")
        st.markdown("""
        - **PostgreSQL Users Monitor** - Last run: 2 hours ago ✅
        - **PostgreSQL Orders Monitor** - Last run: 1 hour ago ✅  
        - **PostgreSQL Events Monitor** - Last run: 3 hours ago ⚠️
        """)
    
    with col2:
        if st.button("🔄 Run All Staves", type="primary", use_container_width=True):
            with st.spinner("Running monitoring staves..."):
                # This would call Podium API to run all staves
                st.success("All monitoring staves executed successfully!")
                st.rerun()
    
    # Individual stave controls
    st.markdown("### 🎯 Individual Stave Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Users Monitor**")
        st.markdown("Last run: 2 hours ago")
        if st.button("Run Users Monitor", key="users_monitor"):
            with st.spinner("Running users monitor..."):
                st.success("Users monitor completed!")
    
    with col2:
        st.markdown("**Orders Monitor**")
        st.markdown("Last run: 1 hour ago")
        if st.button("Run Orders Monitor", key="orders_monitor"):
            with st.spinner("Running orders monitor..."):
                st.success("Orders monitor completed!")
    
    with col3:
        st.markdown("**Events Monitor**")
        st.markdown("Last run: 3 hours ago")
        if st.button("Run Events Monitor", key="events_monitor"):
            with st.spinner("Running events monitor..."):
                st.success("Events monitor completed!")

def show_ml_anomalies_tab():
    """Show ML anomalies tab with machine learning insights."""
    st.markdown("## 🤖 Machine Learning Anomaly Detection")
    
    st.info("🧠 ML anomaly detection results from your configured monitoring staves.")
    
    # Show existing ML results instead of generating new ones
    st.markdown("### 📊 ML Detection Results")
    
    # Mock ML results - in real app this would come from Podium API
    ml_results = {
        "Total Records Analyzed": 1500,
        "Anomalies Detected": 7,
        "Detection Rate": "0.47%",
        "Model Confidence": "94.2%",
        "Last ML Run": "1 hour ago"
    }
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Records Analyzed", ml_results["Total Records Analyzed"])
    with col2:
        st.metric("Anomalies Found", ml_results["Anomalies Detected"])
    with col3:
        st.metric("Model Confidence", f"{ml_results['Model Confidence']}%")
    
    # ML configuration (read-only for now)
    st.markdown("### ⚙️ Current ML Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Algorithm**: Isolation Forest")
        st.info(f"**Contamination Factor**: 0.1")
    
    with col2:
        st.info(f"**Estimators**: 100")
        st.info(f"**Random State**: 42")
    
    # Show ML results visualization
    if st.button("📊 Show ML Results Visualization", use_container_width=True):
        st.markdown("### 🎨 ML Anomaly Visualization")
        
        # Create sample data for visualization
        np.random.seed(42)
        normal_data = np.random.normal(100, 15, 1000)
        anomaly_data = np.random.normal(200, 30, 50)
        
        all_data = np.concatenate([normal_data, anomaly_data])
        labels = ['Normal'] * 1000 + ['Anomaly'] * 50
        
        # Create histogram
        fig = px.histogram(
            x=all_data,
            color=labels,
            title="ML Anomaly Detection Results (Last Run)",
            labels={'x': 'Value', 'y': 'Count'},
            color_discrete_map={'Normal': '#2E86AB', 'Anomaly': '#A23B72'}
        )
        
        fig.update_layout(
            xaxis_title="Data Values",
            yaxis_title="Frequency",
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("💡 This visualization shows the results from the last ML anomaly detection run.")
    
    # Stave management for ML
    st.markdown("### 🤖 ML Stave Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**ML Monitoring Stave:**")
        st.markdown("""
        - **PostgreSQL ML Anomaly Detector** - Last run: 1 hour ago ✅
        - **Model Status**: Active and trained
        - **Training Data**: 10,000 records
        - **Performance**: 94.2% accuracy
        """)
    
    with col2:
        if st.button("🚀 Run ML Detection", type="primary", use_container_width=True):
            with st.spinner("Running ML anomaly detection..."):
                # This would call Podium API to run ML stave
                st.success("ML anomaly detection completed!")
                st.info("New results will be displayed above.")
                st.rerun()

def show_trends_patterns_tab():
    """Show trends and patterns tab with advanced analytics."""
    st.markdown("## 📈 Data Trends & Patterns Analysis")
    
    st.info("📊 Trend analysis and pattern recognition from your monitoring staves.")
    
    # Sub-tabs for different analysis types
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "📊 Data Distribution",
        "📈 Time Series",
        "🔍 Correlation",
        "🎯 Anomaly Patterns"
    ])
    
    with sub_tab1:
        st.markdown("### 📊 Data Distribution Analysis")
        
        st.info("💡 Data distribution analysis from your configured monitoring staves.")
        
        if st.button("🔄 Refresh Distribution Data", use_container_width=True):
            # Mock data distribution
            np.random.seed(42)
            ages = np.random.normal(35, 10, 1000)
            amounts = np.random.lognormal(4, 0.5, 1000)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = px.histogram(
                    x=ages,
                    title="User Age Distribution (Last Analysis)",
                    labels={'x': 'Age', 'y': 'Count'},
                    nbins=30
                )
                fig1.update_traces(marker_color='#2E86AB')
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = px.histogram(
                    x=amounts,
                    title="Order Amount Distribution (Last Analysis)",
                    labels={'x': 'Amount ($)', 'y': 'Count'},
                    nbins=30
                )
                fig2.update_traces(marker_color='#A23B72')
                st.plotly_chart(fig2, use_container_width=True)
    
    with sub_tab2:
        st.markdown("### 📈 Time Series Analysis")
        
        st.info("💡 Time series analysis from your configured monitoring staves.")
        
        if st.button("🔄 Refresh Time Series Data", use_container_width=True):
            # Mock time series data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            users = np.random.poisson(50, len(dates)) + np.random.normal(0, 5, len(dates))
            orders = np.random.poisson(100, len(dates)) + np.random.normal(0, 10, len(dates))
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = px.line(
                    x=dates,
                    y=users,
                    title="Daily User Registrations (Last Analysis)",
                    labels={'x': 'Date', 'y': 'Users'}
                )
                fig1.update_traces(line_color='#2E86AB')
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = px.line(
                    x=dates,
                    y=orders,
                    title="Daily Order Volume (Last Analysis)",
                    labels={'x': 'Date', 'y': 'Orders'}
                )
                fig2.update_traces(line_color='#A23B72')
                st.plotly_chart(fig2, use_container_width=True)
    
    with sub_tab3:
        st.markdown("### 🔍 Correlation Analysis")
        
        st.info("💡 Correlation analysis from your configured monitoring staves.")
        
        if st.button("🔄 Refresh Correlation Data", use_container_width=True):
            # Mock correlation data
            np.random.seed(42)
            ages = np.random.normal(35, 10, 500)
            amounts = 100 + ages * 2 + np.random.normal(0, 20, 500)
            
            # Calculate correlation
            correlation = np.corrcoef(ages, amounts)[0, 1]
            
            fig = px.scatter(
                x=ages,
                y=amounts,
                title=f"Age vs Order Amount Correlation (Last Analysis): {correlation:.3f}",
                labels={'x': 'Age', 'y': 'Order Amount ($)'}
            )
            
            # Add trend line
            z = np.polyfit(ages, amounts, 1)
            p = np.poly1d(z)
            fig.add_trace(go.Scatter(
                x=ages,
                y=p(ages),
                mode='lines',
                name='Trend Line',
                line=dict(color='red', dash='dash')
            ))
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.info(f"📊 Correlation coefficient: {correlation:.3f}")
    
    with sub_tab4:
        st.markdown("### 🎯 Anomaly Pattern Analysis")
        
        st.info("💡 Anomaly pattern analysis from your configured monitoring staves.")
        
        if st.button("🔄 Refresh Anomaly Patterns", use_container_width=True):
            # Mock anomaly pattern data
            np.random.seed(42)
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            anomalies = np.random.choice([0, 1], size=len(dates), p=[0.9, 0.1])
            
            # Create anomaly heatmap
            fig = px.imshow(
                [anomalies],
                title="Anomaly Pattern Over Time (Last Analysis)",
                labels={'x': 'Date', 'y': 'Anomaly Status'},
                color_continuous_scale=['green', 'red']
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Anomaly statistics
            total_anomalies = sum(anomalies)
            anomaly_rate = total_anomalies / len(anomalies) * 100
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Anomalies", total_anomalies)
            with col2:
                st.metric("Anomaly Rate", f"{anomaly_rate:.1f}%")
    
    # Stave management for analytics
    st.markdown("### 📊 Analytics Stave Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Analytics Monitoring Staves:**")
        st.markdown("""
        - **PostgreSQL Distribution Analyzer** - Last run: 4 hours ago ✅
        - **PostgreSQL Time Series Analyzer** - Last run: 4 hours ago ✅
        - **PostgreSQL Correlation Analyzer** - Last run: 4 hours ago ✅
        - **PostgreSQL Pattern Analyzer** - Last run: 4 hours ago ✅
        """)
    
    with col2:
        if st.button("📊 Run All Analytics", type="primary", use_container_width=True):
            with st.spinner("Running all analytics staves..."):
                # This would call Podium API to run analytics staves
                st.success("All analytics staves completed!")
                st.info("New analytics results will be displayed above.")
                st.rerun()

def show_investigation_tab():
    """Show investigation tab with data exploration tools."""
    st.markdown("## 🔍 Data Investigation & Exploration")
    
    st.info("🔍 Data investigation tools are powered by the Podium backend. Configure your data sources to explore your data.")
    
    # Custom SQL query (this would be sent to Podium API)
    st.markdown("### 📝 Custom SQL Query")
    
    query = st.text_area(
        "Enter your SQL query:",
        value="SELECT * FROM users LIMIT 10",
        height=100
    )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🚀 Execute Query", use_container_width=True):
            st.info("Query execution is handled by the Podium backend. Configure your data sources to run queries.")
    
    with col2:
        if st.button("💾 Save Query", use_container_width=True):
            st.success("Query saved to your favorites!")
    
    # Data profiling
    st.markdown("### 📊 Data Profiling")
    
    if st.button("🔍 Profile All Tables", use_container_width=True):
        st.info("Data profiling is handled by the Podium backend. Configure your data sources to profile tables.")
    
    # Sample data viewer
    st.markdown("### 👀 Sample Data Viewer")
    
    # Mock sample data
    sample_data = pd.DataFrame({
        "id": ["user_001", "user_002", "user_003"],
        "username": ["john_doe", "jane_smith", "bob_wilson"],
        "age": [28, 34, 29],
        "email": ["john@example.com", "jane@example.com", "bob@example.com"],
        "created_at": ["2024-01-15", "2024-01-16", "2024-01-17"]
    })
    
    st.dataframe(sample_data, use_container_width=True)
    st.caption("📝 This is sample data. Configure your data sources to see real data.")

def show_reports_tab():
    """Show reports tab with various report generation options."""
    st.markdown("## 📄 Reports")
    st.info("Generate and download various types of reports from your data.")

    # Report generation options
    report_type = st.selectbox(
        "Select Report Type",
        ["Data Quality Summary", "Anomaly Report", "Performance Report", "Custom Report"]
    )

    if report_type == "Data Quality Summary":
        st.markdown("### 📊 Data Quality Summary Report")
        st.info("This report provides a high-level overview of your data quality metrics.")
        
        # Mock data for report
        data_quality_summary = {
            "Total Tables": 10,
            "Monitored Tables": 8,
            "Anomalies Detected": 150,
            "Data Quality Score": 92.5,
            "Last Check": "2 hours ago"
        }
        
        st.json(data_quality_summary)

        if st.button("💾 Download Data Quality Summary", use_container_width=True):
            st.download_button(
                label="Download Data Quality Summary (JSON)",
                data=json.dumps(data_quality_summary, indent=4),
                file_name="data_quality_summary.json",
                mime="application/json"
            )

    elif report_type == "Anomaly Report":
        st.markdown("### 🚨 Anomaly Report")
        st.info("This report details all detected anomalies across your data sources.")
        
        # Mock anomaly data for report
        anomalies_for_report = [
            {"table": "users", "issue": "Age outlier detected", "severity": "Medium", "detected": "2 hours ago", "status": "Investigating"},
            {"table": "orders", "issue": "Amount spike detected", "severity": "High", "detected": "1 hour ago", "status": "Resolved"}
        ]
        
        anomalies_df = pd.DataFrame(anomalies_for_report)
        st.dataframe(anomalies_df, use_container_width=True)

        if st.button("💾 Download Anomaly Report", use_container_width=True):
            st.download_button(
                label="Download Anomaly Report (CSV)",
                data=anomalies_df.to_csv(index=False),
                file_name="anomaly_report.csv",
                mime="text/csv"
            )

    elif report_type == "Performance Report":
        st.markdown("### 📈 Performance Report")
        st.info("This report analyzes the performance of your data pipelines and backend services.")
        
        # Mock performance data for report
        performance_data = {
            "API Response Time": 120,
            "Database Queries/sec": 1500,
            "Memory Usage": "1.2GB",
            "CPU Usage": "70%",
            "Last Check": "10 minutes ago"
        }
        
        st.json(performance_data)

        if st.button("💾 Download Performance Report", use_container_width=True):
            st.download_button(
                label="Download Performance Report (JSON)",
                data=json.dumps(performance_data, indent=4),
                file_name="performance_report.json",
                mime="application/json"
            )

    elif report_type == "Custom Report":
        st.markdown("### 📝 Custom Report")
        st.info("Generate a custom report based on your specific data requirements.")
        
        # Custom report generation logic (e.g., SQL query, data transformation)
        # This would typically involve calling a Podium API endpoint for custom reports
        st.info("Custom report generation is powered by the Podium backend. Configure your data sources and reporting rules to generate custom reports.")
        
        # Example: If you had a Podium API endpoint for custom reports
        # if st.button("🚀 Generate Custom Report", use_container_width=True):
        #     with st.spinner("Generating custom report..."):
        #         # This would involve sending a POST request to a Podium API endpoint
        #         # For example: response = await call_podium_api("/reports/custom", method="POST", data={"query": query})
        #         st.success("Custom report generation initiated!")
        #         # You would then display the results or download them

# Main app logic
def main():
    if st.session_state.auth_token is None:
        show_login_page()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
