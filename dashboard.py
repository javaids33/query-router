import streamlit as st
import requests
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go

# Configuration
ROUTER_URL = "http://localhost:8000"

st.set_page_config(page_title="Query Router: The Data Garage", page_icon="🏎️", layout="wide")

# Custom CSS for "Premium" feel
st.markdown("""
<style>
    .big-stat { font-size: 3rem; font-weight: bold; color: #4CAF50; }
    .story-card { background-color: #1E1E1E; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 20px; }
    .story-text { font-size: 1.1rem; line-height: 1.6; }
    h1 { background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
</style>
""", unsafe_allow_html=True)

st.title("🏎️ The Smart Data Garage")
st.markdown("### A Story of Modern Data Engineering")

# --- SIDEBAR (Mechanic's Bay) ---
st.sidebar.title("🔧 Mechanic's Bay")
if st.sidebar.button("System Diagnostics"):
    with st.spinner("Checking Engine Status..."):
        try:
            res = requests.get(f"{ROUTER_URL}/health")
            if res.status_code == 200:
                st.sidebar.success("Router Online 🟢")
                # Deep check
                st.sidebar.info("Checking Engines:")
                engines = {
                    "Postgres": "SELECT 1",
                    "ClickHouse": "SELECT 1",
                    "Trino": "SELECT 1", 
                    "DuckDB": "SELECT 1"
                }
                for name, sql in engines.items():
                    try:
                        r = requests.post(f"{ROUTER_URL}/query", json={"sql": sql, "force_engine": name.lower()})
                        if "error" not in r.json():
                            st.sidebar.write(f"✅ {name}")
                        else:
                            st.sidebar.error(f"❌ {name}: {r.json()['error']}")
                    except:
                        st.sidebar.error(f"❌ {name} unreachable")
            else:
                st.sidebar.error(f"Router Error: {res.status_code}")
        except:
            st.sidebar.error("Router Down 🔴")

# --- MAIN STORY ---

tab1, tab2, tab3 = st.tabs(["📖 The Journey (Demo)", "🔬 The Lab (Experiments)", "📊 The Dashboard"])

def run_query(sql, force_engine=None):
    payload = {"sql": sql}
    if force_engine:
        payload["force_engine"] = force_engine
    try:
        response = requests.post(f"{ROUTER_URL}/query", json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

with tab1:
    st.markdown("## Act 1: The Bottleneck 🐢")
    st.markdown("""
    <div class="story-card">
        <p class="story-text">
            Meet <b>Sarah</b>, a Data Engineer. She maintains the company's main PostgreSQL database.
            <br>The Marketing team just launched a huge campaign, and the Analytics dashboard is hitting her database hard.
            <br>Every time they run the <b>"Campaign Performance Report"</b> (a heavy aggregation), the entire app slows down.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.info("👇 Run Sarah's Report (on Postgres)")
        if st.button("Run Report (Slow)", key="act1_btn"):
            with st.spinner("Crunching numbers on Postgres... (simulate load)"):
                sql = "SELECT role, COUNT(*) as count FROM users GROUP BY role"
                res = run_query(sql, force_engine="postgres")
                if "data" in res:
                    st.metric("Execution Time", f"{res.get('duration', 0.0):.4f}s")
                    st.error("Too slow for real-time analytics on big data!")
                    st.dataframe(pd.DataFrame(res["data"]))

    with col2:
        st.markdown("#### The Problem")
        st.markdown("- **Row-based storage** (Postgres) is bad at aggregations.")
        st.markdown("- **Resource Contention**: Analytics queries lock up transactional rows.")
        st.markdown("- **Scaling issues**: Sarah can't just 'add more Postgres'.")

    st.markdown("---")
    
    st.markdown("## Act 2: The Upgrade 🏎️")
    st.markdown("""
    <div class="story-card">
        <p class="story-text">
           Sarah installs the <b>Smart Query Router</b>. 
           <br>Instead of forcing Postgres to do math, the Router automatically detects analytical queries 
           and sends them to <b>ClickHouse</b> (or DuckDB), which reads the <i>exact same data</i> from the Data Lake (MinIO).
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.info("👇 Run Report (via Router)")
        if st.button("Run Smart Report ⚡", key="act2_btn"):
            with st.spinner("Routing..."):
                sql = "SELECT role, COUNT(*) as count FROM users GROUP BY role"
                res = run_query(sql) # Auto-route
                
                engine = res.get("engine", "unknown").upper()
                duration = res.get("duration", 0.0)
                
                st.metric("Execution Time", f"{duration:.4f}s")
                st.success(f"Routed to: {engine}")
                
                if "data" in res:
                     st.dataframe(pd.DataFrame(res["data"]))
                elif "error" in res:
                     st.error(res["error"])

    with col2:
        st.markdown("#### The Solution")
        st.markdown(f"- **Zero Code Change**: The client sends the _exact same SQL_.")
        st.markdown("- **Performance**: Columnar engines are 10-100x faster at this.")
        st.markdown("- **Safety**: Postgres is left alone to handle user logins and orders.")

    st.markdown("---")

    st.markdown("## Act 3: The Ecosystem (Joins & Ad-hoc) 🌍")
    st.markdown("""
    <div class="story-card">
        <p class="story-text">
           The Data Garage isn't just about speed—it's about the <b>Right Tool for the Job</b>.
           <br>• Need to join User data with massive Event logs? Router picks <b>Trino</b>.
           <br>• Just exploring raw data or local files? Router picks <b>DuckDB</b>.
           <br>• One URL (localhost:8000), infinite possibilities.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("#### Try it yourself:")
    q_type = st.radio("I want to...", ["Lookup a specific User (OLTP -> Postgres)", "Analyze User Roles (OLAP -> ClickHouse)", "Join Users & Events (Federated -> Trino)", "Quick Scan/Ad-hoc (Explore -> DuckDB)"])
    
    if st.button("Execute Intent"):
        if "Lookup" in q_type:
            sql = "SELECT * FROM users WHERE id = '1'"
        elif "Analyze" in q_type:
            sql = "SELECT role, COUNT(*) FROM users GROUP BY role"
        elif "Join" in q_type:
            # Join implies Trino
            sql = "SELECT u.name, e.event_date FROM users u JOIN events e ON u.id = e.user_id"
        else:
            # Simple select without ID implies DuckDB/Adhoc
            sql = "SELECT * FROM users LIMIT 5"
            
        with st.spinner("Routing..."):
            res = run_query(sql)
            engine = res.get('engine', 'unknown').upper()
            
            st.metric("Routed To", engine)
            st.code(sql, language="sql")
            
            if "error" in res:
                st.warning(f"Engine Warning: {res['error']} (Expected if tables missing in demo)")
            else:
                st.success("Query executed successfully")
                if "data" in res:
                    st.dataframe(pd.DataFrame(res["data"]))


with tab2:
    st.markdown("### 🔬 The Lab: Stress Testing")
    st.write("Simulating a chaotic real-world workload.")
    
    if st.button("🔥 IGNITE FULL STRESS TEST"):
        progress = st.progress(0)
        results = []
        
        # Mixed workload with randomized parameters to avoid PK collisions
        for i in range(25):
            import random
            choice = random.choice(["oltp", "olap", "write", "join", "adhoc"])
            
            if choice == "oltp":
                q = f"SELECT * FROM users WHERE id = '{random.randint(1,10)}'"
                expected = "postgres"
            elif choice == "olap":
                q = "SELECT role, COUNT(*) FROM users GROUP BY role"
                expected = "clickhouse"
            elif choice == "write":
                # Random ID to prevent duplicate key errors
                rid = random.randint(1000, 100000)
                q = f"INSERT INTO users (id, name, role) VALUES ('{rid}', 'StressBot', 'Robot')"
                expected = "postgres"
            elif choice == "join":
                q = "SELECT u.name FROM users u JOIN events e ON u.id = e.user_id"
                expected = "trino"
            else:
                q = "SELECT * FROM users LIMIT 1"
                expected = "duckdb"

            res = run_query(q)
            
            # Record result
            results.append({
                "id": i,
                "Query Type": choice.upper(),
                "Engine": res.get("engine", "error").upper(),
                "Latency (s)": res.get("duration", 0),
                "Status": "ok" if "error" not in res else "error"
            })
            time.sleep(0.05)
            progress.progress((i+1)/25)
            
        df = pd.DataFrame(results)
        
        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(df)
        with c2:
            fig = px.bar(df, x="id", y="Latency (s)", color="Engine", title="Latency & Engine Distribution")
            st.plotly_chart(fig, use_container_width=True)
            
            # Pie
            fig2 = px.pie(df, names="Engine", title="Workload Distribution")
            st.plotly_chart(fig2, use_container_width=True)


with tab3:
    st.markdown("### 📊 Operational View")
    st.markdown("Real-time view of the Data Garage")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Router Status", "Online")
    c2.metric("Connected Engines", "4")
    c3.metric("Data Lake Protocol", "Iceberg/S3")
    
    st.image("https://mermaid.ink/img/pako:eNp1kU1PwzAMhv9K5HMToT1w4zFpEiYQ0w44cNiNqW-1kS05TtV2Q_x3nLXtABJcnPj1K_tJ54y1JkMTWvF9qZE9-V7yAnle4iXyIi9Xm4IsFiv0tF6hV6tN9nS12eQFrfBqW6A1WpHn-QJ56xV6s94m_Gq1S9C6-9t1jtaoI8_zNfK2K_RutUvQhvvtOkfr1G3kRb5B3naF3q12Cdp0v13naL068jwvkLddoferXYI23W_XOdqgjjzPN8jbrtD71S5Bm-636xztUEee5xvkbVfo_WqXoM3_367zP9r8gTbkef6OvO0KvV_tErT5frvO0eYbeV68I2-7Qu9XuwRtud-uc7RFHXleLJC3XaH3ql2Cttxvt9l7y79o8wN5Xq6Qt12h96tdgrbcb9c52oqM_N-v0PtV_t9b7rfrDK1RR74v3pC_AbVifq8", caption="Architecture")
