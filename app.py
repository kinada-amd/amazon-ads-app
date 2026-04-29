import streamlit as st
import pandas as pd
import io
import requests
import plotly.graph_objects as go
import plotly.express as px

# 1. ページ設定
st.set_page_config(page_title="Amazon Ads Analytics", layout="wide")

# 2. 強力なCSS（右下のバッジ非表示 ＋ Amazonブランドカラー）
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    
    /* 右下のバッジとアイコンを完全に隠す(最新版) */
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
    # HTTPからHTTPSへの修正を適用
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status() # エラーがあれば停止
    return io.BytesIO(res.content)

try:
    # 修正されたHTTPSプロトコルを使用
    df_ads = pd.read_excel(load_data("https://gigaplus.makeshop.jp/aimedia/data/ads.xlsx"))
    
    # 前処理
    df_ads.columns = df_ads.columns.str.strip()
    df_ads['日付_dt'] = pd.to_datetime(df_ads['日付'], format='%Y年%m月', errors='coerce')
    df_ads['年月'] = df_ads['日付_dt'].dt.strftime('%Y-%m')

    # サイドバー
    st.sidebar.title("Ads Analytics")
    st.sidebar.link_button("📊 売上分析アプリへ", "https://amazon-sales-app.streamlit.app/")
    st.sidebar.markdown("---")
    
    # ① 単月表示の切り替え
    all_months = sorted(df_ads['年月'].dropna().unique(), reverse=True)
    target_month = st.sidebar.selectbox("分析対象月を選択", all_months, index=0)

    st.title(f"Advertising Summary: {target_month}")

    # 当月データの抽出
    df_month = df_ads[df_ads['年月'] == target_month]
    
    # タイプ別に集計
    type_summary = df_month.groupby('タイプ').agg({
        '広告費': 'sum',
        '広告売上': 'sum'
    }).reset_index()

    # 指標の表示
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
    
    # ② 全タイプ合算の月毎推移表
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
        use_container_width=True,
        hide_index=True
    )

except Exception as e:
    st.error(f"データの読み込みに失敗しました。URL(HTTPS)またはファイル形式を確認してください。")
    st.info(f"詳細エラー: {e}")