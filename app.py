import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from datetime import datetime, timedelta

# 1. Page Configuration & Theme
st.set_page_config(layout="wide", page_title="Hotspot Dashboard - PCD/GISTDA", page_icon="🔥")

st.markdown("""
    <style>
    .main { background-color: #F5F5F5; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #ddd; }
    .stMetric { background-color: #ffffff; border-radius: 10px; padding: 15px; border-top: 5px solid #B00020; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    div.stButton > button:first-child { background-color: #B00020; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. Color Mapping (Based on Screenshots)
COLORS_RESPONSIBILITY = {
    "ป่าอนุรักษ์": "#1B5E20", "ป่าสงวนแห่งชาติ": "#4CAF50", "เขต สปก.": "#FB8C00",
    "พื้นที่เกษตร": "#FBC02D", "ชุมชนและอื่นๆ": "#757575", "พื้นที่ริมทางหลวง": "#795548"
}
COLORS_LANDUSE = {
    "นาข้าว": "#FBC02D", "ข้าวโพดและไร่หมุนเวียน": "#FB8C00", "อ้อย": "#E91E63",
    "พื้นที่ป่า": "#2E7D32", "เกษตรอื่นๆ": "#00BCD4", "อื่น ๆ": "#9E9E9E"
}

# 3. Data Loading (Optimized for 600k rows)
@st.cache_data(ttl=3600)
def load_data():
    sheet_id = "19iGWLP1HFF9NuVxZWNgphNUaBnifyJ4WsYQoZMLtLOE"
    sheet_name = "hotspot2022-2024"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    
    cols = ['LATITUDE', 'LONGITUDE', 'วัน', 'จังหวัด', 'อำเภอ', 'พื้นที่รับผิดชอบ', 'การใช้ที่ดิน']
    dtypes = {'LATITUDE': 'float32', 'LONGITUDE': 'float32', 'จังหวัด': 'category', 'พื้นที่รับผิดชอบ': 'category', 'การใช้ที่ดิน': 'category'}
    
    df = pd.read_csv(url, usecols=cols, dtype=dtypes, low_memory=False)
    df.columns = df.columns.str.strip()
    df['วัน'] = pd.to_datetime(df['วัน'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['วัน'])
    return df

data = load_data()

# 4. Sidebar Navigation (Follow PDF/Screenshots left menu)
with st.sidebar:
    st.image("https://www.gistda.or.th/main/sites/default/files/gistda_logo_2022.png", width=120)
    st.title("Main Menu")
    menu = st.radio("หัวข้อรายงาน", 
                    ["การใช้ที่ดิน (Land Use)", 
                     "พื้นที่รับผิดชอบ (Responsibility)", 
                     "จุดความร้อนสะสม (Accumulated)", 
                     "จุดความร้อนรายวัน (Daily Tracking)"])
    
    st.divider()
    st.header("ตัวกรอง (Filters)")
    
    # Default Date Setup
    max_d = data['วัน'].max().date()
    yesterday = max_d - timedelta(days=1)
    
    date_range = st.date_input("ช่วงเวลา", value=(yesterday, yesterday), 
                               min_value=data['วัน'].min().date(), max_value=max_d)
    
    selected_prov = st.multiselect("เลือกจังหวัด", options=sorted(data['จังหวัด'].unique()))

# Filter Logic
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    mask = (data['วัน'].dt.date >= start) & (data['วัน'].dt.date <= end)
else:
    mask = (data['วัน'].dt.date == date_range[0])

if selected_prov: mask &= data['จังหวัด'].isin(selected_prov)
f_data = data[mask].copy()

# 5. Dashboard Contents
def draw_map(df, color_col, color_map):
    # Convert HEX to RGB for Pydeck
    def hex_to_rgb(hex_str):
        h = hex_str.lstrip('#')
        return [int(h[i:i+2], 16) for i in (0, 2, 4)] + [180]
    
    df['fill_color'] = df[color_col].map(lambda x: hex_to_rgb(color_map.get(x, "#FF0000")))
    
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v10', # Gray/Light Map
        initial_view_state=pdk.ViewState(latitude=13.7, longitude=100.5, zoom=5),
        layers=[pdk.Layer("ScatterplotLayer", df, get_position='[LONGITUDE, LATITUDE]',
                          get_fill_color='fill_color', get_radius=1500, pickable=True)],
        tooltip={"text": "วันที่: {วัน}\nจังหวัด: {จังหวัด}\n{color_col}: {" + color_col + "}"}
    ))

if menu == "การใช้ที่ดิน (Land Use)":
    st.title("📊 สถิติจุดความร้อน: การใช้ที่ดิน")
    c1, c2 = st.columns([4, 6])
    with c1:
        st.metric("จำนวนจุดความร้อน (การใช้ที่ดิน)", f"{len(f_data):,}")
        fig = px.pie(f_data, names='การใช้ที่ดิน', color='การใช้ที่ดิน', color_discrete_map=COLORS_LANDUSE, hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        draw_map(f_data, 'การใช้ที่ดิน', COLORS_LANDUSE)

elif menu == "พื้นที่รับผิดชอบ (Responsibility)":
    st.title("🌳 สถิติจุดความร้อน: พื้นที่รับผิดชอบ")
    c1, c2 = st.columns([4, 6])
    with c1:
        st.metric("จำนวนจุดความร้อน (พื้นที่รับผิดชอบ)", f"{len(f_data):,}")
        fig = px.pie(f_data, names='พื้นที่รับผิดชอบ', color='พื้นที่รับผิดชอบ', color_discrete_map=COLORS_RESPONSIBILITY, hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        draw_map(f_data, 'พื้นที่รับผิดชอบ', COLORS_RESPONSIBILITY)

elif menu == "จุดความร้อนสะสม (Accumulated)":
    st.title("📈 จุดความร้อนสะสม (เปรียบเทียบปี)")
    data['year'] = data['วัน'].dt.year
    yearly = data.groupby('year').size().reset_index(name='จำนวนจุด')
    fig = px.bar(yearly, x='year', y='จำนวนจุด', color='year', title="เปรียบเทียบจุดความร้อนสะสมรายปี")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(yearly, use_container_width=True)

elif menu == "จุดความร้อนรายวัน (Daily Tracking)":
    st.title("🗓️ จุดความร้อนรายวัน (Stack Bar)")
    daily_data = f_data.groupby([f_data['วัน'].dt.date, 'การใช้ที่ดิน'], observed=True).size().reset_index(name='จำนวนจุด')
    daily_data.columns = ['วันที่', 'การใช้ที่ดิน', 'จำนวนจุด']
    
    fig = px.bar(daily_data, x='วันที่', y='จำนวนจุด', color='การใช้ที่ดิน', 
                 color_discrete_map=COLORS_LANDUSE, barmode='stack',
                 title="จำนวนจุดความร้อนรายวันแยกตามการใช้ที่ดิน")
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
