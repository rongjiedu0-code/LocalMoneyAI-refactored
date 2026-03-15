"""
报表页面：图表展示、数据导出。
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
from utils.i18n import get_text

class ReportPage:
    def __init__(self, tx_service):
        self.tx_service = tx_service
    
    def render(self):
        st.header(get_text("report_header"))
        st.caption(get_text("report_caption"))
        
        # 时间范围选择
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(get_text("start_date"), value=None)
        with col2:
            end_date = st.date_input(get_text("end_date"), value=None)
        
        start_str = start_date.strftime("%Y-%m-%d") if start_date else None
        end_str = end_date.strftime("%Y-%m-%d") if end_date else None
        
        try:
            stats = self.tx_service.get_stats(start_date=start_str, end_date=end_str)
            
            # 空数据检查
            if not stats or (stats["total_income"] == 0 and stats["total_expense"] == 0):
                st.info(get_text("no_data"))
                return
            
            # 数据清洗与异常保护
            stats["monthly_trend"] = stats.get("monthly_trend", [])
            stats["by_category"] = stats.get("by_category", [])
            
            # 确保数据完整性
            for item in stats["monthly_trend"]:
                item["income"] = item.get("income", 0) or 0
                item["expense"] = item.get("expense", 0) or 0
                item["net"] = item.get("net", 0) or 0
            
            for item in stats["by_category"]:
                item["income"] = item.get("income", 0) or 0
                item["expense"] = item.get("expense", 0) or 0
                item["net"] = item.get("net", 0) or 0
            
            # 关键指标卡片
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(get_text("total_income"), f"¥{stats['total_income']:,.2f}")
            with col2:
                st.metric(get_text("total_expense"), f"¥{stats['total_expense']:,.2f}")
            with col3:
                st.metric(get_text("net_balance"), f"¥{stats['net']:,.2f}", 
                         delta=f"{get_text('positive') if stats['net']>=0 else get_text('negative')}")
            
            # 财务洞察指标
            st.markdown("#### 📊 财务洞察")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # 净储蓄率
                savings_rate = (stats['net'] / stats['total_income'] * 100) if stats['total_income'] > 0 else 0
                st.metric(
                    get_text("savings_rate"),
                    f"{savings_rate:.1f}%",
                    delta=f"{get_text('good') if savings_rate >= 20 else get_text('needs_attention')}"
                )
            
            with col2:
                # 支出收入比
                expense_ratio = (stats['total_expense'] / stats['total_income'] * 100) if stats['total_income'] > 0 else 0
                st.metric(
                    get_text("expense_ratio"),
                    f"{expense_ratio:.1f}%",
                    delta=f"{get_text('healthy') if expense_ratio <= 70 else get_text('high')}"
                )
            
            with col3:
                # 月度环比
                monthly_trend = stats.get("monthly_trend", [])
                if len(monthly_trend) >= 2:
                    current_month = monthly_trend[-1]["net"]
                    prev_month = monthly_trend[-2]["net"]
                    mom_growth = ((current_month - prev_month) / abs(prev_month) * 100) if prev_month != 0 else 0
                    st.metric(
                        get_text("mom_growth"),
                        f"{mom_growth:+.1f}%",
                        delta_color="normal"
                    )
                else:
                    st.metric(get_text("mom_growth"), "N/A")
            
            with col4:
                # 预警提示
                if len(monthly_trend) >= 2:
                    current_month = monthly_trend[-1]["net"]
                    prev_month = monthly_trend[-2]["net"]
                    if prev_month > 0 and current_month < prev_month * 0.8:  # 下降超过 20%
                        st.error("⚠️ 净值环比下降超过 20%")
                    elif current_month < 0:
                        st.warning("⚠️ 本月净值为负")
                    else:
                        st.success("✅ 财务状况良好")
            
            st.markdown("---")
            
            # 统一图表配置
            chart_config = {
                'locale': 'zh-CN' if st.session_state.get('language', 'zh') == 'zh' else 'en',
                'displaylogo': False,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'modeBarButtonsToAdd': ['zoom2d', 'pan2d', 'resetScale2d', 'toImage'],
                'displayModeBar': True,
                'responsive': True
            }

            # 图表1：月度趋势（双轴）
            if stats["monthly_trend"]:
                st.subheader(get_text("monthly_trend"))
                df_trend = pd.DataFrame(stats["monthly_trend"]).fillna(0)
                df_trend["month"] = pd.to_datetime(df_trend["month"], errors='coerce')
                df_trend = df_trend.sort_values("month")
                
                # 使用 plotly.graph_objects 实现双轴
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # 收入柱状图（绿色）
                fig.add_trace(
                    go.Bar(
                        x=df_trend["month"],
                        y=df_trend["income"],
                        name=get_text("income"),
                        marker_color='#2ecc71',
                        hovertemplate=f"<b>{get_text('chart_hover_month')}</b>: %{{x|%Y-%m}}<br>" +
                                      f"<b>{get_text('income')}</b>: ¥%{{y:,.2f}}<extra></extra>"
                    ),
                    secondary_y=False
                )
                
                # 支出柱状图（红色）
                fig.add_trace(
                    go.Bar(
                        x=df_trend["month"],
                        y=df_trend["expense"],
                        name=get_text("expense"),
                        marker_color='#e74c3c',
                        hovertemplate=f"<b>{get_text('chart_hover_month')}</b>: %{{x|%Y-%m}}<br>" +
                                      f"<b>{get_text('expense')}</b>: ¥%{{y:,.2f}}<extra></extra>"
                    ),
                    secondary_y=False
                )
                
                # 净值折线图（蓝色，右轴）
                fig.add_trace(
                    go.Scatter(
                        x=df_trend["month"],
                        y=df_trend["net"],
                        name=get_text("net_balance"),
                        mode='lines+markers',
                        line=dict(color='#3498db', width=2),
                        marker=dict(size=8),
                        hovertemplate=f"<b>{get_text('chart_hover_month')}</b>: %{{x|%Y-%m}}<br>" +
                                      f"<b>{get_text('net_balance')}</b>: ¥%{{y:,.2f}}<extra></extra>"
                    ),
                    secondary_y=True
                )
                
                # 零线
                fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
                
                # 轴标签
                fig.update_xaxes(title_text=get_text("month_axis"), tickformat="%Y-%m")
                fig.update_yaxes(title_text=get_text("amount_axis"), secondary_y=False)
                fig.update_yaxes(title_text=get_text("net_balance"), secondary_y=True)
                
                # 汉化图例
                fig.update_layout(
                    title=get_text("trend_title"),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True, config=chart_config)
            
            # 图表2：类别分布（饼图）
            if stats["by_category"]:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(get_text("cat_dist"))
                    df_cat = pd.DataFrame(stats["by_category"]).fillna(0)
                    df_cat = df_cat[df_cat["expense"] > 0]  # 只看支出
                    df_cat = df_cat.sort_values("expense", ascending=False)
                    
                    if len(df_cat) > 0:
                        fig = px.pie(df_cat, names="category", values="expense",
                                    title=get_text("cat_pie_title"))
                        fig.update_traces(
                            textinfo='percent+label',
                            hovertemplate=f"<b>{get_text('chart_hover_cat')}</b>: %{{label}}<br>" +
                                          f"<b>{get_text('chart_hover_amount')}</b>: ¥%{{value:,.2f}}<br>" +
                                          f"<b>{get_text('chart_hover_ratio')}</b>: %{{percent}}<extra></extra>"
                        )
                        st.plotly_chart(fig, use_container_width=True, config=chart_config)
                    else:
                        st.info(get_text("no_data"))
                
                with col2:
                    st.subheader(get_text("cat_detail_table"))
                    df_cat_display = df_cat.copy()
                    df_cat_display[get_text("dist_ratio")] = df_cat_display["expense"] / df_cat_display["expense"].sum() * 100
                    df_cat_display[get_text("field_amount")] = df_cat_display["expense"].apply(lambda x: f"¥{x:,.2f}")
                    df_cat_display[get_text("dist_ratio")] = df_cat_display[get_text("dist_ratio")].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(
                        df_cat_display[["category", get_text("field_amount"), get_text("dist_ratio")]].rename(columns={"category": get_text("field_category")}),
                        use_container_width=True,
                        hide_index=True
                    )
            
            # 原始数据导出
            st.markdown("---")
            st.subheader(get_text("export_all"))
            if st.button(get_text("export_all_btn")):
                # 重新查询所有数据（无分页）
                all_tx = self.tx_service.list_transactions(page=1, page_size=10000)["data"]
                df_export = pd.DataFrame(all_tx)
                csv = df_export.to_csv(index=False, encoding="utf-8-sig")
                
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label=get_text("download_label", filename=f"transactions_{ts}.csv"),
                    data=csv,
                    file_name=f"transactions_{ts}.csv",
                    mime="text/csv"
                )
                
        except Exception as e:
            st.error(f"{get_text('error')}: {e}")
            import logging
            logging.error(f"报表渲染失败: {e}", exc_info=True)