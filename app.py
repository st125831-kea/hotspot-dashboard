import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px

st.set_page_config(layout="wide", page_title="Hotspot Web App")

@st.cache_data(ttl=3600) # เก็บ Cache 1 ชม. เพื่อลดการโหลดซ้ำ
def load_data():
    sheet_id = "19iGWLP1HFF9NuVxZWNgphNUaBnifyJ4WsYQoZMLtLOE"
    sheet_name = "hotspot2022-2024"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    
    # 1. ระบุคอลัมน์ที่ "จำเป็นเท่านั้น" (ช่วยลด RAM มหาศาล)
    cols = ['LATITUDE', 'LONGITUDE', 'วัน', 'จังหวัด', 'การใช้ที่ดิน']
    
    # 2. กำหนด Type ข้อมูลให้เล็กลง (Optimization)
    dtypes = {
        'LATITUDE': 'float32',
        'LONGITUDE': 'float32',
        'จังหวัด': 'category',
        'การใช้ที่ดิน': 'category'
    }
    
    # อ่านข้อมูล
    df = pd.read_csv(url, usecols=cols, dtype=dtypes, low_memory=False)
    
    # ล้างหัวตาราง
    df.columns = df.columns.str.strip()
    
    # แปลงวันที่
    if 'วัน' in df.columns:
        df['วัน'] = pd.to_datetime(df['วัน'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['วัน'])
    
    return df

st.title("🔥 ระบบติดตามจุดความร้อน (Website Version)")

# แสดงสถานะ RAM ให้เห็นเบื้องหลัง (ถ้าต้องการ)
try:
    with st.spinner('กำลังโหลดข้อมูล (อาจใช้เวลา 1-2 นาทีเนื่องจากข้อมูลมีขนาดใหญ่)...'):
        data = load_data()
    
    # --- Sidebar ---
    st.sidebar.header("ตัวกรอง")
    prov_list = sorted(data['จังหวัด'].unique().tolist())
    sel_prov = st.sidebar.multiselect("เลือกจังหวัด", options=prov_list)
    
    land_list = data['การใช้ที่ดิน'].unique().tolist()
    sel_land = st.sidebar.multiselect("การใช้ที่ดิน", options=land_list, default=land_list)
    
    # กรองข้อมูล
    mask = data['การใช้ที่ดิน'].isin(sel_land)
    if sel_prov:
        mask &= data['จังหวัด'].isin(sel_prov)
    
    f_data = data[mask]
    
    # --- แสดงผล ---
    st.metric("จำนวนจุดความร้อน", f"{len(f_data):,}")
    
    # แผนที่
    st.subheader("📍 แผนที่พิกัดจุดความร้อน")
    st.pydeck_chart(pdk.Deck(
        layers=[pdk.Layer(
            "ScatterplotLayer",
            f_data,
            get_position='[LONGITUDE, LATITUDE]',
            get_color='[255, 75, 75, 120]',
            get_radius=800,
            pickable=True,
        )],
        initial_view_state=pdk.ViewState(latitude=13.7, longitude=100.5, zoom=5),
        tooltip={"text": "จังหวัด: {จังหวัด}\nการใช้ที่ดิน: {การใช้ที่ดิน}"}
    ))
    
    # กราฟ
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.pie(f_data, names='การใช้ที่ดิน', hole=0.4), use_container_width=True)
    with c2:
        top10 = f_data['จังหวัด'].value_counts().head(10).reset_index()
        top10.columns = ['จังหวัด', 'จำนวน']
        st.plotly_chart(px.bar(top10, x='จังหวัด', y='จำนวน'), use_container_width=True)

except Exception as e:
    st.error(f"แอปหยุดทำงานเนื่องจาก: {e}")
    st.info("คำแนะนำ: ข้อมูล 6 แสนแถวอาจใหญ่เกินไปสำหรับ Server ฟรี ลองเลือกแชร์เฉพาะคอลัมน์ที่จำเป็นใน Google Sheets")
