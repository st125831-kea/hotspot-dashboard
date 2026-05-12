import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px

# 1. ตั้งค่าหน้าจอ
st.set_page_config(layout="wide", page_title="Hotspot Dashboard 2022-2026")

# 2. ฟังก์ชันดึงข้อมูลแบบ Optimized
@st.cache_data
def load_data():
    sheet_id = "19iGWLP1HFF9NuVxZWNgphNUaBnifyJ4WsYQoZMLtLOE"
    sheet_name = "hotspot2022-2024"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    
    # เพื่อประหยัด RAM: โหลดเฉพาะคอลัมน์ที่จำเป็นต้องใช้จริงๆ
    cols_to_use = ['LATITUDE', 'LONGITUDE', 'วัน', 'จังหวัด', 'อำเภอ', 'การใช้ที่ดิน']
    
    # อ่านข้อมูลพร้อมระบุ dtype เบื้องต้นเพื่อความเร็ว
    df = pd.read_csv(url, usecols=cols_to_use, low_memory=False)
    
    # ล้างช่องว่างหัวคอลัมน์
    df.columns = df.columns.str.strip()
    
    # แปลงวันที่แบบ dd/mm/yyyy (dayfirst=True)
    if 'วัน' in df.columns:
        df['วัน'] = pd.to_datetime(df['วัน'], dayfirst=True, errors='coerce')
        # ลบแถวที่วันที่ผิดพลาด
        df = df.dropna(subset=['วัน'])
    
    return df

# ส่วนหน้าจอหลัก
st.title("🔥 ระบบติดตามจุดความร้อน (Website Version)")
st.info(f"ข้อมูลปัจจุบันอ้างอิงรูปแบบวันที่: dd/mm/yyyy")

# โหลดข้อมูล
try:
    with st.spinner('กำลังประมวลผลข้อมูล 600,000 แถว...'):
        data = load_data()
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
    st.stop()

# 3. Sidebar ตัวกรอง
st.sidebar.header("ตัวกรองข้อมูล")

# กรองจังหวัด
all_provinces = sorted(data['จังหวัด'].unique())
selected_provinces = st.sidebar.multiselect("เลือกจังหวัด", options=all_provinces)

# กรองการใช้ที่ดิน
all_landuse = data['การใช้ที่ดิน'].unique()
selected_landuse = st.sidebar.multiselect("การใช้ที่ดิน", options=all_landuse, default=all_landuse)

# ประมวลผล Filter
filtered_data = data[data['การใช้ที่ดิน'].isin(selected_landuse)]
if selected_provinces:
    filtered_data = filtered_data[filtered_data['จังหวัด'].isin(selected_provinces)]

# 4. แสดงผล KPI
st.metric("จำนวนจุดความร้อนที่พบในตัวกรอง", f"{len(filtered_data):,}")

# 5. แผนที่ความละเอียดสูง (รองรับจุดจำนวนมาก)
st.subheader("📍 แผนที่ตำแหน่งพิกัดจุดความร้อน")

# สร้าง Layer แบบ Scatterplot
layer = pdk.Layer(
    "ScatterplotLayer",
    filtered_data,
    get_position='[LONGITUDE, LATITUDE]',
    get_color='[255, 75, 75, 140]',  # สีแดงใส
    get_radius=700,
    pickable=True,
)

# ตั้งค่ามุมมองเริ่มต้น (ให้เห็นทั่วไทย)
view_state = pdk.ViewState(latitude=13.7, longitude=100.5, zoom=5, pitch=0)

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={"text": "วันที่: {วัน}\nจังหวัด: {จังหวัด}\nประเภท: {การใช้ที่ดิน}"}
))

# 6. กราฟวิเคราะห์
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 สัดส่วนการใช้ที่ดิน")
    fig_pie = px.pie(filtered_data, names='การใช้ที่ดิน', hole=0.3)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    st.subheader("🏆 10 จังหวัดที่มีจุดสูงสุด")
    top_10 = filtered_data['จังหวัด'].value_counts().head(10).reset_index()
    top_10.columns = ['จังหวัด', 'จำนวนจุด']
    fig_bar = px.bar(top_10, x='จังหวัด', y='จำนวนจุด', color='จำนวนจุด', color_continuous_scale='Reds')
    st.plotly_chart(fig_bar, use_container_width=True)
