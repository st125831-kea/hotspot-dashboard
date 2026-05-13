import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from datetime import datetime, timedelta

# 1. การตั้งค่าหน้าจอและ Theme
st.set_page_config(
    layout="wide", 
    page_title="ระบบรายงานจุดความร้อนประเทศไทย (PCD/GISTDA)",
    page_icon="🔥"
)

# Custom CSS เพื่อให้ UI เหมือน Dashboard มืออาชีพ (Theme สว่าง)
st.markdown("""
    <style>
    .main { background-color: #F9F9F9; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E0E0E0; }
    .stMetric { background-color: #FFFFFF; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-top: 4px solid #B00020; }
    h1, h2, h3 { color: #202124; }
    </style>
    """, unsafe_allow_html=True)

# 2. การจัดการสี (Color Palette ตามไฟล์ PDF)
COLOR_RESPONSIBILITY = {
    "ป่าอนุรักษ์": "#1B5E20",      # เขียวเข้ม
    "ป่าสงวนแห่งชาติ": "#4CAF50",  # เขียวสว่าง
    "เขต สปก.": "#FB8C00",        # ส้ม
    "พื้นที่เกษตร": "#FBC02D",     # เหลืองทอง
    "ชุมชนและอื่นๆ": "#757575",    # เทา
    "พื้นที่ริมทางหลวง": "#795548"   # น้ำตาล
}

COLOR_HOTSPOT = [176, 0, 32, 180] # สีแดงเข้ม (B00020) สำหรับจุดในแผนที่

# 3. ฟังก์ชันโหลดข้อมูล (Optimization)
@st.cache_data(ttl=3600)
def load_data():
    sheet_id = "19iGWLP1HFF9NuVxZWNgphNUaBnifyJ4WsYQoZMLtLOE"
    sheet_name = "hotspot2022-2024"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    
    # โหลดเฉพาะคอลัมน์ A-I (LATITUDE ถึง การใช้ที่ดิน)
    cols = ['LATITUDE', 'LONGITUDE', 'วัน', 'ประเทศ', 'ตำบล', 'อำเภอ', 'จังหวัด', 'พื้นที่รับผิดชอบ', 'การใช้ที่ดิน']
    df = pd.read_csv(url, usecols=cols, low_memory=False)
    df.columns = df.columns.str.strip()
    
    # แปลงวันที่ dd/mm/yyyy
    df['วัน'] = pd.to_datetime(df['วัน'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['วัน'])
    
    # แปลง Category เพื่อประหยัด RAM
    cat_cols = ['จังหวัด', 'อำเภอ', 'พื้นที่รับผิดชอบ', 'การใช้ที่ดิน']
    for col in cat_cols:
        df[col] = df[col].astype('category')
        
    return df

# โหลดข้อมูล
try:
    data = load_data()
except Exception as e:
    st.error(f"ไม่สามารถเชื่อมต่อข้อมูลได้: {e}")
    st.stop()

# 4. SIDEBAR NAVIGATION (เลียนแบบเมนูด้านซ้ายใน PDF)
with st.sidebar:
    st.image("https://www.gistda.or.th/main/sites/default/files/gistda_logo_2022.png", width=120)
    st.title("Menu Navigation")
    page = st.radio("หัวข้อรายงาน", ["📊 ภาพรวม (Overview)", "📍 วิเคราะห์เชิงพื้นที่ (Map)", "📉 สถิติการใช้ที่ดิน", "📄 ข้อมูลรายจุด"])
    
    st.divider()
    st.header("ตัวกรองข้อมูล (Filters)")
    
    # Date Selection: Default = Yesterday
    last_date = data['วัน'].max().date()
    yesterday = last_date - timedelta(days=1)
    
    date_range = st.date_input(
        "ช่วงเวลา (เริ่ม: เมื่อวาน)",
        value=(yesterday, yesterday),
        min_value=data['วัน'].min().date(),
        max_value=last_date
    )
    
    # จังหวัด Filter
    selected_prov = st.multiselect("จังหวัด", options=sorted(data['จังหวัด'].unique()))
    
    # พื้นที่รับผิดชอบ Filter
    selected_resp = st.multiselect("พื้นที่รับผิดชอบ", options=data['พื้นที่รับผิดชอบ'].unique())

# 5. ประมวลผลการกรองข้อมูล
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    mask = (data['วัน'].dt.date >= start_date) & (data['วัน'].dt.date <= end_date)
else:
    mask = (data['วัน'].dt.date == date_range[0])

if selected_prov: mask &= data['จังหวัด'].isin(selected_prov)
if selected_resp: mask &= data['พื้นที่รับผิดชอบ'].isin(selected_resp)

f_data = data[mask]

# 6. ส่วนการแสดงผลตามหน้า (Pages)
if page == "📊 ภาพรวม (Overview)":
    st.header("สรุปสถานการณ์จุดความร้อนสะสม")
    
    # KPI Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("จุดความร้อนทั้งหมด", f"{len(f_data):,}")
    c2.metric("จังหวัดที่พบมากที่สุด", f_data['จังหวัด'].value_counts().idxmax() if not f_data.empty else "-")
    c3.metric("พื้นที่รับผิดชอบหลัก", f_data['พื้นที่รับผิดชอบ'].value_counts().idxmax() if not f_data.empty else "-")
    c4.metric("การใช้ที่ดินหลัก", f_data['การใช้ที่ดิน'].value_counts().idxmax() if not f_data.empty else "-")
    
    st.divider()
    
    col_l, col_r = st.columns([6, 4])
    with col_l:
        st.subheader("แยกตามพื้นที่รับผิดชอบ (Responsibility)")
        fig_resp = px.bar(f_data['พื้นที่รับผิดชอบ'].value_counts().reset_index(), 
                          x='count', y='พื้นที่รับผิดชอบ', orientation='h',
                          color='พื้นที่รับผิดชอบ', color_discrete_map=COLOR_RESPONSIBILITY)
        fig_resp.update_layout(showlegend=False)
        st.plotly_chart(fig_resp, use_container_width=True)
        
    with col_r:
        st.subheader("สัดส่วนการใช้ที่ดิน (Land Use Subset)")
        fig_land = px.pie(f_data, names='การใช้ที่ดิน', hole=0.4,
                          color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_land, use_container_width=True)

elif page == "📍 วิเคราะห์เชิงพื้นที่ (Map)":
    st.header("แผนที่แสดงตำแหน่งจุดความร้อนรายพิกัด")
    st.caption("จุดสีแดงแทนตำแหน่ง Hotspot (VIIRS)")
    
    # Map Layer
    view_state = pdk.ViewState(latitude=13.7, longitude=100.5, zoom=5)
    layer = pdk.Layer(
        "ScatterplotLayer",
        f_data,
        get_position='[LONGITUDE, LATITUDE]',
        get_color=COLOR_HOTSPOT,
        get_radius=1200,
        pickable=True,
    )
    
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v10',
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "วันที่: {วัน}\nจังหวัด: {จังหวัด}\nอำเภอ: {อำเภอ}\nพื้นที่: {พื้นที่รับผิดชอบ}\nการใช้ที่ดิน: {การใช้ที่ดิน}"}
    ))

elif page == "📉 สถิติการใช้ที่ดิน":
    st.header("การจำแนกจุดความร้อนตามการใช้ที่ดิน")
    st.info("กราฟนี้แสดงความสัมพันธ์ของประเภทที่ดินที่เป็น Subset ของพื้นที่รับผิดชอบ")
    
    # กราฟแท่งเปรียบเทียบ จังหวัด vs การใช้ที่ดิน
    top_provinces = f_data['จังหวัด'].value_counts().head(10).index
    subset_df = f_data[f_data['จังหวัด'].isin(top_provinces)]
    
    fig_subset = px.histogram(subset_df, x='จังหวัด', color='การใช้ที่ดิน', 
                              barmode='stack', title="Top 10 จังหวัดแยกตามการใช้ที่ดิน")
    st.plotly_chart(fig_subset, use_container_width=True)

elif page == "📄 ข้อมูลรายจุด":
    st.header("ตารางข้อมูลจุดความร้อนล่าสุด (Raw Data)")
    st.write(f"แสดงข้อมูลทั้งหมด {len(f_data):,} แถว")
    st.dataframe(f_data, use_container_width=True)
