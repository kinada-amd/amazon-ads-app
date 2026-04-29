import streamlit as st
import pandas as pd
import io
import requests
import plotly.graph_objects as go
import plotly.express as px

# 1. ページ設定
st.set_page_config(page_title="Amazon Ads Analytics", layout="wide")

# 2. デザイン修正（チップデザインとテーブルの統一感）
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

/* 比較テーブル用デザイン（Streamlitの標準表に擬態） */
.comparison-table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    font-size: 14px;
}
.comparison-table th {
    background-color: #f8f9fb;
    color: #31333f;
    text-align: left;
    padding: 8px 12px;
    border: 1px solid #e6e9ef;
    font-weight: 600;
}
.comparison-table td {
    padding: 10px 12px;
    border: 1px solid #e6e9ef;
    color: #131921;
    vertical-align: middle;
}
.delta-chip {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 700;
    margin-left: 6px;
}
.chip-green { background-color: #e6f4ea; color: #1e7e34; }
.chip-red { background-color: #fce8e6; color: #d93025; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    return io.BytesIO(res.content)

def format_delta_chip(diff, is_cost=False, prefix=""):
    if diff == 0: return f'<span class="delta-chip" style="background:#f0f2f6;color:#5f6368;">(±0)</span>'
    # 広告費やACOSは増えると赤、その他は増えると緑
    is_positive = diff > 0
    if is_cost:
        status = "chip-red" if is_positive else "chip-green"
    else:
        status = "chip-green" if is_positive else "chip-red"
    sign = "+" if is_positive else ""
    val_str = f"{diff:,.0f}" if isinstance(diff, (int, float)) else str(diff)
    return f'<span class="delta-chip {status}">{sign}{prefix}{val_str}</span>'

try:
    df_ads = pd.read_excel(load_data("https://gigaplus.makeshop.jp/aimedia/data/ads.xlsx"))
    df_ads.columns = df_ads.columns.str.strip()
    if '売上' in df_ads.columns and '広告売上' not in df_ads.columns:
        df_ads = df_ads.rename(columns={'売上': '広告売上'})

    df_ads['日付_dt'] = pd.to_datetime(df_ads['日付'], format='%Y年%m月', errors='coerce')
    df_ads['年月'] = df_ads['日付_dt'].dt.strftime('%Y-%m')

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

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("タイプ別 広告費比率")
            st.plotly_chart(px.pie(type_sum, values='広告費', names='タイプ', hole=0.4, color_discrete_sequence=['#232F3E', '#FF9900', '#37475A', '#A9A9A9']), use_container_width=True)
        with col2:
            st.subheader("タイプ別 実績")
            st.plotly_chart(px.bar(type_sum, x='タイプ', y='広告売上', text_auto=',.0f', color_discrete_sequence=['#FF9900']).update_layout(plot_bgcolor='white'), use_container_width=True)

    else:
        month_a = st.sidebar.selectbox("比較期間 A", all_months, index=0)
        month_b = st.sidebar.selectbox("比較期間 B", all_months, index=1 if len(all_months) > 1 else 0)
        st.title(f"Comparison: {month_a} vs {month_b}")
        
        df_a, df_b = df_ads[df_ads['年月'] == month_a].copy(), df_ads[df_ads['年月'] == month_b].copy()
        sum_a, sum_b = df_a.sum(numeric_only=True), df_b.sum(numeric_only=True)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("総広告費", f"¥{int(sum_a['広告費']):,}", delta=f"¥{int(sum_a['広告費'] - sum_b['広告費']):,}", delta_color="inverse")
        m2.metric("総広告売上", f"¥{int(sum_a['広告売上']):,}", delta=f"¥{int(sum_a['広告売上'] - sum_b['広告売上']):,}")
        m3.metric("ROAS", f"{(sum_a['広告売上']/sum_a['広告費']*100):.0f}%", delta=f"{(sum_a['広告売上']/sum_a['広告費']*100)-(sum_b['広告売上']/sum_b['広告費']*100):.1f}%")
        m4.metric("ACOS", f"{(sum_a['広告費']/sum_a['広告売上']*100):.1f}%", delta=f"{(sum_a['広告費']/sum_a['広告売上']*100)-(sum_b['広告費']/sum_b['広告売上']*100):.1f}%", delta_color="inverse")

        # 1. 総合実績テーブル
        st.subheader("広告総合実績比較")
        comp_summary = pd.DataFrame([sum_a, sum_b], index=[month_a, month_b]).reset_index().rename(columns={'index':'年月'})
        st.dataframe(comp_summary.style.format({'インプレッション':'{:,.0f}','クリック数':'{:,.0f}','広告費':'¥{:,.0f}','注文':'{:,.0f}','広告売上':'¥{:,.0f}'}), use_container_width=True, hide_index=True)

        # 2. タイプ別実績比較テーブル (HTMLによるチップデザイン適用)
        st.subheader(f"タイプ別実績比較 ({month_a} vs {month_b})")
        g_a, g_b = df_a.groupby('タイプ').sum(numeric_only=True), df_b.groupby('タイプ').sum(numeric_only=True)
        
        html_table = '<table class="comparison-table"><tr><th>タイプ</th><th>インプレッション</th><th>クリック数</th><th>広告費</th><th>注文</th><th>広告売上</th><th>ROAS</th></tr>'
        for t in g_a.index:
            diff = g_a.loc[t] - g_b.loc[t]
            roas_a = (g_a.loc[t,'広告売上']/g_a.loc[t,'広告費']*100) if g_a.loc[t,'広告費']>0 else 0
            roas_b = (g_b.loc[t,'広告売上']/g_b.loc[t,'広告費']*100) if g_b.loc[t,'広告費']>0 else 0
            
            html_table += f'<tr><td>{t}</td>'
            html_table += f'<td>{g_a.loc[t,"インプレッション"]:,.0f}{format_delta_chip(diff["インプレッション"])}</td>'
            html_table += f'<td>{g_a.loc[t,"クリック数"]:,.0f}{format_delta_chip(diff["クリック数"])}</td>'
            html_table += f'<td>¥{g_a.loc[t,"広告費"]:,.0f}{format_delta_chip(diff["広告費"], is_cost=True, prefix="¥")}</td>'
            html_table += f'<td>{g_a.loc[t,"注文"]:,.0f}{format_delta_chip(diff["注文"])}</td>'
            html_table += f'<td>¥{g_a.loc[t,"広告売上"]:,.0f}{format_delta_chip(diff["広告売上"], prefix="¥")}</td>'
            html_table += f'<td>{roas_a:.0f}%<span class="delta-chip {"chip-green" if roas_a>=roas_b else "chip-red"}">{roas_a-roas_b:+.1f}%</span></td></tr>'
        html_table += '</table>'
        st.markdown(html_table, unsafe_allow_html=True)

        # 3. グラフ
        st.markdown("<br>", unsafe_allow_html=True)
        cg1, cg2 = st.columns(2)
        compare_df = pd.concat([g_a.assign(期間=month_a), g_b.assign(期間=month_b)]).reset_index()
        with cg1:
            st.subheader("タイプ別 広告費比較")
            st.plotly_chart(px.bar(compare_df, x='タイプ', y='広告費', color='期間', barmode='group', color_discrete_map={month_a:'#37475A', month_b:'#A9A9A9'}).update_layout(plot_bgcolor='white', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)), use_container_width=True)
        with cg2:
            st.subheader("タイプ別 実績比較")
            st.plotly_chart(px.bar(compare_df, x='タイプ', y='広告売上', color='期間', barmode='group', color_discrete_map={month_a:'#FF9900', month_b:'#232F3E'}).update_layout(plot_bgcolor='white', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)), use_container_width=True)

    st.markdown("---")
    st.subheader("月別 広告総合実績推移 (All Metrics)")
    trend = df_ads.groupby('年月').sum(numeric_only=True).sort_index(ascending=False).reset_index()
    st.dataframe(trend.style.format({'インプレッション':'{:,.0f}','クリック数':'{:,.0f}','広告費':'¥{:,.0f}','注文':'{:,.0f}','広告売上':'¥{:,.0f}'}), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
