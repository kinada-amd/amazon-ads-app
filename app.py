import streamlit as st
import pandas as pd
import io
import requests
import plotly.graph_objects as go

# 1. ページ設定
st.set_page_config(page_title="Amazon Ads Analytics Pro", layout="wide", initial_sidebar_state="expanded")

# 2. デザイン修正（売上アプリと統一）
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    input { color: #131921 !important; }
    div[data-baseweb="select"] * { color: #131921 !important; }
    html, body, [data-testid="stAppViewContainer"], .stApp { background-color: #FFFFFF !important; color: #131921 !important; font-family: 'Inter', sans-serif !important; }
    #MainMenu, footer, header { visibility: hidden !important; }
    .stDeployButton, [data-testid="stStatusWidget"] {display:none !important;}
    [data-testid="stSidebar"] { background-color: #131921 !important; }
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }
    div[data-testid="stMetricValue"] { color: #131921 !important; font-weight: 800 !important; }
    h1, h2, h3 { color: #131921 !important; font-weight: 800 !important; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    return io.BytesIO(res.content)

try:
    # データの読み込み（広告実績 + 商品マスター）
    df_ads = pd.read_excel(load_data("http://gigaplus.makeshop.jp/aimedia/data/ads.xlsx"))
    df_m = pd.read_excel(load_data("http://gigaplus.makeshop.jp/aimedia/data/master.xlsx"))

    # クレンジング
    df_ads.columns = df_ads.columns.str.strip()
    df_ads['日付_dt'] = pd.to_datetime(df_ads['日付'], format='%Y年%m月', errors='coerce')
    df_ads['年月'] = df_ads['日付_dt'].dt.strftime('%Y-%m')

    # メイン表示
    st.title("Ads Performance Dashboard")
    
    # 相互リンクボタン
    st.sidebar.link_button("📊 売上分析へ戻る", "https://amazon-sales-app.streamlit.app/")
    st.sidebar.markdown("---")

    # 期間選択
    all_m = sorted(df_ads['年月'].dropna().unique(), reverse=True)
    target_p = st.sidebar.selectbox("分析期間を選択", all_m, index=0)

    # フィルタリングと集計
    df_f = pd.merge(df_ads[df_ads['年月'] == target_p], df_m, on='ASIN', how='left')
    
    # 指標計算
    total_spend = df_f['広告費'].sum()
    total_sales = df_f['広告売上'].sum()
    roas = total_sales / total_spend if total_spend > 0 else 0
    acos = (total_spend / total_sales) * 100 if total_sales > 0 else 0

    # サマリー
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("広告費合計", f"¥{int(total_spend):,}")
    m2.metric("広告売上合計", f"¥{int(total_sales):,}")
    m3.metric("ROAS", f"{roas:.2f}")
    m4.metric("ACOS", f"{acos:.1f}%")

    # ASIN別テーブル
    st.subheader("商品別広告パフォーマンス")
    disp = df_f.groupby(['ASIN', '正式品名', '規格']).agg({'広告費':'sum', '広告売上':'sum', 'クリック数':'sum'}).reset_index()
    disp['ROAS'] = disp['広告売上'] / disp['広告費']
    
    st.dataframe(
        disp.style.format({'広告費': '¥{:,.0f}', '広告売上': '¥{:,.0f}', 'ROAS': '{:.2f}'}),
        use_container_width=True, hide_index=True
    )

except Exception as e:
    st.error(f"エラーが発生しました: {e}")

### 3. 相互リンクの設定

相互に切り替えができるようにするため、**既存の売上アプリ（[https://amazon-sales-app.streamlit.app/](https://amazon-sales-app.streamlit.app/)）のコード**にも、サイドバーへ以下のボタンを追加してください。

```python
# 売上アプリのサイドバーに追記
st.sidebar.link_button("📢 広告実績分析へ", "https://（新しく作った広告アプリのURL）.streamlit.app/")

この手順で進めれば、同じAmazonトーン＆マナーの「売上」と「広告」を自由に行き来できる、強力な統合ダッシュボードが完成します！ぜひお試しください。
