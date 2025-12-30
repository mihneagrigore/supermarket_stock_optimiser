"""
Analytics module for generating Plotly charts for dashboard.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


def generate_product_charts(product_id: str, prediction: dict, historical_data: list) -> dict:
    """
    Generate 4 Plotly charts for a specific product.
    
    Args:
        product_id: Product ID string (e.g., "P0001")
        prediction: Prediction dict with forecast_horizon_demand, current_inventory, etc.
        historical_data: List of dicts with Date, Units_Sold, Inventory_Level, Price, etc.
    
    Returns:
        dict with keys: inventory_timeline, sales_forecast, reorder_gauge, daily_sales
        Each value is an HTML string of the Plotly chart.
    """
    charts = {}
    
    # Convert historical data to DataFrame
    if historical_data:
        df = pd.DataFrame(historical_data)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
    else:
        df = pd.DataFrame()
    
    # Chart 1: Inventory Timeline with Reorder Point
    charts['inventory_timeline'] = _create_inventory_timeline(df, prediction, product_id)
    
    # Chart 2: Sales vs Forecast Comparison
    charts['sales_forecast'] = _create_sales_forecast_chart(df, prediction, product_id)
    
    # Chart 3: Reorder Status Gauge
    charts['reorder_gauge'] = _create_reorder_gauge(prediction, product_id)
    
    # Chart 4: Daily Sales Bar Chart (last 30 days)
    charts['daily_sales'] = _create_daily_sales_chart(df, product_id)
    
    return charts


def _create_inventory_timeline(df: pd.DataFrame, prediction: dict, product_id: str) -> str:
    """Create inventory level timeline with reorder point line."""
    fig = go.Figure()
    
    if not df.empty and 'Inventory_Level' in df.columns:
        # Inventory level line
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['Inventory_Level'],
            mode='lines',
            name='Inventory Level',
            line=dict(color='#2563eb', width=2),
            fill='tozeroy',
            fillcolor='rgba(37, 99, 235, 0.1)'
        ))
        
        # Reorder point horizontal line
        if prediction and 'reorder_point_units' in prediction:
            reorder_point = prediction['reorder_point_units']
            fig.add_hline(
                y=reorder_point,
                line_dash="dash",
                line_color="#dc2626",
                annotation_text=f"Reorder Point: {reorder_point:.0f}",
                annotation_position="top right"
            )
    
    fig.update_layout(
        title=dict(text=f"Inventory Level - {product_id}", font=dict(size=14)),
        xaxis_title="Date",
        yaxis_title="Units",
        height=280,
        margin=dict(l=40, r=40, t=50, b=40),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white"
    )
    
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=f"inventory_{product_id}")


def _create_sales_forecast_chart(df: pd.DataFrame, prediction: dict, product_id: str) -> str:
    """Create bar chart comparing historical average vs forecast."""
    fig = go.Figure()
    
    historical_mean = prediction.get('historical_daily_mean', 0) if prediction else 0
    forecast_mean = prediction.get('forecast_daily_mean', 0) if prediction else 0
    
    categories = ['Historical Avg', 'ML Forecast']
    values = [historical_mean, forecast_mean]
    colors = ['#6b7280', '#2563eb']
    
    fig.add_trace(go.Bar(
        x=categories,
        y=values,
        marker_color=colors,
        text=[f"{v:.1f}" for v in values],
        textposition='inside',
        textfont=dict(color='white', size=14)
    ))
    
    fig.update_layout(
        title=dict(text=f"Daily Sales: Historical vs Forecast - {product_id}", font=dict(size=14)),
        yaxis_title="Units/Day",
        height=280,
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=False,
        template="plotly_white"
    )
    
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=f"forecast_{product_id}")


def _create_reorder_gauge(prediction: dict, product_id: str) -> str:
    """Create gauge chart showing inventory status relative to reorder point."""
    fig = go.Figure()
    
    current = prediction.get('current_inventory', 0) if prediction else 0
    reorder_point = prediction.get('reorder_point_units', 100) if prediction else 100
    order_up_to = prediction.get('order_up_to_level', 200) if prediction else 200
    
    # Calculate percentage (0-100 scale where reorder point is at ~40%)
    max_val = max(order_up_to * 1.2, current * 1.2, reorder_point * 2.5)
    
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=current,
        title={'text': f"Current Stock - {product_id}", 'font': {'size': 14}},
        delta={'reference': reorder_point, 'relative': False, 'position': "bottom"},
        gauge={
            'axis': {'range': [0, max_val], 'tickwidth': 1},
            'bar': {'color': "#2563eb"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#e5e7eb",
            'steps': [
                {'range': [0, reorder_point], 'color': '#fecaca'},
                {'range': [reorder_point, order_up_to], 'color': '#bbf7d0'},
                {'range': [order_up_to, max_val], 'color': '#e5e7eb'}
            ],
            'threshold': {
                'line': {'color': "#dc2626", 'width': 4},
                'thickness': 0.75,
                'value': reorder_point
            }
        }
    ))
    
    fig.update_layout(
        height=280,
        margin=dict(l=40, r=40, t=50, b=40),
        template="plotly_white"
    )
    
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=f"gauge_{product_id}")


def _create_daily_sales_chart(df: pd.DataFrame, product_id: str) -> str:
    """Create daily sales bar chart for last 30 days."""
    fig = go.Figure()
    
    if not df.empty and 'Units_Sold' in df.columns:
        # Get last 30 days of data
        recent_df = df.tail(30).copy()
        
        # Color bars based on performance (above/below average)
        avg_sales = recent_df['Units_Sold'].mean()
        colors = ['#22c55e' if v >= avg_sales else '#f97316' for v in recent_df['Units_Sold']]
        
        fig.add_trace(go.Bar(
            x=recent_df['Date'],
            y=recent_df['Units_Sold'],
            marker_color=colors,
            name='Units Sold'
        ))
        
        # Add average line
        fig.add_hline(
            y=avg_sales,
            line_dash="dot",
            line_color="#6b7280",
            annotation_text=f"Avg: {avg_sales:.0f}",
            annotation_position="top right"
        )
    
    fig.update_layout(
        title=dict(text=f"Daily Sales (Last 30 Days) - {product_id}", font=dict(size=14)),
        xaxis_title="Date",
        yaxis_title="Units Sold",
        height=280,
        margin=dict(l=40, r=40, t=50, b=40),
        showlegend=False,
        template="plotly_white"
    )
    
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=f"sales_{product_id}")


def generate_no_data_message(product_id: str) -> dict:
    """Generate placeholder charts when no prediction data is available."""
    html_template = """
    <div style="height: 280px; display: flex; align-items: center; justify-content: center; 
                background: #f9fafb; border: 2px dashed #d1d5db; border-radius: 12px;">
        <div style="text-align: center; color: #6b7280;">
            <p style="font-size: 16px; margin-bottom: 8px;">📊 Insufficient Data</p>
            <p style="font-size: 13px;">Product {product_id} needs at least 28 days of data for predictions.</p>
        </div>
    </div>
    """
    
    return {
        'inventory_timeline': html_template.format(product_id=product_id),
        'sales_forecast': html_template.format(product_id=product_id),
        'reorder_gauge': html_template.format(product_id=product_id),
        'daily_sales': html_template.format(product_id=product_id)
    }
