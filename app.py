import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px

# 1. การตั้งค่าหน้าจอให้กว้างเหมือน Dashboard
st.set_page_config(layout="wide", page_title="Hotspot Dashboard 2022-2024")

# 2. ฟังก์ชันดึงข้อมูลจาก Google Sheets และทำ Cache (เพื่อความเร็ว)
@st.cache_data
def load_data():
    # URL สำหรับ Export Google Sheets เป็น CSV
    sheet_id = "19iGWLP1HFF9NuVxZWNgphNUaBnifyJ4WsYQoZMLtLOE"
    sheet_name = "hotspot2022-2024"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    
    df = pd.read_csv(url)
    # แปลงวันที่ให้เป็น Format ที่ถูกต้อง
    if 'ACQ_DATE' in df.columns:
        df['ACQ_DATE'] = pd.to_datetime(df['ACQ_DATE'])
    return df

st.title("🔥 ระบบติดตามจุดความร้อน (Hotspot Dashboard)")
st.markdown("แสดงข้อมูลจาก Google Sheets (600,000+ records)")

# โหลดข้อมูล
with st.spinner('กำลังประมวลผลข้อมูลมหาศาล...'):
    data = load_data()

# 3. ส่วนของ Sidebar สำหรับตัวกรอง (Filters)
st.sidebar.header("ตัวกรองข้อมูล")
selected_provinces = st.sidebar.multiselect(
    "เลือกจังหวัด", 
    options=sorted(data['PROVINCE_NAME_TH'].unique()),
    default=[]
)

selected_landuse = st.sidebar.multiselect(
    "ประเภทการใช้ประโยชน์ที่ดิน", 
    options=data['LANDUSE_TYPE'].unique(),
    default=data['LANDUSE_TYPE'].unique()
)

# กรองข้อมูลตามที่เลือก
filtered_data = data[data['LANDUSE_TYPE'].isin(selected_landuse)]
if selected_provinces:
    filtered_data = filtered_data[filtered_data['PROVINCE_NAME_TH'].isin(selected_provinces)]

# 4. แสดง KPI Cards (ส่วนบนของต้นแบบ)
col1, col2, col3, col4 = st.columns(4)
col1.metric("จำนวนจุดความร้อนทั้งหมด", f"{len(filtered_data):,}")
# (คุณสามารถเพิ่มสูตรคำนวณ % การเปลี่ยนแปลงเทียบกับปีที่แล้วได้ที่นี่)

# 5. แผนที่ความละเอียดสูง (Pydeck) - แสดงได้เป็นแสนจุดโดยไม่ค้าง
st.subheader("📍 แผนที่ตำแหน่งจุดความร้อน")

# กำหนด Layer สำหรับแผนที่
layer = pdk.Layer(
    "ScatterplotLayer",
    filtered_data,
    get_position='[LONGITUDE, LATITUDE]',
    get_color='[255, 75, 75, 160]',  # สีแดงโปร่งแสง
    get_radius=500,
    pickable=True,
)

view_state = pdk.ViewState(
    latitude=13.7367, longitude=100.5231, zoom=5, pitch=0
)

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={"text": "จังหวัด: {PROVINCE_NAME_TH}\nวันที่: {ACQ_DATE}"}
))

# 6. กราฟวิเคราะห์ (ส่วนล่างของต้นแบบ)
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.subheader("📊 แยกตามประเภทที่ดิน")
    fig_pie = px.pie(filtered_data, names='LANDUSE_TYPE', hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    st.subheader("🏆 10 จังหวัดที่มีจุดความร้อนสูงสุด")
    top_provinces = filtered_data['PROVINCE_NAME_TH'].value_counts().head(10).reset_index()
    fig_bar = px.bar(top_provinces, x='index', y='PROVINCE_NAME_TH', labels={'index':'จังหวัด', 'PROVINCE_NAME_TH':'จำนวนจุด'})
    st.plotly_chart(fig_bar, use_container_width=True)