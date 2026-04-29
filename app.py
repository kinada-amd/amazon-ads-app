import streamlit as st
import pandas as pd
import io
import requests
import plotly.graph_objects as go
import plotly.express as px

# 1. ページ設定
st.set_page_config(page_title="Amazon Ads Analytics", layout="wide")

# 2. 強力なCSS
st.markdown("""
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
    div[data-testid="stMetricValue"] { color: #131921 !important; font-weight: 800 !important; }
    h1, h2, h3 { color: #131921 !important; font-weight: 800 !important; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    return io.BytesIO(res.content)

try:
    # データ読み込み
    df_ads = pd.read_excel(load_data("https://gigaplus.makeshop.jp/aimedia/data/ads.xlsx"))
    
    # 列名のクレンジング（スペース削除）
    df_ads.columns = df_ads.columns.str.strip()

    # --- 列名の柔軟な対応ロジック ---
    # 「広告売上」がなければ「売上」を探す
    if '広告売上' not in df_ads.columns and '売上' in df_ads.columns:
        df_ads = df_ads.rename(columns={'売上': '広告売上'})
    
    # 必須列のチェック
    required_cols = ['日付', 'タイプ', '広告費', '広告売上']
    missing_cols = [c for c in required_cols if c not in df_ads.columns]
    if missing_cols:
        st.error(f"Excel内に必要な列が見つかりません: {missing_cols}")
        st.stop()

    # 前処理
    df_ads['日付_dt'] = pd.to_datetime(df_ads['日付'], format='%Y年%m月', errors='coerce')
    df_ads['年月'] = df_ads['日付_dt'].dt.strftime('%Y-%m')

    # サイドバー
    st.sidebar.title("Ads Analytics")
    st.sidebar.link_button("📊 売上分析アプリへ", "https://amazon-sales-app.streamlit.app/")
    st.sidebar.markdown("---")
    
    all_months = sorted(df_ads['年月'].dropna().unique(), reverse=True)
    target_month = st.sidebar.selectbox("分析対象月を選択", all_months, index=0)

    st.title(f"Advertising Summary: {target_month}")

    df_month = df_ads[df_ads['年月'] == target_month]
    
    type_summary = df_month.groupby('タイプ').agg({
        '広告費': 'sum',
        '広告売上': 'sum'
    }).reset_index()

    m1, m2, m3, m4 = st.columns(4)
    total_sp = df_month['広告費'].sum()
    total_sa = df_month['広告売上'].sum()
    m1.metric("総広告費", f"¥{int(total_sp):,}")
    m2.metric("総広告売上", f"¥{int(total_sa):,}")
    m3.metric("ROAS", f"{(total_sa/total_sp):.2f}" if total_sp > 0 else "0.00")
    m4.metric("ACOS", f"{(total_sp/total_sa*100):.1f}%" if total_sa > 0 else "0.0%")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("タイプ別 広告費比率")
        fig_pie = px.pie(type_summary, values='広告費', names='タイプ', 
                         color='タイプ', color_discrete_sequence=['#FF9900', '#232F3E', '#37475A', '#D5D9D9'],
                         hole=0.4)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("タイプ別 実績比較")
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(name='広告費', x=type_summary['タイプ'], y=type_summary['広告費'], marker_color='#232F3E'))
        fig_bar.add_trace(go.Bar(name='広告売上', x=type_summary['タイプ'], y=type_summary['広告売上'], marker_color='#FF9900'))
        fig_bar.update_layout(barmode='group', plot_bgcolor='white', margin=dict(t=20, b=20))
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    st.subheader("月別 広告総合実績推移")
    monthly_trend = df_ads.groupby('年月').agg({
        '広告費': 'sum',
        '広告売上': 'sum'
    }).sort_index(ascending=False).reset_index()

    monthly_trend['ROAS'] = monthly_trend['広告売上'] / monthly_trend['広告費']
    monthly_trend['ACOS'] = (monthly_trend['広告費'] / monthly_trend['広告売上']) * 100

    st.dataframe(
        monthly_trend.style.format({
            '広告費': '¥{:,.0f}',
            '広告売上': '¥{:,.0f}',
            'ROAS': '{:.2f}',
            'ACOS': '{:.1f}%'
        }),
        use_container_width=True, hide_index=True
    )

except Exception as e:
    st.error(f"データの読み込みに失敗しました。詳細エラー: {e}")