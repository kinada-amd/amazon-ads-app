import streamlit as st
import pandas as pd
import io
import requests
import plotly.graph_objects as go
import plotly.express as px

# 1. ページ設定
st.set_page_config(page_title="Amazon Ads Analytics", layout="wide")

# 2. デザイン修正（背景固定・ホバー挙動安定化・フォント同期）
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');

/* 1. デプロイボタンや余計なUIを排除 */
.stAppDeployButton, [data-testid="stStatusWidget"], footer, header, #MainMenu { 
    visibility: hidden !important; 
    display: none !important; 
}
div[data-testid="stDecoration"] { display: none !important; }

/* 2. メインエリア：背景白・文字黒・Interフォントに強制固定 */
html, body, [data-testid="stAppViewContainer"], .stApp, [data-testid="inner-content-container"], [data-testid="stVerticalBlock"] {
    background-color: #FFFFFF !important;
    color: #131921 !important;
    font-family: 'Inter', sans-serif !important;
}

/* 3. サイドバー：背景ネイビー・文字白に固定 */
[data-testid="stSidebar"] { 
    background-color: #131921 !important; 
}
[data-testid="stSidebar"] * { 
    color: #FFFFFF !important; 
    font-family: 'Inter', sans-serif !important;
}

/* 4. サイドバー内のプルダウン（期間選択）のみ黒文字 */
div[data-baseweb="select"] * { 
    color: #131921 !important; 
}

/* 5. グラフコンテナの背景を白に強制（ダークモード対策） */
iframe[title="st.plotly_chart"], .js-plotly-plot, .plot-container {
    background-color: #FFFFFF !important;
}

/* 6. 指標(Metric)と見出しのスタイル固定 */
div[data-testid="stMetricValue"] { 
    color: #131921 !important; 
    font-weight: 800 !important; 
}
h1, h2, h3, span, p, div { 
    color: #131921 !important; 
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] p {
    color: #FFFFFF !important;
}

/* 7. リンクボタンのAmazon風スタイル */
.stLinkButton a {
    background-color: #37475a !important;
    border: 1px solid #a2a6ac !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    text-decoration: none !important;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    return io.BytesIO(res.content)

try:
    df_ads = pd.read_excel(load_data("https://gigaplus.makeshop.jp/aimedia/data/ads.xlsx"))
    df_ads.columns = df_ads.columns.str.strip()
    if '売上' in df_ads.columns and '広告売上' not in df_ads.columns:
        df_ads = df_ads.rename(columns={'売上': '広告売上'})

    df_ads['日付_dt'] = pd.to_datetime(df_ads['日付'], format='%Y年%m月', errors='coerce')
    df_ads['年月'] = df_ads['日付_dt'].dt.strftime('%Y-%m')

    # サイドバー
    st.sidebar.markdown('<h2><i class="fa-solid fa-chart-line"></i> Ads Analytics</h2>', unsafe_allow_html=True)
    st.sidebar.link_button("売上分析アプリへ移動", "https://amazon-sales-app.streamlit.app/")
    st.sidebar.markdown("---")
    
    all_months = sorted(df_ads['年月'].dropna().unique(), reverse=True)
    target_month = st.sidebar.selectbox("表示する期間を選択", all_months, index=0)

    # メインタイトル
    st.title(f"Advertising Summary: {target_month}")

    df_month = df_ads[df_ads['年月'] == target_month].copy()
    
    m1, m2, m3, m4 = st.columns(4)
    total_sp = df_month['広告費'].sum()
    total_sa = df_month['広告売上'].sum()
    m1.metric("総広告費", f"¥{int(total_sp):,}")
    m2.metric("総広告売上", f"¥{int(total_sa):,}")
    m3.metric("ROAS", f"{(total_sa/total_sp*100):.0f}%" if total_sp > 0 else "0%")
    m4.metric("ACOS", f"{(total_sp/total_sa*100):.1f}%" if total_sa > 0 else "0.0%")

    col1, col2 = st.columns(2)
    
    type_summary = df_month.groupby('タイプ').agg({
        'インプレッション': 'sum', 'クリック数': 'sum', '広告費': 'sum', '注文': 'sum', '広告売上': 'sum'
    }).reset_index()

    with col1:
        st.subheader("タイプ別 広告費比率")
        amazon_colors = ['#232F3E', '#FF9900', '#37475A', '#A9A9A9']
        fig_pie = px.pie(type_summary, values='広告費', names='タイプ', 
                         color='タイプ', color_discrete_sequence=amazon_colors,
                         hole=0.4)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#FFFFFF', width=2)), insidetextfont=dict(size=16))
        fig_pie.update_layout(hoverlabel=dict(font_size=20), font_family="Inter")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("タイプ別 実績（広告売上）")
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=type_summary['タイプ'], 
            y=type_summary['広告売上'], 
            marker_color='#FF9900',
            text=type_summary['広告売上'].apply(lambda x: f"¥{x:,.0f}"), 
            textposition='outside', 
            textfont=dict(size=14, color='#131921', family="Inter"),
            hovertemplate='売上: ¥%{y:,.0f}<extra></extra>'
        ))
        fig_bar.update_layout(
            plot_bgcolor='white', margin=dict(t=40, b=20), 
            hoverlabel=dict(font_size=20), font_family="Inter",
            xaxis=dict(showline=True, linecolor='#d5d9d9'),
            yaxis=dict(showgrid=True, gridcolor='#F3F3F3', tickformat=',')
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader(f"{target_month} タイプ別実績詳細")
    
    type_summary['CTR'] = (type_summary['クリック数'] / type_summary['インプレッション'] * 100).fillna(0)
    type_summary['CPC'] = (type_summary['広告費'] / type_summary['クリック数']).fillna(0)
    type_summary['ROAS'] = (type_summary['広告売上'] / type_summary['広告費'] * 100).fillna(0)
    type_summary['CV率'] = (type_summary['注文'] / type_summary['クリック数'] * 100).fillna(0)
    type_summary['ACOS'] = (type_summary['広告費'] / type_summary['広告売上'] * 100).fillna(0)
    
    ts_table = type_summary[['タイプ', 'インプレッション', 'クリック数', 'CTR', 'CPC', '広告費', '注文', '広告売上', 'ROAS', 'CV率', 'ACOS']]

    st.dataframe(
        ts_table.style.format({
            'インプレッション': '{:,.0f}', 'クリック数': '{:,.0f}', 'CTR': '{:.2f}%',
            'CPC': '¥{:,.0f}', '広告費': '¥{:,.0f}', '注文': '{:,.0f}',
            '広告売上': '¥{:,.0f}', 'ROAS': '{:,.0f}%', 'CV率': '{:.1f}%', 'ACOS': '{:.1f}%'
        }),
        use_container_width=True, hide_index=True
    )

    st.markdown("---")
    st.subheader("月別 広告総合実績推移 (All Metrics)")
    
    monthly_trend = df_ads.groupby('年月').agg({
        'インプレッション': 'sum', 'クリック数': 'sum', '広告費': 'sum', '注文': 'sum', '広告売上': 'sum'
    }).sort_index(ascending=False).reset_index()

    monthly_trend['CTR'] = (monthly_trend['クリック数'] / monthly_trend['インプレッション'] * 100).fillna(0)
    monthly_trend['CPC'] = (monthly_trend['広告費'] / monthly_trend['クリック数']).fillna(0)
    monthly_trend['ROAS'] = (monthly_trend['広告売上'] / monthly_trend['広告費'] * 100).fillna(0)
    monthly_trend['CV率'] = (monthly_trend['注文'] / monthly_trend['クリック数'] * 100).fillna(0)
    monthly_trend['ACOS'] = (monthly_trend['広告費'] / monthly_trend['広告売上'] * 100).fillna(0)

    mt_table = monthly_trend[['年月', 'インプレッション', 'クリック数', 'CTR', 'CPC', '広告費', '注文', '広告売上', 'ROAS', 'CV率', 'ACOS']]

    st.dataframe(
        mt_table.style.format({
            'インプレッション': '{:,.0f}', 'クリック数': '{:,.0f}', 'CTR': '{:.2f}%',
            'CPC': '¥{:,.0f}', '広告費': '¥{:,.0f}', '注文': '{:,.0f}',
            '広告売上': '¥{:,.0f}', 'ROAS': '{:,.0f}%', 'CV率': '{:.1f}%', 'ACOS': '{:.1f}%'
        }),
        use_container_width=True, hide_index=True
    )

except Exception as e:
    st.error(f"データの読み込みに失敗しました。詳細エラー: {e}")