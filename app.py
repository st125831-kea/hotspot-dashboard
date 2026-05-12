import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from datetime import datetime, timedelta

# 1. การตั้งค่าหน้าจอและธีม (Bright Theme + PCD/GISTDA Red)
st.set_page_config(
    layout="wide", 
    page_title="Thailand Hotspot Reporting System",
    page_icon="🔥"
)

# Custom CSS เพื่อปรับสีสันให้เหมือน PDF (โทนขาว-เทา-แดงเข้ม)
st.markdown("""
    <style>
    /* พื้นหลังและฟอนต์ */
    .main { background-color: #FFFFFF; }
    h1, h2, h3 { color: #1A1A1A; font-weight: 700; }
    
    /* สไตล์ Metric Card */
    div[data-testid="stMetric"] {
        background-color: #F8F9FA;
        border-left: 5px solid #B00020;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* ปรับแต่ง Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #F1F3F5;
        border-radius: 5px 5px 0 0;
        padding: 10px 25px;
        color: #495057;
    }
    .stTabs [aria-selected="true"] {
        background-color: #B00020 !important;
        color: white !important;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. ฟังก์ชันโหลดข้อมูล (จำกัดคอลัมน์และประเภทข้อมูลเพื่อประหยัด RAM)
@st.cache_data(ttl=3600)
def load_data():
    sheet_id = "19iGWLP1HFF9NuVxZWNgphNUaBnifyJ4WsYQoZMLtLOE"
    sheet_name = "hotspot2022-2024"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    
    # เลือกเฉพาะคอลัมน์ที่ต้องใช้
    cols = ['LATITUDE', 'LONGITUDE', 'วัน', 'จังหวัด', 'อำเภอ', 'การใช้ที่ดิน']
    # กำหนด Type เพื่อลดการใช้ Memory
    dtypes = {
        'LATITUDE': 'float32', 'LONGITUDE': 'float32',
        'จังหวัด': 'category', 'การใช้ที่ดิน': 'category'
    }
    
    df = pd.read_csv(url, usecols=cols, dtype=dtypes, low_memory=False)
    df.columns = df.columns.str.strip()
    
    # แปลงวันที่
    df['วัน'] = pd.to_datetime(df['วัน'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['วัน'])
    return df

# โหลดข้อมูล
try:
    data = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# 3. Sidebar (Default = เมื่อวานนี้)
with st.sidebar:
    st.image("https://www.gistda.or.th/main/sites/default/files/gistda_logo_2022.png", width=120)
    st.header("ตัวเลือกการกรอง")
    
    # ตั้งค่าวันที่เมื่อวานเป็น Default
    last_date = data['วัน'].max().date()
    yesterday = last_date - timedelta(days=1)
    
    date_range = st.date_input(
        "เลือกช่วงเวลา (Default: เมื่อวาน)",
        value=(yesterday, yesterday),
        min_value=data['วัน'].min().date(),
        max_value=last_date
    )
    
    prov_filter = st.multiselect("เลือกจังหวัด", options=sorted(data['จังหวัด'].unique()))
    land_filter = st.multiselect("ประเภทการใช้ที่ดิน", options=sorted(data['การใช้ที่ดิน'].unique()))

# กรองข้อมูล
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    mask = (data['วัน'].dt.date >= start) & (data['วัน'].dt.date <= end)
else:
    mask = (data['วัน'].dt.date == date_range[0])

if prov_filter: mask &= data['จังหวัด'].isin(prov_filter)
if land_filter: mask &= data['การใช้ที่ดิน'].isin(land_filter)

f_data = data[mask]

# 4. การกำหนดสี (Color Palette ตามไฟล์ PDF)
# กำหนดสีเฉพาะให้แต่ละประเภทที่ดินเพื่อให้เหมือนต้นฉบับ
color_map = {
    "ป่าอนุรักษ์": "#1B5E20",      # เขียวเข้ม
    "ป่าสงวนแห่งชาติ": "#4CAF50",  # เขียวสว่าง
    "พื้นที่เกษตร": "#FBC02D",     # เหลืองทอง
    "เขต ส.ป.ก.": "#FB8C00",      # ส้ม
    "ชุมชนและอื่นๆ": "#757575"      # เทา
}

# 5. การแสดงผลเนื้อหาหลัก
st.title("🔥 Thailand Hotspot Situation Report")
st.info(f"แสดงข้อมูลระหว่างวันที่: {date_range[0]} ถึง {date_range[1]} | พบทั้งหมด {len(f_data):,} จุด")

tab1, tab2, tab3 = st.tabs(["📊 สรุปสถิติหลัก", "📍 แผนที่ความร้อน", "📋 ตารางข้อมูล"])

# --- TAB 1: สถิติและกราฟ ---
with tab1:
    col_a, col_b = st.columns([6, 4])
    
    with col_a:
        st.subheader("จำนวนจุดความร้อนแยกตามประเภทที่ดิน")
        # กราฟแท่งแนวนอน (Horizontal Bar Chart) สีแดงเข้มแบบไล่เฉด
        land_counts = f_data['การใช้ที่ดิน'].value_counts().reset_index()
        land_counts.columns = ['ประเภทที่ดิน', 'จำนวนจุด']
        
        fig_bar = px.bar(land_counts, x='จำนวนจุด', y='ประเภทที่ดิน', orientation='h',
                         color='จำนวนจุด', color_continuous_scale=['#FFCDD2', '#B00020'])
        fig_bar.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_b:
        st.subheader("สัดส่วนพื้นที่ (Donut Chart)")
        fig_pie = px.pie(f_data, names='การใช้ที่ดิน', hole=0.5,
                         color='การใช้ที่ดิน', color_discrete_map=color_map)
        fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()
    st.subheader("10 จังหวัดที่พบจุดความร้อนสูงสุด")
    top_prov = f_data['จังหวัด'].value_counts().head(10).reset_index()
    top_prov.columns = ['จังหวัด', 'จำนวนจุด']
    fig_top = px.bar(top_prov, x='จังหวัด', y='จำนวนจุด', text='จำนวนจุด')
    fig_top.update_traces(marker_color='#B00020', textposition='outside')
    st.plotly_chart(fig_top, use_container_width=True)

# --- TAB 2: แผนที่ (Maps) ---
with tab2:
    st.subheader("ตำแหน่งจุดความร้อนรายพิกัด (VIIRS)")
    # แผนที่ใช้จุดสีแดงสว่างเพื่อให้ตัดกับพื้นหลัง
    view_state = pdk.ViewState(latitude=15.0, longitude=100.5, zoom=5)
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        f_data,
        get_position='[LONGITUDE, LATITUDE]',
        get_color='[176, 0, 32, 180]', # สีแดงเข้ม (B00020) แบบโปร่งแสง
        get_radius=1200,
        pickable=True,
    )
    
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v10', # แผนที่โทนสว่าง
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "วันที่: {วัน}\nจังหวัด: {จังหวัด}\nประเภท: {การใช้ที่ดิน}"}
    ))

# --- TAB 3: ข้อมูลดิบ ---
with tab3:
    st.subheader("รายการข้อมูลจุดความร้อนล่าสุด")
    st.dataframe(f_data, use_container_width=True, height=500)
