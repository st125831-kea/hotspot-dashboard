import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from datetime import datetime, timedelta

# 1. Page Config & Custom CSS
st.set_page_config(layout="wide", page_title="Hotspot Dashboard", page_icon="🔥")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 800 !important; color: #B00020; }
    [data-testid="stMetricLabel"] { font-size: 1.1rem !important; font-weight: 600 !important; }
    .main { background-color: #F8F9FA; }
    </style>
    """, unsafe_allow_html=True)

# 2. ปรับสีตาม Screenshot (586) และ (587)
COLORS_RESPONSIBILITY = {
    "ป่าอนุรักษ์": "#006400",       # เขียวเข้ม
    "ป่าสงวนแห่งชาติ": "#32CD32",   # เขียวสว่าง
    "เขต สปก.": "#FFD700",         # เหลืองทอง
    "พื้นที่เกษตร": "#FFA500",      # ส้ม
    "ชุมชนและอื่นๆ": "#FF0000",     # แดง
    "พื้นที่ริมทางหลวง": "#8B4513"    # น้ำตาล
}

COLORS_LANDUSE = {
    "นาข้าว": "#FFFF00",           # เหลือง
    "ข้าวโพดและไร่หมุนเวียน": "#FF8C00", # ส้มเข้ม
    "อ้อย": "#FF1493",             # ชมพูเข้ม
    "พื้นที่ป่า": "#228B22",         # เขียวป่า
    "เกษตรอื่นๆ": "#00CED1",       # ฟ้าอมเขียว
    "อื่น ๆ": "#A9A9A9"            # เทา
}

# 3. Load Data
@st.cache_data(ttl=3600)
def load_data():
    sheet_id = "19iGWLP1HFF9NuVxZWNgphNUaBnifyJ4WsYQoZMLtLOE"
    sheet_name = "hotspot2022-2024"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    cols = ['LATITUDE', 'LONGITUDE', 'วัน', 'จังหวัด', 'พื้นที่รับผิดชอบ', 'การใช้ที่ดิน']
    df = pd.read_csv(url, usecols=cols, low_memory=False)
    df.columns = df.columns.str.strip()
    df['วัน'] = pd.to_datetime(df['วัน'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['วัน'])
    return df

data = load_data()

# 4. Sidebar Controls
with st.sidebar:
    st.image("https://www.gistda.or.th/main/sites/default/files/gistda_logo_2022.png", width=120)
    menu = st.radio("เลือกหัวข้อ", ["การใช้ที่ดิน (Land Use)", "พื้นที่รับผิดชอบ (Responsibility)", "จุดความร้อนสะสมรายปี"])
    st.divider()
    max_d = data['วัน'].max().date()
    yesterday_val = max_d - timedelta(days=1)
    date_input = st.date_input("เลือกวันที่", value=(yesterday_val, yesterday_val))
    all_years = sorted(data['วัน'].dt.year.unique(), reverse=True)
    selected_years = st.multiselect("เลือกปีที่ต้องการเปรียบเทียบ", options=all_years, default=all_years)

# Filtering
if isinstance(date_input, tuple) and len(date_input) == 2:
    start_d, end_d = date_input
    f_data = data[(data['วัน'].dt.date >= start_d) & (data['วัน'].dt.date <= end_d)].copy()
else:
    f_data = data[data['วัน'].dt.date == date_input[0]].copy()
    start_d = date_input[0]

# 5. Functions for Comparison
def get_deltas(full_df, start_date):
    day_before = start_date - timedelta(days=1)
    count_yesterday = len(full_df[full_df['วัน'].dt.date == day_before])
    last_year_date = start_date - timedelta(days=365)
    count_last_year = len(full_df[full_df['วัน'].dt.date == last_year_date])
    return count_yesterday, count_last_year

# 6. Dashboard Content
if menu in ["การใช้ที่ดิน (Land Use)", "พื้นที่รับผิดชอบ (Responsibility)"]:
    color_col = 'การใช้ที่ดิน' if menu == "การใช้ที่ดิน (Land Use)" else 'พื้นที่รับผิดชอบ'
    color_palette = COLORS_LANDUSE if menu == "การใช้ที่ดิน (Land Use)" else COLORS_RESPONSIBILITY
    
    col_map, col_info = st.columns([6, 4])
    
    with col_map:
        st.subheader(f"แผนที่พิกัด: {menu}")
        def hex_to_rgb(hex_str):
            h = hex_str.lstrip('#')
            return [int(h[i:i+2], 16) for i in (0, 2, 4)]
        
        f_data['color'] = f_data[color_col].map(lambda x: hex_to_rgb(color_palette.get(x, "#B00020")))
        
        # ปรับแก้ Map Style เป็น 'light' เพื่อให้โครงสร้างแผนที่ขึ้นแน่นอน (เหมือน Screenshot 588)
        st.pydeck_chart(pdk.Deck(
            map_style='light', 
            initial_view_state=pdk.ViewState(latitude=13.7, longitude=100.5, zoom=5, pitch=0),
            layers=[pdk.Layer(
                "ScatterplotLayer", 
                f_data, 
                get_position='[LONGITUDE, LATITUDE]',
                get_fill_color='color', 
                get_radius=1800, 
                pickable=True
            )],
            tooltip={"text": "จังหวัด: {จังหวัด}\nประเภท: {" + color_col + "}"}
        ))

    with col_info:
        total_now = len(f_data)
        count_yest, count_ly = get_deltas(data, start_d)
        
        st.metric("จำนวนจุดวันนี้", f"{total_now:,}", delta=f"{total_now - count_yest} จากเมื่อวาน", delta_color="inverse")
        diff_ly = total_now - count_ly
        perc_ly = (diff_ly / count_ly * 100) if count_ly > 0 else 0
        st.metric("เทียบกับปีที่แล้ว", f"{total_now:,}", delta=f"{diff_ly:+} ({perc_ly:.1f}%)", delta_color="inverse")

        fig = px.pie(f_data, names=color_col, color=color_col, color_discrete_map=color_palette, hole=0.5)
        fig.update_traces(textinfo='value', textfont_size=14)
        fig.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0), legend=dict(orientation="h", yanchor="bottom", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)

elif menu == "จุดความร้อนสะสมรายปี":
    st.title("📈 แนวโน้มจุดความร้อนสะสมรายปี")
    line_data = data[data['วัน'].dt.year.isin(selected_years)].copy()
    line_data['day_of_year'] = line_data['วัน'].dt.dayofyear
    line_data['year'] = line_data['วัน'].dt.year.astype(str)
    daily_counts = line_data.groupby(['year', 'day_of_year']).size().reset_index(name='daily_count')
    daily_counts['accumulated'] = daily_counts.groupby('year')['daily_count'].cumsum()
    fig_line = px.line(daily_counts, x='day_of_year', y='accumulated', color='year', title="กราฟเปรียบเทียบยอดสะสมรายปี")
    st.plotly_chart(fig_line, use_container_width=True)
