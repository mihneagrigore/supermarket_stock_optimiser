import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np


def generate_product_charts(inventory_df, prediction_data):
    """
    Generate 4 Plotly charts for a single product.
    
    Args:
        inventory_df: DataFrame with Date, Inventory_Level, Units_Sold, Price, Discount, Holiday_Promotion
        prediction_data: Dict with forecast_horizon_demand, reorder_point_units, current_inventory, etc.
        
    Returns:
        Dict with keys: 'sales', 'inventory', 'forecast', 'discount' containing HTML strings
    """
    charts = {}
    
    # Chart 1: Sales Velocity with 7-day moving average
    charts['sales'] = create_sales_velocity_chart(inventory_df)
    
    # Chart 2: Inventory Level with reorder point
    charts['inventory'] = create_inventory_level_chart(inventory_df, prediction_data)
    
    # Chart 3: Forecast Accuracy (last 7 days actual vs predicted)
    charts['forecast'] = create_forecast_comparison_chart(inventory_df, prediction_data)
    
    # Chart 4: Price-Discount Impact
    charts['discount'] = create_discount_impact_chart(inventory_df)
    
    return charts


def create_sales_velocity_chart(df):
    """Create line chart showing Units_Sold over time with 7-day moving average."""
    if df.empty:
        return "<div class='chart-placeholder'>No sales data available</div>"
    
    # Calculate 7-day moving average
    df = df.copy()
    df['MA_7'] = df['Units_Sold'].rolling(window=7, min_periods=1).mean()
    
    fig = go.Figure()
    
    # Actual sales
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Units_Sold'],
        mode='lines',
        name='Daily Sales',
        line=dict(color='#3b82f6', width=1.5),
        opacity=0.6
    ))
    
    # 7-day moving average
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['MA_7'],
        mode='lines',
        name='7-Day Average',
        line=dict(color='#ef4444', width=2.5)
    ))
    
    fig.update_layout(
        title='Sales Velocity Trend',
        xaxis_title='Date',
        yaxis_title='Units Sold',
        hovermode='x unified',
        template='plotly_white',
        height=350,
        margin=dict(l=50, r=30, t=50, b=50)
    )
    
    return fig.to_html(full_html=False, include_plotlyjs=False, config={'displayModeBar': False})


def create_inventory_level_chart(df, prediction_data):
    """Create area chart showing Inventory_Level with reorder point line."""
    if df.empty:
        return "<div class='chart-placeholder'>No inventory data available</div>"
    
    reorder_point = prediction_data.get('reorder_point_units', 0)
    
    fig = go.Figure()
    
    # Inventory level area
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Inventory_Level'],
        mode='lines',
        name='Inventory Level',
        fill='tozeroy',
        line=dict(color='#10b981', width=2),
        fillcolor='rgba(16, 185, 129, 0.2)'
    ))
    
    # Reorder point line
    fig.add_trace(go.Scatter(
        x=[df['Date'].min(), df['Date'].max()],
        y=[reorder_point, reorder_point],
        mode='lines',
        name='Reorder Point',
        line=dict(color='#f59e0b', width=2, dash='dash')
    ))
    
    fig.update_layout(
        title='Inventory Level Over Time',
        xaxis_title='Date',
        yaxis_title='Units in Stock',
        hovermode='x unified',
        template='plotly_white',
        height=350,
        margin=dict(l=50, r=30, t=50, b=50)
    )
    
    return fig.to_html(full_html=False, include_plotlyjs=False, config={'displayModeBar': False})


def create_forecast_comparison_chart(df, prediction_data):
    """Create line chart comparing last 7 days actual vs ML prediction."""
    if df.empty or len(df) < 7:
        return "<div class='chart-placeholder'>Insufficient data for forecast comparison</div>"
    
    # Get last 7 days of actual data
    last_7_days = df.tail(7).copy()
    actual_sum = last_7_days['Units_Sold'].sum()
    
    # Get forecast from prediction data
    forecast_total = prediction_data.get('forecast_horizon_demand', 0)
    
    # Calculate MAPE (Mean Absolute Percentage Error)
    mape = abs(actual_sum - forecast_total) / actual_sum * 100 if actual_sum > 0 else 0
    
    # Create daily forecast (distribute evenly)
    forecast_daily = forecast_total / 7
    
    fig = go.Figure()
    
    # Actual sales
    fig.add_trace(go.Scatter(
        x=last_7_days['Date'],
        y=last_7_days['Units_Sold'],
        mode='lines+markers',
        name='Actual',
        line=dict(color='#3b82f6', width=2.5),
        marker=dict(size=8)
    ))
    
    # Forecast line
    fig.add_trace(go.Scatter(
        x=last_7_days['Date'],
        y=[forecast_daily] * 7,
        mode='lines',
        name='Forecast',
        line=dict(color='#8b5cf6', width=2.5, dash='dash')
    ))
    
    fig.update_layout(
        title=f'Forecast Accuracy (MAPE: {mape:.1f}%)',
        xaxis_title='Date',
        yaxis_title='Units Sold',
        hovermode='x unified',
        template='plotly_white',
        height=350,
        margin=dict(l=50, r=30, t=50, b=50)
    )
    
    return fig.to_html(full_html=False, include_plotlyjs=False, config={'displayModeBar': False})


def create_discount_impact_chart(df):
    """Create scatter plot showing relationship between Discount and Units_Sold."""
    if df.empty:
        return "<div class='chart-placeholder'>No discount data available</div>"
    
    df = df.copy()
    
    # Separate by promotion status
    promo_yes = df[df['Holiday_Promotion'] == 1]
    promo_no = df[df['Holiday_Promotion'] == 0]
    
    fig = go.Figure()
    
    # No promotion
    fig.add_trace(go.Scatter(
        x=promo_no['Discount'],
        y=promo_no['Units_Sold'],
        mode='markers',
        name='Regular',
        marker=dict(color='#6b7280', size=8, opacity=0.6)
    ))
    
    # With promotion
    if not promo_yes.empty:
        fig.add_trace(go.Scatter(
            x=promo_yes['Discount'],
            y=promo_yes['Units_Sold'],
            mode='markers',
            name='Holiday/Promotion',
            marker=dict(color='#f59e0b', size=8, opacity=0.8)
        ))
    
    fig.update_layout(
        title='Discount Impact on Sales',
        xaxis_title='Discount (%)',
        yaxis_title='Units Sold',
        hovermode='closest',
        template='plotly_white',
        height=350,
        margin=dict(l=50, r=30, t=50, b=50)
    )
    
    return fig.to_html(full_html=False, include_plotlyjs=False, config={'displayModeBar': False})
