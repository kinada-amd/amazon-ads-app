import streamlit as st
import pandas as pd
import io
import requests
import plotly.graph_objects as go
import plotly.express as px

# 1. ページ設定
st.set_page_config(page_title="Amazon Ads Analytics", layout="wide")

# 2. デザイン（CSS）
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
.stAppDeployButton, [data-testid="stStatusWidget"], footer, header, #MainMenu { visibility: hidden !important; display: none !important; }
div[data-testid="stDecoration"] { display: none !important; }
html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #FFFFFF !important;
    color: #131921 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stSidebar"] { background-color: #131921 !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
div[data-baseweb="select"] * { color: #131921 !important; }
.stLinkButton a {
    background-color: #37475a !important;
    border: 1px solid #a2a6ac !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    text-decoration: none !important;
}
div[data-testid="stMetricValue"] { color: #131921 !important; font-weight: 800 !important; font-family: 'Inter', sans-serif !important; }
h1, h2, h3 { color: #131921 !important; font-weight: 800 !important; font-family: 'Inter', sans-serif !important; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    return io.BytesIO(res.content)

# 指標計算用ヘルパー関数
def calculate_metrics(df):
    sp = df['広告費'].sum()
    sa = df['広告売上'].sum()
    roas = (sa / sp * 100) if sp > 0 else 0
    acos = (sp / sa * 100) if sa > 0 else 0
    return sp, sa, roas, acos

try:
    df_ads = pd.read_excel(load_data("https://gigaplus.makeshop.jp/aimedia/data/ads.xlsx"))
    df_ads.columns = df_ads.columns.str.strip()
    if '売上' in df_ads.columns and '広告売上' not in df_ads.columns:
        df_ads = df_ads.rename(columns={'売上': '広告売上'})

    df_ads['日付_dt'] = pd.to_datetime(df_ads['日付'], format='%Y年%m月', errors='coerce')
    df_ads['年月'] = df_ads['日付_dt'].dt.strftime('%Y-%m')
    all_months = sorted(df_ads['年月'].dropna().unique(), reverse=True)

    # --- サイドバー ---
    st.sidebar.markdown('<h2>Amazon Ads Analytics</h2>', unsafe_allow_html=True)
    st.sidebar.link_button("売上実績へ切り替える", "https://amazon-sales-app.streamlit.app/")
    st.sidebar.markdown("---")

    # 表示モード選択
    view_mode = st.sidebar.radio("表示モードを選択", ["通常モード", "比較モード"], index=0)

    if view_mode == "通常モード":
        target_month = st.sidebar.selectbox("表示する期間を選択", all_months, index=0)
    else:
        st.sidebar.info("比較する2つの期間を選択してください")
        month_a = st.sidebar.selectbox("比較期間 A (最新)", all_months, index=0)
        month_b = st.sidebar.selectbox("比較期間 B (過去)", all_months, index=1 if len(all_months) > 1 else 0)

    # --- メインコンテンツ ---
    if view_mode == "通常モード":
        st.title(f"Advertising Summary: {target_month}")
        df_month = df_ads[df_ads['年月'] == target_month].copy()
        
        sp, sa, roas, acos = calculate_metrics(df_month)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("総広告費", f"¥{int(sp):,}")
        m2.metric("総広告売上", f"¥{int(sa):,}")
        m3.metric("ROAS", f"{roas:.0f}%")
        m4.metric("ACOS", f"{acos:.1f}%")

    else:
        st.title(f"Comparison: {month_a} vs {month_b}")
        df_a = df_ads[df_ads['年月'] == month_a]
        df_b = df_ads[df_ads['年月'] == month_b]
        
        sp_a, sa_a, roas_a, acos_a = calculate_metrics(df_a)
        sp_b, sa_b, roas_b, acos_b = calculate_metrics(df_b)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("総広告費", f"¥{int(sp_a):,}", delta=f"¥{int(sp_a - sp_b):,}", delta_color="inverse")
        m2.metric("総広告売上", f"¥{int(sa_a):,}", delta=f"¥{int(sa_a - sa_b):,}")
        m3.metric("ROAS", f"{roas_a:.0f}%", delta=f"{roas_a - roas_b:.1f}%")
        m4.metric("ACOS", f"{acos_a:.1f}%", delta=f"{acos_a - acos_b:.1f}%", delta_color="inverse")

    # --- 共通のグラフ表示 (通常モードでも比較モードでも、target_monthまたはmonth_aを表示) ---
    display_month = target_month if view_mode == "通常モード" else month_a
    df_display = df_ads[df_ads['年月'] == display_month].copy()
    
    col1, col2 = st.columns(2)
    type_summary = df_display.groupby('タイプ').agg({
        'インプレッション': 'sum', 'クリック数': 'sum', '広告費': 'sum', '注文': 'sum', '広告売上': 'sum'
    }).reset_index()

    with col1:
        st.subheader(f"タイプ別 広告費比率 ({display_month})")
        amazon_colors = ['#232F3E', '#FF9900', '#37475A', '#A9A9A9']
        fig_pie = px.pie(type_summary, values='広告費', names='タイプ', color_discrete_sequence=amazon_colors, hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader(f"タイプ別 広告売上 ({display_month})")
        fig_bar = px.bar(type_summary, x='タイプ', y='広告売上', text_auto=',.0f')
        fig_bar.update_traces(marker_color='#FF9900')
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- 詳細テーブル (月別推移) ---
    st.markdown("---")
    st.subheader("月別 広告総合実績推移")
    
    monthly_trend = df_ads.groupby('年月').agg({
        'インプレッション': 'sum', 'クリック数': 'sum', '広告費': 'sum', '注文': 'sum', '広告売上': 'sum'
    }).sort_index(ascending=False).reset_index()

    monthly_trend['CTR'] = (monthly_trend['クリック数'] / monthly_trend['インプレッション'] * 100).fillna(0)
    monthly_trend['CPC'] = (monthly_trend['広告費'] / monthly_trend['クリック数']).fillna(0)
    monthly_trend['ROAS'] = (monthly_trend['広告売上'] / monthly_trend['広告費'] * 100).fillna(0)
    monthly_trend['CV率'] = (monthly_trend['注文'] / monthly_trend['クリック数'] * 100).fillna(0)
    monthly_trend['ACOS'] = (monthly_trend['広告費'] / monthly_trend['広告売上'] * 100).fillna(0)

    st.dataframe(
        monthly_trend.style.format({
            'インプレッション': '{:,.0f}', 'クリック数': '{:,.0f}', 'CTR': '{:.2f}%',
            'CPC': '¥{:,.0f}', '広告費': '¥{:,.0f}', '注文': '{:,.0f}',
            '広告売上': '¥{:,.0f}', 'ROAS': '{:,.0f}%', 'CV率': '{:.1f}%', 'ACOS': '{:.1f}%'
        }),
        use_container_width=True, hide_index=True
    )

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
