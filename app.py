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

try:
    df_ads = pd.read_excel(load_data("https://gigaplus.makeshop.jp/aimedia/data/ads.xlsx"))
    df_ads.columns = df_ads.columns.str.strip()
    if '売上' in df_ads.columns and '広告売上' not in df_ads.columns:
        df_ads = df_ads.rename(columns={'売上': '広告売上'})

    df_ads['日付_dt'] = pd.to_datetime(df_ads['日付'], format='%Y年%m月', errors='coerce')
    df_ads['年月'] = df_ads['日付_dt'].dt.strftime('%Y-%m')
    
    # 年度計算 (4月始まり)
    df_ads['年度'] = df_ads['日付_dt'].apply(lambda x: f"{(x.year - 1) if x.month < 4 else x.year}年度")

    # --- サイドバー ---
    st.sidebar.markdown('<h2>Amazon Ads Analytics</h2>', unsafe_allow_html=True)
    st.sidebar.link_button("売上実績へ切り替える", "https://amazon-sales-app.streamlit.app/")
    st.sidebar.markdown("---")
    
    view_mode = st.sidebar.radio("表示モードを選択", ["通常モード", "比較モード"], index=0)
    
    if view_mode == "通常モード":
        # 表示単位の選択を追加
        unit_mode = st.sidebar.radio("表示単位を選択", ["月単位", "年度単位"], index=0)
        
        if unit_mode == "月単位":
            all_options = sorted(df_ads['年月'].dropna().unique(), reverse=True)
            target_period = st.sidebar.selectbox("表示する期間を選択", all_options, index=0)
            df_filtered = df_ads[df_ads['年月'] == target_period].copy()
            title_text = f"Advertising Summary: {target_period}"
        else:
            all_options = sorted(df_ads['年度'].dropna().unique(), reverse=True)
            target_period = st.sidebar.selectbox("表示する期間を選択", all_options, index=0)
            df_filtered = df_ads[df_ads['年度'] == target_period].copy()
            title_text = f"Advertising Summary: {target_period}"

        st.title(title_text)
        
        m1, m2, m3, m4 = st.columns(4)
        total_sp = df_filtered['広告費'].sum()
        total_sa = df_filtered['広告売上'].sum()
        m1.metric("総広告費", f"¥{int(total_sp):,}")
        m2.metric("総広告売上", f"¥{int(total_sa):,}")
        m3.metric("ROAS", f"{(total_sa/total_sp*100):.0f}%" if total_sp > 0 else "0%")
        m4.metric("ACOS", f"{(total_sp/total_sa*100):.1f}%" if total_sa > 0 else "0.0%")
        
        type_summary = df_filtered.groupby('タイプ').agg({
            'インプレッション': 'sum', 'クリック数': 'sum', '広告費': 'sum', '注文': 'sum', '広告売上': 'sum'
        }).reset_index()

        # 通常モード：テーブル
        st.subheader(f"{target_period} タイプ別実績詳細")
        type_summary['CTR'] = (type_summary['クリック数'] / type_summary['インプレッション'] * 100).fillna(0)
        type_summary['CPC'] = (type_summary['広告費'] / type_summary['クリック数']).fillna(0)
        type_summary['ROAS'] = (type_summary['広告売上'] / type_summary['広告費'] * 100).fillna(0)
        type_summary['CV率'] = (type_summary['注文'] / type_summary['クリック数'] * 100).fillna(0)
        type_summary['ACOS'] = (type_summary['広告費'] / type_summary['広告売上'] * 100).fillna(0)
        st.dataframe(
            type_summary[['タイプ', 'インプレッション', 'クリック数', 'CTR', 'CPC', '広告費', '注文', '広告売上', 'ROAS', 'CV率', 'ACOS']].style.format({
                'インプレッション': '{:,.0f}', 'クリック数': '{:,.0f}', 'CTR': '{:.2f}%',
                'CPC': '¥{:,.0f}', '広告費': '¥{:,.0f}', '注文': '{:,.0f}',
                '広告売上': '¥{:,.0f}', 'ROAS': '{:,.0f}%', 'CV率': '{:.1f}%', 'ACOS': '{:.1f}%'
            }), use_container_width=True, hide_index=True
        )

        # 通常モード：グラフ
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("タイプ別 広告費比率")
            amazon_colors = ['#232F3E', '#FF9900', '#37475A', '#A9A9A9']
            fig_pie = px.pie(type_summary, values='広告費', names='タイプ', color_discrete_sequence=amazon_colors, hole=0.4)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#FFFFFF', width=2)), insidetextfont=dict(size=16))
            fig_pie.update_layout(hoverlabel=dict(font_size=20), font_family="Inter")
            st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
            st.subheader("タイプ別 実績")
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                x=type_summary['タイプ'], y=type_summary['広告売上'], marker_color='#FF9900',
                text=type_summary['広告売上'].apply(lambda x: f"¥{x:,.0f}"), textposition='outside',
                textfont=dict(size=14, color='#131921', family="Inter"), hovertemplate='売上: ¥%{y:,.0f}<extra></extra>'
            ))
            fig_bar.update_layout(plot_bgcolor='white', margin=dict(t=40, b=20), hoverlabel=dict(font_size=20), font_family="Inter",
                                  xaxis=dict(showline=True, linecolor='#d5d9d9'), yaxis=dict(showgrid=True, gridcolor='#F3F3F3', tickformat=','))
            st.plotly_chart(fig_bar, use_container_width=True)

    else:
        all_months = sorted(df_ads['年月'].dropna().unique(), reverse=True)
        month_a = st.sidebar.selectbox("比較期間 A", all_months, index=0)
        month_b = st.sidebar.selectbox("比較期間 B", all_months, index=1 if len(all_months) > 1 else 0)
        
        st.title(f"Comparison: {month_a} vs {month_b}")
        df_a = df_ads[df_ads['年月'] == month_a].copy()
        df_b = df_ads[df_ads['年月'] == month_b].copy()
        
        sp_a, sa_a = df_a['広告費'].sum(), df_a['広告売上'].sum()
        sp_b, sa_b = df_b['広告費'].sum(), df_b['広告売上'].sum()
        roas_a = (sa_a / sp_a * 100) if sp_a > 0 else 0
        roas_b = (sa_b / sp_b * 100) if sp_b > 0 else 0
        acos_a = (sp_a / sa_a * 100) if sa_a > 0 else 0
        acos_b = (sp_b / sa_b * 100) if sa_b > 0 else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("総広告費", f"¥{int(sp_a):,}", delta=f"¥{int(sp_a - sp_b):,}", delta_color="inverse")
        m2.metric("総広告売上", f"¥{int(sa_a):,}", delta=f"¥{int(sa_a - sa_b):,}")
        m3.metric("ROAS", f"{roas_a:.0f}%", delta=f"{roas_a - roas_b:.1f}%")
        m4.metric("ACOS", f"{acos_a:.1f}%", delta=f"{acos_a - acos_b:.1f}%", delta_color="inverse")
        
        # 比較モード 1: 広告総合実績テーブル
        st.subheader("広告総合実績比較")
        summary_a = df_a.agg({'インプレッション':'sum','クリック数':'sum','広告費':'sum','注文':'sum','広告売上':'sum'})
        summary_b = df_b.agg({'インプレッション':'sum','クリック数':'sum','広告費':'sum','注文':'sum','広告売上':'sum'})
        comp_summary = pd.DataFrame([summary_a, summary_b], index=[month_a, month_b]).reset_index().rename(columns={'index': '年月'})
        comp_summary['CTR'] = (comp_summary['クリック数'] / comp_summary['インプレッション'] * 100).fillna(0)
        comp_summary['CPC'] = (comp_summary['広告費'] / comp_summary['クリック数']).fillna(0)
        comp_summary['ROAS'] = (comp_summary['広告売上'] / comp_summary['広告費'] * 100).fillna(0)
        comp_summary['CV率'] = (comp_summary['注文'] / comp_summary['クリック数'] * 100).fillna(0)
        comp_summary['ACOS'] = (comp_summary['広告費'] / comp_summary['広告売上'] * 100).fillna(0)
        st.dataframe(
            comp_summary[['年月', 'インプレッション', 'クリック数', 'CTR', 'CPC', '広告費', '注文', '広告売上', 'ROAS', 'CV率', 'ACOS']].style.format({
                'インプレッション': '{:,.0f}', 'クリック数': '{:,.0f}', 'CTR': '{:.2f}%',
                'CPC': '¥{:,.0f}', '広告費': '¥{:,.0f}', '注文': '{:,.0f}',
                '広告売上': '¥{:,.0f}', 'ROAS': '{:,.0f}%', 'CV率': '{:.1f}%', 'ACOS': '{:.1f}%'
            }), use_container_width=True, hide_index=True
        )

        # 比較モード 2: タイプ別実績比較テーブル
        st.subheader(f"タイプ別実績比較 ({month_a} vs {month_b})")
        def get_summary(df):
            return df.groupby('タイプ').agg({'インプレッション':'sum','クリック数':'sum','広告費':'sum','注文':'sum','広告売上':'sum'})
        sum_a, sum_b = get_summary(df_a), get_summary(df_b)
        diff = sum_a - sum_b
        compare_display_list = []
        for t in sum_a.index:
            row = {'タイプ': t}
            for col in ['インプレッション', 'クリック数', '広告費', '注文', '広告売上']:
                val_a = sum_a.loc[t, col]
                val_diff = diff.loc[t, col]
                prefix = "¥" if "売上" in col or "費" in col else ""
                row[col] = f"{prefix}{val_a:,.0f} ({'+' if val_diff>=0 else ''}{prefix}{val_diff:,.0f})"
            ra = (sum_a.loc[t, '広告売上'] / sum_a.loc[t, '広告費'] * 100) if sum_a.loc[t, '広告費'] > 0 else 0
            rb = (sum_b.loc[t, '広告売上'] / sum_b.loc[t, '広告費'] * 100) if sum_b.loc[t, '広告費'] > 0 else 0
            row['ROAS'] = f"{ra:.0f}% ({ra - rb:+.1f}%)"
            compare_display_list.append(row)
        st.dataframe(pd.DataFrame(compare_display_list), use_container_width=True, hide_index=True)

        # 比較モード 3: グラフ
        cg1, cg2 = st.columns(2)
        sum_a_g = sum_a.reset_index()
        sum_b_g = sum_b.reset_index()
        sum_a_g['期間'], sum_b_g['期間'] = month_a, month_b
        compare_df = pd.concat([sum_a_g, sum_b_g])
        with cg1:
            st.subheader("タイプ別 広告費比較")
            fig_sp = px.bar(compare_df, x='タイプ', y='広告費', color='期間', barmode='group',
                            color_discrete_map={month_a: '#37475A', month_b: '#A9A9A9'}, text_auto=',.0f')
            fig_sp.update_layout(plot_bgcolor='white', font_family="Inter", margin=dict(t=40, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_sp, use_container_width=True)
        with cg2:
            st.subheader("タイプ別 実績比較")
            fig_sa = px.bar(compare_df, x='タイプ', y='広告売上', color='期間', barmode='group',
                            color_discrete_map={month_a: '#FF9900', month_b: '#232F3E'}, text_auto=',.0f')
            fig_sa.update_layout(plot_bgcolor='white', font_family="Inter", margin=dict(t=40, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_sa, use_container_width=True)

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
