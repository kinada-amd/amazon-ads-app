import streamlit as st
import pandas as pd
import io
import requests
import plotly.graph_objects as go
import plotly.express as px

# 1. ページ設定
st.set_page_config(page_title="Amazon Ads Analytics", layout="wide")

# 2. デザイン修正（margin/padding設定を元に戻し、厳守）
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

/* ページ全体の余白設定を初期状態に固定 */
.st-emotion-cache-zy6yx3 {padding-top: 1rem !important;padding-bottom: 3rem !important;}
.st-emotion-cache-qmp9ai {visibility: visible;}
.st-emotion-cache-1r1cntt {padding-top: 1rem;}
.st-emotion-cache-10p9htt {display: none;}

/* 比較用テーブル内のデザイン（ページ全体の余白に影響しないようスコープを限定） */
.custom-comp-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
    margin-bottom: 2rem;
}
.custom-comp-table th {
    background-color: #f8f9fb;
    border: 1px solid #e6e9ef;
    padding: 8px 12px;
    text-align: left;
    font-size: 14px;
    font-weight: 600;
}
.custom-comp-table td {
    border: 1px solid #e6e9ef;
    padding: 10px 12px;
    font-size: 14px;
    vertical-align: middle;
}
.delta-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 700;
    margin-left: 8px;
}
.tag-up { background-color: #e6f4ea; color: #1e7e34; }
.tag-down { background-color: #fce8e6; color: #d93025; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    return io.BytesIO(res.content)

def get_tag(diff, is_cost=False, pre=""):
    if diff == 0: return '<span class="delta-tag" style="background:#f1f3f4;color:#5f6368;">±0</span>'
    is_plus = diff > 0
    # 広告費は増えると赤、その他は増えると緑
    cls = "tag-down" if (is_plus if is_cost else not is_plus) else "tag-up"
    sign = "+" if is_plus else ""
    return f'<span class="delta-tag {cls}">{sign}{pre}{diff:,.0f}</span>'

try:
    df_ads = pd.read_excel(load_data("https://gigaplus.makeshop.jp/aimedia/data/ads.xlsx"))
    df_ads.columns = df_ads.columns.str.strip()
    if '売上' in df_ads.columns and '広告売上' not in df_ads.columns:
        df_ads = df_ads.rename(columns={'売上': '広告売上'})

    df_ads['日付_dt'] = pd.to_datetime(df_ads['日付'], format='%Y年%m月', errors='coerce')
    df_ads['年月'] = df_ads['日付_dt'].dt.strftime('%Y-%m')

    # --- サイドバー ---
    st.sidebar.markdown('<h2>Amazon Ads Analytics</h2>', unsafe_allow_html=True)
    st.sidebar.link_button("売上実績へ切り替える", "https://amazon-sales-app.streamlit.app/")
    st.sidebar.markdown("---")
    
    view_mode = st.sidebar.radio("表示モードを選択", ["通常モード", "比較モード"], index=0)
    all_months = sorted(df_ads['年月'].dropna().unique(), reverse=True)

    if view_mode == "通常モード":
        target_month = st.sidebar.selectbox("表示する期間を選択", all_months, index=0)
        st.title(f"Advertising Summary: {target_month}")
        df_month = df_ads[df_ads['年月'] == target_month].copy()
        
        m1, m2, m3, m4 = st.columns(4)
        total_sp, total_sa = df_month['広告費'].sum(), df_month['広告売上'].sum()
        m1.metric("総広告費", f"¥{int(total_sp):,}")
        m2.metric("総広告売上", f"¥{int(total_sa):,}")
        m3.metric("ROAS", f"{(total_sa/total_sp*100):.0f}%" if total_sp > 0 else "0%")
        m4.metric("ACOS", f"{(total_sp/total_sa*100):.1f}%" if total_sa > 0 else "0.0%")
        
        type_sum = df_month.groupby('タイプ').agg({'インプレッション':'sum','クリック数':'sum','広告費':'sum','注文':'sum','広告売上':'sum'}).reset_index()
        st.subheader(f"{target_month} タイプ別実績詳細")
        st.dataframe(type_sum.style.format({'インプレッション':'{:,.0f}','クリック数':'{:,.0f}','広告費':'¥{:,.0f}','注文':'{:,.0f}','広告売上':'¥{:,.0f}'}), use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("タイプ別 広告費比率")
            st.plotly_chart(px.pie(type_sum, values='広告費', names='タイプ', hole=0.4, color_discrete_sequence=['#232F3E', '#FF9900', '#37475A', '#A9A9A9']), use_container_width=True)
        with c2:
            st.subheader("タイプ別 実績")
            st.plotly_chart(px.bar(type_sum, x='タイプ', y='広告売上', text_auto=',.0f', color_discrete_sequence=['#FF9900']).update_layout(plot_bgcolor='white'), use_container_width=True)

    else:
        month_a = st.sidebar.selectbox("比較期間 A", all_months, index=0)
        month_b = st.sidebar.selectbox("比較期間 B", all_months, index=1 if len(all_months) > 1 else 0)
        st.title(f"Comparison: {month_a} vs {month_b}")
        
        df_a, df_b = df_ads[df_ads['年月'] == month_a].copy(), df_ads[df_ads['年月'] == month_b].copy()
        s_a, s_b = df_a.sum(numeric_only=True), df_b.sum(numeric_only=True)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("総広告費", f"¥{int(s_a['広告費']):,}", delta=f"¥{int(s_a['広告費']-s_b['広告費']):,}", delta_color="inverse")
        m2.metric("総広告売上", f"¥{int(s_a['広告売上']):,}", delta=f"¥{int(s_a['広告売上']-s_b['広告売上']):,}")
        m3.metric("ROAS", f"{(s_a['広告売上']/s_a['広告費']*100):.0f}%", delta=f"{(s_a['広告売上']/s_a['広告費']*100)-(s_b['広告売上']/s_b['広告費']*100):.1f}%")
        m4.metric("ACOS", f"{(s_a['広告費']/s_a['広告売上']*100):.1f}%", delta=f"{(s_a['広告費']/s_a['広告売上']*100)-(s_b['広告費']/s_b['広告売上']*100):.1f}%", delta_color="inverse")

        # 1. 総合実績テーブル
        st.subheader("広告総合実績比較")
        st.dataframe(pd.DataFrame([s_a, s_b], index=[month_a, month_b]).reset_index().rename(columns={'index':'年月'}).style.format({'インプレッション':'{:,.0f}','クリック数':'{:,.0f}','広告費':'¥{:,.0f}','注文':'{:,.0f}','広告売上':'¥{:,.0f}'}), use_container_width=True, hide_index=True)

        # 2. タイプ別実績比較 (HTMLチップ)
        st.subheader(f"タイプ別実績比較 ({month_a} vs {month_b})")
        g_a, g_b = df_a.groupby('タイプ').sum(numeric_only=True), df_b.groupby('タイプ').sum(numeric_only=True)
        
        tbl = '<table class="custom-comp-table"><tr><th>タイプ</th><th>インプレッション</th><th>クリック数</th><th>広告費</th><th>注文</th><th>広告売上</th><th>ROAS</th></tr>'
        for t in g_a.index:
            d = g_a.loc[t] - g_b.loc[t]
            ra = (g_a.loc[t,'広告売上']/g_a.loc[t,'広告費']*100) if g_a.loc[t,'広告費']>0 else 0
            rb = (g_b.loc[t,'広告売上']/g_b.loc[t,'広告費']*100) if g_b.loc[t,'広告費']>0 else 0
            tbl += f'<tr><td>{t}</td>'
            tbl += f'<td>{g_a.loc[t,"インプレッション"]:,.0f}{get_tag(d["インプレッション"])}</td>'
            tbl += f'<td>{g_a.loc[t,"クリック数"]:,.0f}{get_tag(d["クリック数"])}</td>'
            tbl += f'<td>¥{g_a.loc[t,"広告費"]:,.0f}{get_tag(d["広告費"], True, "¥")}</td>'
            tbl += f'<td>{g_a.loc[t,"注文"]:,.0f}{get_tag(d["注文"])}</td>'
            tbl += f'<td>¥{g_a.loc[t,"広告売上"]:,.0f}{get_tag(d["広告売上"], False, "¥")}</td>'
            tbl += f'<td>{ra:.0f}%<span class="delta-tag {"tag-up" if ra>=rb else "tag-down"}">{ra-rb:+.1f}%</span></td></tr>'
        st.markdown(tbl + '</table>', unsafe_allow_html=True)

        # 3. グラフ
        cg1, cg2 = st.columns(2)
        cdf = pd.concat([g_a.assign(期間=month_a), g_b.assign(期間=month_b)]).reset_index()
        with cg1:
            st.subheader("タイプ別 広告費比較")
            st.plotly_chart(px.bar(cdf, x='タイプ', y='広告費', color='期間', barmode='group', color_discrete_map={month_a:'#37475A', month_b:'#A9A9A9'}).update_layout(plot_bgcolor='white', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)), use_container_width=True)
        with cg2:
            st.subheader("タイプ別 実績比較")
            st.plotly_chart(px.bar(cdf, x='タイプ', y='広告売上', color='期間', barmode='group', color_discrete_map={month_a:'#FF9900', month_b:'#232F3E'}).update_layout(plot_bgcolor='white', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)), use_container_width=True)

    st.markdown("---")
    st.subheader("月別 広告総合実績推移 (All Metrics)")
    st.dataframe(df_ads.groupby('年月').sum(numeric_only=True).sort_index(ascending=False).reset_index().style.format({'インプレッション':'{:,.0f}','クリック数':'{:,.0f}','広告費':'¥{:,.0f}','注文':'{:,.0f}','広告売上':'¥{:,.0f}'}), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
