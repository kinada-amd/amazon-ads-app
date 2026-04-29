import streamlit as st
import pandas as pd
import io
import requests
import plotly.graph_objects as go
import plotly.express as px

# 1. ページ設定
st.set_page_config(page_title="Amazon Ads Analytics", layout="wide")

# 2. デザイン修正
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
.st-emotion-cache-zy6yx3 {padding-top: 1rem !important;padding-bottom: 3rem !important;}
.st-emotion-cache-qmp9ai {visibility: visible;}
.st-emotion-cache-1r1cntt {padding-top: 1rem;}
.st-emotion-cache-10p9htt {display: none;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    return io.BytesIO(res.content)

# --- 比較テーブル用カラーリング関数 ---
def style_comparison(val):
    if isinstance(val, str) and '(' in val:
        # ( ) 内の数値と記号を取り出す
        diff_part = val.split('(')[-1].replace(')', '').replace('¥', '').replace('%', '').replace(',', '')
        try:
            diff_val = float(diff_part)
            # 基本はプラスが緑、マイナスが赤
            if diff_val > 0:
                return 'background-color: #e6f4ea; color: #1e7e34; font-weight: bold; border-radius: 4px;'
            elif diff_val < 0:
                return 'background-color: #fce8e6; color: #d93025; font-weight: bold; border-radius: 4px;'
        except:
            pass
    return ''

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
        
        type_summary = df_month.groupby('タイプ').agg({'インプレッション':'sum','クリック数':'sum','広告費':'sum','注文':'sum','広告売上':'sum'}).reset_index()
        st.subheader(f"{target_month} タイプ別実績詳細")
        for col, calc in [('CTR', 'クリック数/インプレッション*100'), ('CPC', '広告費/クリック数'), ('ROAS', '広告売上/広告費*100'), ('CV率', '注文/クリック数*100'), ('ACOS', '広告費/広告売上*100')]:
            type_summary[col] = eval(f"(type_summary['{calc.split('/')[0]}'] / type_summary['{calc.split('/')[1].split('*')[0]}'] * {calc.split('*')[1] if '*' in calc else '1'})").fillna(0)
        
        st.dataframe(type_summary.style.format({'インプレッション':'{:,.0f}','クリック数':'{:,.0f}','CTR':'{:.2f}%','CPC':'¥{:,.0f}','広告費':'¥{:,.0f}','注文':'{:,.0f}','広告売上':'¥{:,.0f}','ROAS':'{:,.0f}%','CV率':'{:.1f}%','ACOS':'{:.1f}%'}), use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("タイプ別 広告費比率")
            fig_pie = px.pie(type_summary, values='広告費', names='タイプ', color_discrete_sequence=['#232F3E', '#FF9900', '#37475A', '#A9A9A9'], hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
            st.subheader("タイプ別 実績")
            fig_bar = go.Figure(go.Bar(x=type_summary['タイプ'], y=type_summary['広告売上'], marker_color='#FF9900', text=type_summary['広告売上'].apply(lambda x: f"¥{x:,.0f}"), textposition='outside'))
            fig_bar.update_layout(plot_bgcolor='white', font_family="Inter", xaxis=dict(showline=True, linecolor='#d5d9d9'), yaxis=dict(showgrid=True, gridcolor='#F3F3F3'))
            st.plotly_chart(fig_bar, use_container_width=True)

    else:
        month_a = st.sidebar.selectbox("比較期間 A", all_months, index=0)
        month_b = st.sidebar.selectbox("比較期間 B", all_months, index=1 if len(all_months) > 1 else 0)
        st.title(f"Comparison: {month_a} vs {month_b}")
        df_a, df_b = df_ads[df_ads['年月'] == month_a].copy(), df_ads[df_ads['年月'] == month_b].copy()
        
        sp_a, sa_a = df_a['広告費'].sum(), df_a['広告売上'].sum()
        sp_b, sa_b = df_b['広告費'].sum(), df_b['広告売上'].sum()
        roas_a, roas_b = (sa_a/sp_a*100 if sp_a>0 else 0), (sa_b/sp_b*100 if sp_b>0 else 0)
        acos_a, acos_b = (sp_a/sa_a*100 if sa_a>0 else 0), (sp_b/sa_b*100 if sa_b>0 else 0)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("総広告費", f"¥{int(sp_a):,}", delta=f"¥{int(sp_a - sp_b):,}", delta_color="inverse")
        m2.metric("総広告売上", f"¥{int(sa_a):,}", delta=f"¥{int(sa_a - sa_b):,}")
        m3.metric("ROAS", f"{roas_a:.0f}%", delta=f"{roas_a - roas_b:.1f}%")
        m4.metric("ACOS", f"{acos_a:.1f}%", delta=f"{acos_a - acos_b:.1f}%", delta_color="inverse")
        
        st.subheader("広告総合実績比較")
        sum_a_all = df_a.agg({'インプレッション':'sum','クリック数':'sum','広告費':'sum','注文':'sum','広告売上':'sum'})
        sum_b_all = df_b.agg({'インプレッション':'sum','クリック数':'sum','広告費':'sum','注文':'sum','広告売上':'sum'})
        comp_summary = pd.DataFrame([sum_a_all, sum_b_all], index=[month_a, month_b]).reset_index().rename(columns={'index': '年月'})
        comp_summary['CTR'] = (comp_summary['クリック数']/comp_summary['インプレッション']*100).fillna(0)
        comp_summary['CPC'] = (comp_summary['広告費']/comp_summary['クリック数']).fillna(0)
        comp_summary['ROAS'] = (comp_summary['広告売上']/comp_summary['広告費']*100).fillna(0)
        comp_summary['CV率'] = (comp_summary['注文']/comp_summary['クリック数']*100).fillna(0)
        comp_summary['ACOS'] = (comp_summary['広告費']/comp_summary['広告売上']*100).fillna(0)
        st.dataframe(comp_summary.style.format({'インプレッション':'{:,.0f}','クリック数':'{:,.0f}','CTR':'{:.2f}%','CPC':'¥{:,.0f}','広告費':'¥{:,.0f}','注文':'{:,.0f}','広告売上':'¥{:,.0f}','ROAS':'{:,.0f}%','CV率':'{:.1f}%','ACOS':'{:.1f}%'}), use_container_width=True, hide_index=True)

        st.subheader(f"タイプ別実績比較 ({month_a} vs {month_b})")
        def get_sum(df): return df.groupby('タイプ').agg({'インプレッション':'sum','クリック数':'sum','広告費':'sum','注文':'sum','広告売上':'sum'})
        s_a, s_b = get_sum(df_a), get_sum(df_b)
        diff = s_a - s_b
        compare_list = []
        for t in s_a.index:
            row = {'タイプ': t}
            for col in ['インプレッション', 'クリック数', '広告費', '注文', '広告売上']:
                pre = "¥" if "売上" in col or "費" in col else ""
                row[col] = f"{pre}{s_a.loc[t, col]:,.0f} ({'+' if diff.loc[t, col]>=0 else ''}{pre}{diff.loc[t, col]:,.0f})"
            ra, rb = (s_a.loc[t, '広告売上']/s_a.loc[t, '広告費']*100 if s_a.loc[t, '広告費']>0 else 0), (s_b.loc[t, '広告売上']/s_b.loc[t, '広告費']*100 if s_b.loc[t, '広告費']>0 else 0)
            row['ROAS'] = f"{ra:.0f}% ({ra - rb:+.1f}%)"
            compare_list.append(row)
        
        # カラーリング適用
        df_compare = pd.DataFrame(compare_list)
        st.dataframe(df_compare.style.applymap(style_comparison, subset=['インプレッション', 'クリック数', '広告費', '注文', '広告売上', 'ROAS']), use_container_width=True, hide_index=True)

        cg1, cg2 = st.columns(2)
        sum_a_g, sum_b_g = s_a.reset_index(), s_b.reset_index()
        sum_a_g['期間'], sum_b_g['期間'] = month_a, month_b
        cdf = pd.concat([sum_a_g, sum_b_g])
        with cg1:
            st.subheader("タイプ別 広告費比較")
            fig_sp = px.bar(cdf, x='タイプ', y='広告費', color='期間', barmode='group', color_discrete_map={month_a: '#37475A', month_b: '#A9A9A9'}, text_auto=',.0f')
            fig_sp.update_layout(plot_bgcolor='white', font_family="Inter", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_sp, use_container_width=True)
        with cg2:
            st.subheader("タイプ別 実績比較")
            fig_sa = px.bar(cdf, x='タイプ', y='広告売上', color='期間', barmode='group', color_discrete_map={month_a: '#FF9900', month_b: '#232F3E'}, text_auto=',.0f')
            fig_sa.update_layout(plot_bgcolor='white', font_family="Inter", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_sa, use_container_width=True)

    st.markdown("---")
    st.subheader("月別 広告総合実績推移 (All Metrics)")
    trend = df_ads.groupby('年月').agg({'インプレッション':'sum','クリック数':'sum','広告費':'sum','注文':'sum','広告売上':'sum'}).sort_index(ascending=False).reset_index()
    trend['CTR'] = (trend['クリック数']/trend['インプレッション']*100).fillna(0)
    trend['CPC'] = (trend['広告費']/trend['クリック数']).fillna(0)
    trend['ROAS'] = (trend['広告売上']/trend['広告費']*100).fillna(0)
    trend['CV率'] = (trend['注文']/trend['クリック数']*100).fillna(0)
    trend['ACOS'] = (trend['広告費']/trend['広告売上']*100).fillna(0)
    st.dataframe(trend[['年月', 'インプレッション', 'クリック数', 'CTR', 'CPC', '広告費', '注文', '広告売上', 'ROAS', 'CV率', 'ACOS']].style.format({'インプレッション':'{:,.0f}','クリック数':'{:,.0f}','CTR':'{:.2f}%','CPC':'¥{:,.0f}','広告費':'¥{:,.0f}','注文':'{:,.0f}','広告売上':'¥{:,.0f}','ROAS':'{:,.0f}%','CV率':'{:.1f}%','ACOS':'{:.1f}%'}), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
