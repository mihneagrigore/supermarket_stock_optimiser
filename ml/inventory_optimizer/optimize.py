#!/usr/bin/env python3
"""
CLI tool for optimizing inventory for a single product.

Usage:
    python optimize.py "Product Name"
    python optimize.py "Arabica Coffee"
    python optimize.py "Bell Pepper"
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

from config import OptimizerConfig
from optimizer import optimize_inventory


def load_product_data(product_name: str, data_path: Path) -> pd.DataFrame:
    """Load historical data for a specific product."""
    df = pd.read_csv(data_path)
    
    # Case-insensitive search
    mask = df['Product_Name'].str.lower() == product_name.lower()
    product_df = df[mask].copy()
    
    if len(product_df) == 0:
        available = df['Product_Name'].unique()[:10]
        raise ValueError(
            f"Product '{product_name}' not found.\n"
            f"Available products (first 10): {', '.join(available)}"
        )
    
    return product_df


def parse_price(price_str) -> float:
    """Parse price string (e.g., '$4.50' -> 4.5)"""
    if isinstance(price_str, str):
        return float(price_str.replace('$', '').replace(',', ''))
    return float(price_str)


def main():
    if len(sys.argv) < 2:
        print("Usage: python optimize.py \"Product Name\"")
        print("\nExample:")
        print("  python optimize.py \"Arabica Coffee\"")
        print("  python optimize.py \"Bell Pepper\"")
        sys.exit(1)
    
    product_name = sys.argv[1]
    cfg = OptimizerConfig()
    
    print("=" * 70)
    print("INVENTORY OPTIMIZER - FORMULA-BASED")
    print("=" * 70)
    print(f"\nProduct: {product_name}")
    
    # Load data
    print("\nLoading data...")
    df = load_product_data(product_name, cfg.DATA_PATH)
    print(f"Found {len(df)} historical records")
    
    # Parse numeric fields
    df['Sales_Volume'] = pd.to_numeric(df['Sales_Volume'], errors='coerce')
    df['Stock_Quantity'] = pd.to_numeric(df['Stock_Quantity'], errors='coerce')
    df['Unit_Price'] = df['Unit_Price'].apply(parse_price)
    
    # Get latest values
    latest = df.iloc[-1]
    
    # Extract parameters
    sales_history = df['Sales_Volume'].dropna().values
    unit_price = latest['Unit_Price']
    current_stock = latest['Stock_Quantity']
    category = latest['Catagory'] if 'Catagory' in latest else 'Unknown'
    
    print(f"Category: {category}")
    print(f"Current stock: {current_stock:.0f} units")
    print(f"Unit price: ${unit_price:.2f}")
    print(f"Sales history: {len(sales_history)} data points")
    
    # Optimize
    print("\nCalculating optimal inventory parameters...")
    result = optimize_inventory(
        sales_history=sales_history,
        unit_price=unit_price,
        current_stock=current_stock,
        category=category,
        order_cost=cfg.ORDER_COST,
        holding_cost_rate=cfg.HOLDING_COST_RATE,
        lead_time_days=cfg.DEFAULT_LEAD_TIME_DAYS,
        service_level_z=cfg.SERVICE_LEVEL_Z,
        category_safety_multipliers=cfg.CATEGORY_SAFETY_MULTIPLIERS,
        max_order_weeks=cfg.MAX_ORDER_WEEKS
    )
    
    # Display results
    print("\n" + "=" * 70)
    print("OPTIMIZATION RESULTS")
    print("=" * 70)
    
    print("\n📊 Demand Analysis:")
    print(f"  Monthly demand (mean): {result['monthly_demand_mean']:.2f} units/month")
    print(f"  Monthly demand (std): {result['monthly_demand_std']:.2f} units/month")
    print(f"  Daily demand (mean): {result['daily_demand_mean']:.2f} units/day")
    print(f"  Daily demand (std): {result['daily_demand_std']:.2f} units/day")
    print(f"  Annual demand: {result['annual_demand']:.0f} units/year")
    
    print("\n📦 Inventory Parameters:")
    print(f"  Economic Order Quantity (EOQ): {result['eoq']:.0f} units")
    print(f"  EOQ (perishability-constrained): {result['eoq_constrained']:.0f} units")
    print(f"  Safety Stock: {result['safety_stock']:.0f} units")
    print(f"  Reorder Point: {result['reorder_point']:.0f} units")
    print(f"  Current Stock: {result['current_stock']:.0f} units")
    print(f"  Days of Supply: {result['days_of_supply']:.1f} days")
    
    print("\n💰 Cost Analysis:")
    print(f"  Order Cost: ${result['order_cost']:.2f}")
    print(f"  Total Cost (if ordering): ${result['total_cost']:.2f}")
    
    print("\n🎯 Recommendation:")
    if result['needs_reorder']:
        print(f"  ⚠️  REORDER NEEDED")
        print(f"  Order Quantity: {result['order_quantity']:.0f} units")
        print(f"  Order Cost: ${result['order_quantity'] * unit_price:.2f}")
    else:
        print(f"  ✓ Stock level is adequate")
        print(f"  No reorder needed at this time")
    
    print("\n📝 Notes:")
    print(f"  Category safety multiplier: {result['category_multiplier']:.1f}x")
    print(f"  Max order constraint: {result['max_weeks_constraint']} weeks supply")
    print(f"  Service level: {cfg.SERVICE_LEVEL * 100:.0f}%")
    print(f"  Lead time: {cfg.DEFAULT_LEAD_TIME_DAYS} days")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
