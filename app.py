import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from datetime import datetime

# 1. การตั้งค่าหน้าจอและธีมสว่าง
st.set_page_config(
    layout="wide", 
    page_title="ระบบรายงานจุดความร้อนประเทศไทย",
    page_icon="🔥"
)

# ปรับสไตล์ CSS ให้ดูเหมือนรายงาน (ธีมสว่าง, ฟอนต์สะอาด)
st.markdown("""
    <style>
    .main { background-color: #FFFFFF; }
    .stMetric { background-color: #F8F9FA; padding: 15px; border-radius: 10px; border: 1px solid #E9ECEF; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #F1F3F5;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #FF4B4B !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. ฟังก์ชันโหลดข้อมูล (Optimization สูงสุด)
@st.cache_data(ttl=3600)
def load_data():
    sheet_id = "19iGWLP1HFF9NuVxZWNgphNUaBnifyJ4WsYQoZMLtLOE"
    sheet_name = "hotspot2022-2024"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    
    # โหลดเฉพาะคอลัมน์ที่จำเป็นเพื่อประหยัด RAM
    cols = ['LATITUDE', 'LONGITUDE', 'วัน', 'จังหวัด', 'อำเภอ', 'การใช้ที่ดิน', 'พื้นที่รับผิดชอบ']
    df = pd.read_csv(url, usecols=cols, low_memory=False)
    df.columns = df.columns.str.strip()
    
    # แปลงวันที่
    df['วัน'] = pd.to_datetime(df['วัน'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['วัน'])
    
    # ปรับ Type เพื่อประหยัด RAM
    df['จังหวัด'] = df['จังหวัด'].astype('category')
    df['การใช้ที่ดิน'] = df['การใช้ที่ดิน'].astype('category')
    return df

# โหลดข้อมูล
try:
    data = load_data()
except Exception as e:
    st.error(f"ไม่สามารถโหลดข้อมูลได้: {e}")
    st.stop()

# 3. ส่วนแถบด้านข้าง (Sidebar) - Filters
with st.sidebar:
    st.image("https://www.gistda.or.th/main/sites/default/files/gistda_logo_2022.png", width=150)
    st.header("ตัวเลือกการกรอง")
    
    # Calendar Selection (เลือกช่วงวันที่)
    min_date = data['วัน'].min().date()
    max_date = data['วัน'].max().date()
    date_range = st.date_input("เลือกช่วงเวลา", [min_date, max_date], min_value=min_date, max_value=max_date)
    
    # Filter จังหวัด และ การใช้ที่ดิน
    prov_filter = st.multiselect("จังหวัด", options=sorted(data['จังหวัด'].unique()))
    land_filter = st.multiselect("ประเภทการใช้ที่ดิน", options=sorted(data['การใช้ที่ดิน'].unique()))

# กรองข้อมูลตาม Filter
mask = (data['วัน'].dt.date >= date_range[0]) & (data['วัน'].dt.date <= date_range[1])
if prov_filter:
    mask &= data['จังหวัด'].isin(prov_filter)
if land_filter:
    mask &= data['การใช้ที่ดิน'].isin(land_filter)

f_data = data[mask]

# 4. ส่วนเนื้อหาหลัก (Main Interface) ตามแบบ PDF
st.title("📊 รายงานสถานการณ์จุดความร้อน (Hotspot Reporting)")
st.caption(f"ข้อมูลระหว่างวันที่ {date_range[0]} ถึง {date_range[1]}")

# สร้าง Tabs (แบ่งหมวดหมู่เหมือนหน้าใน PDF)
tab1, tab2, tab3 = st.tabs(["📌 ภาพรวมระดับประเทศ", "🗺️ แผนที่พิกัดเชิงลึก", "📉 แนวโน้มและสถิติ"])

# --- TAB 1: ภาพรวม (Overview) ---
with tab1:
    col1, col2, col3 = st.columns(3)
    col1.metric("จุดความร้อนสะสม", f"{len(f_data):,}")
    # จำลองค่าเปรียบเทียบ (ถ้ามีข้อมูลปีเก่าสามารถคำนวณจริงได้)
    col2.metric("จังหวัดที่พบสูงสุด", f_data['จังหวัด'].value_counts().idxmax() if not f_data.empty else "-")
    col3.metric("พื้นที่เฝ้าระวังหลัก", f_data['การใช้ที่ดิน'].value_counts().idxmax() if not f_data.empty else "-")
    
    st.divider()
    
    c1, c2 = st.columns([6, 4])
    with c1:
        st.subheader("สัดส่วนจุดความร้อนแยกตามประเภทที่ดิน")
        fig_pie = px.pie(f_data, names='การใช้ที่ดิน', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        st.subheader("10 จังหวัดที่มีจำนวนสูงสุด")
        top_10 = f_data['จังหวัด'].value_counts().head(10).reset_index()
        top_10.columns = ['จังหวัด', 'จำนวน']
        fig_bar = px.bar(top_10, y='จังหวัด', x='จำนวน', orientation='h', color='จำนวน', color_continuous_scale='Reds')
        st.plotly_chart(fig_bar, use_container_width=True)

# --- TAB 2: แผนที่ (Maps) ---
with tab2:
    st.subheader("ตำแหน่งจุดความร้อนรายพิกัด")
    view_state = pdk.ViewState(latitude=13.7, longitude=100.5, zoom=5, pitch=0)
    layer = pdk.Layer(
        "ScatterplotLayer",
        f_data,
        get_position='[LONGITUDE, LATITUDE]',
        get_color='[255, 75, 75, 160]',
        get_radius=1000,
        pickable=True,
    )
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "จังหวัด: {จังหวัด}\nอำเภอ: {อำเภอ}\nประเภท: {การใช้ที่ดิน}"}))

# --- TAB 3: แนวโน้ม (Trends) ---
with tab3:
    st.subheader("สถิติจุดความร้อนรายวัน (Time Series)")
    trend_data = f_data.groupby(f_data['วัน'].dt.date).size().reset_index(name='จำนวนจุด')
    fig_line = px.line(trend_data, x='วัน', y='จำนวนจุด', markers=True)
    fig_line.update_traces(line_color='#FF4B4B')
    st.plotly_chart(fig_line, use_container_width=True)
    
    st.subheader("ตารางข้อมูลสรุปรายอำเภอ")
    st.dataframe(f_data[['วัน', 'จังหวัด', 'อำเภอ', 'การใช้ที่ดิน']].head(1000), use_container_width=True)
