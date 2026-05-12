import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px

# 1. ตั้งค่าหน้าจอ
st.set_page_config(layout="wide", page_title="Hotspot Dashboard")

# 2. ฟังก์ชันดึงข้อมูล
@st.cache_data
def load_data():
    sheet_id = "19iGWLP1HFF9NuVxZWNgphNUaBnifyJ4WsYQoZMLtLOE"
    sheet_name = "hotspot2022-2024"
    # ใช้ URL แบบดึง CSV โดยตรง
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    
    # อ่านข้อมูล (ระบุเฉพาะคอลัมน์ที่ต้องใช้เพื่อประหยัด RAM)
    df = pd.read_csv(url)
    
    # ล้างช่องว่างที่อาจติดมากับหัวตาราง (สำคัญมากสำหรับภาษาไทย)
    df.columns = df.columns.str.strip()
    
    # แปลงคอลัมน์ 'วัน' ให้เป็นวันที่
    if 'วัน' in df.columns:
        df['วัน'] = pd.to_datetime(df['วัน'])
    
    return df

st.title("🔥 ระบบติดตามจุดความร้อน (Hotspot Dashboard)")

# โหลดข้อมูล
with st.spinner('กำลังโหลดข้อมูล...'):
    data = load_data()
    st.write(data.columns.tolist())
# 3. Sidebar ตัวกรอง (ใช้ชื่อภาษาไทยตามที่คุณระบุ)
st.sidebar.header("ตัวกรองข้อมูล")

# กรองจังหวัด
selected_provinces = st.sidebar.multiselect(
    "เลือกจังหวัด", 
    options=sorted(data['จังหวัด'].unique()) if 'จังหวัด' in data.columns else []
)

# กรองการใช้ที่ดิน
selected_landuse = st.sidebar.multiselect(
    "การใช้ที่ดิน", 
    options=data['การใช้ที่ดิน'].unique() if 'การใช้ที่ดิน' in data.columns else [],
    default=data['การใช้ที่ดิน'].unique() if 'การใช้ที่ดิน' in data.columns else []
)

# ประมวลผลการกรอง
filtered_data = data[data['การใช้ที่ดิน'].isin(selected_landuse)]
if selected_provinces:
    filtered_data = filtered_data[filtered_data['จังหวัด'].isin(selected_provinces)]

# 4. แสดง KPI
col1, col2 = st.columns(2)
col1.metric("จำนวนจุดความร้อนที่พบ", f"{len(filtered_data):,}")

# 5. แผนที่ (ใช้ LATITUDE, LONGITUDE ภาษาอังกฤษตามที่คุณบอก)
st.subheader("📍 แผนที่ตำแหน่งจุดความร้อน")
layer = pdk.Layer(
    "ScatterplotLayer",
    filtered_data,
    get_position='[LONGITUDE, LATITUDE]',
    get_color='[255, 75, 75, 160]',
    get_radius=800,
    pickable=True,
)

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=pdk.ViewState(latitude=13.7, longitude=100.5, zoom=5),
    tooltip={"text": "จังหวัด: {จังหวัด}\nอำเภอ: {อำเภอ}\nที่ดิน: {การใช้ที่ดิน}"}
))

# 6. กราฟด้านล่าง
c1, c2 = st.columns(2)
with c1:
    st.subheader("📊 แยกตามการใช้ที่ดิน")
    fig_pie = px.pie(filtered_data, names='การใช้ที่ดิน', hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    st.subheader("🏆 10 จังหวัดที่มีจุดสูงสุด")
    top_provinces = filtered_data['จังหวัด'].value_counts().head(10).reset_index()
    fig_bar = px.bar(top_provinces, x='index', y='จังหวัด')
    st.plotly_chart(fig_bar, use_container_width=True)
