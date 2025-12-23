#!/usr/bin/env python3
"""
Batch inventory optimization for all products.

Usage:
    python batch_optimize.py
    python batch_optimize.py --output results.csv
"""
import argparse
import pandas as pd
import numpy as np
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm not available
    def tqdm(iterable, desc=None):
        return iterable

from config import OptimizerConfig
from optimizer import optimize_inventory


def parse_price(price_str) -> float:
    """Parse price string (e.g., '$4.50' -> 4.5)"""
    if isinstance(price_str, str):
        return float(price_str.replace('$', '').replace(',', ''))
    return float(price_str)


def batch_optimize(data_path: Path, cfg: OptimizerConfig) -> pd.DataFrame:
    """
    Optimize inventory for all products in dataset.
    
    Returns:
        DataFrame with optimization results per product
    """
    print("=" * 70)
    print("BATCH INVENTORY OPTIMIZATION")
    print("=" * 70)
    
    # Load data
    print("\nLoading data...")
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} records")
    
    # Parse numeric fields
    df['Sales_Volume'] = pd.to_numeric(df['Sales_Volume'], errors='coerce')
    df['Stock_Quantity'] = pd.to_numeric(df['Stock_Quantity'], errors='coerce')
    df['Unit_Price'] = df['Unit_Price'].apply(parse_price)
    df['Date_Received'] = pd.to_datetime(df['Date_Received'], format='mixed', errors='coerce')
    
    # Get unique products
    products = df['Product_Name'].unique()
    print(f"Found {len(products)} unique products")
    
    # Optimize each product
    print("\nOptimizing inventory parameters...")
    results = []
    
    for product in tqdm(products, desc="Processing products"):
        try:
            # Get product data
            product_df = df[df['Product_Name'] == product].copy()
            product_df = product_df.sort_values('Date_Received')
            
            # Skip if insufficient data
            if len(product_df) < 2:
                continue
            
            # Get latest values
            latest = product_df.iloc[-1]
            
            # Extract parameters
            sales_history = product_df['Sales_Volume'].dropna().values
            if len(sales_history) == 0:
                continue
            
            unit_price = latest['Unit_Price']
            current_stock = latest['Stock_Quantity']
            category = latest['Catagory'] if 'Catagory' in latest else 'Unknown'
            
            # Skip invalid data
            if pd.isna(unit_price) or pd.isna(current_stock):
                continue
            if unit_price <= 0 or current_stock < 0:
                continue
            
            # Optimize
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
            
            # Store results
            results.append({
                'Product_Name': product,
                'Category': category,
                'Unit_Price': unit_price,
                'Current_Stock': result['current_stock'],
                'Daily_Demand_Mean': result['daily_demand_mean'],
                'Daily_Demand_Std': result['daily_demand_std'],
                'Annual_Demand': result['annual_demand'],
                'EOQ': result['eoq'],
                'EOQ_Constrained': result['eoq_constrained'],
                'Safety_Stock': result['safety_stock'],
                'Reorder_Point': result['reorder_point'],
                'Days_Of_Supply': result['days_of_supply'],
                'Needs_Reorder': result['needs_reorder'],
                'Order_Quantity': result['order_quantity'],
                'Order_Cost': result['total_cost'],
                'Category_Multiplier': result['category_multiplier'],
            })
            
        except Exception as e:
            print(f"\nWarning: Failed to optimize {product}: {e}")
            continue
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    print("\n" + "=" * 70)
    print("OPTIMIZATION SUMMARY")
    print("=" * 70)
    
    print(f"\nProducts optimized: {len(results_df)}")
    print(f"Products needing reorder: {results_df['Needs_Reorder'].sum()}")
    print(f"Total order cost: ${results_df['Order_Cost'].sum():.2f}")
    
    # Category breakdown
    print("\n📊 By Category:")
    category_summary = results_df.groupby('Category').agg({
        'Product_Name': 'count',
        'Needs_Reorder': 'sum',
        'Order_Cost': 'sum'
    }).rename(columns={
        'Product_Name': 'Products',
        'Needs_Reorder': 'Need_Reorder',
        'Order_Cost': 'Total_Cost'
    })
    print(category_summary.to_string())
    
    # Top reorder priorities
    print("\n🎯 Top 10 Reorder Priorities (by order quantity):")
    top_reorders = results_df[results_df['Needs_Reorder']].nlargest(10, 'Order_Quantity')
    print(top_reorders[['Product_Name', 'Category', 'Current_Stock', 
                        'Reorder_Point', 'Order_Quantity', 'Order_Cost']].to_string(index=False))
    
    return results_df


def main():
    parser = argparse.ArgumentParser(description='Batch inventory optimization')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='Output CSV file path (default: auto-generated)')
    args = parser.parse_args()
    
    cfg = OptimizerConfig()
    
    # Run batch optimization
    results_df = batch_optimize(cfg.DATA_PATH, cfg)
    
    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = cfg.OUTPUT_DIR / "batch_optimization_results.csv"
    
    results_df.to_csv(output_path, index=False)
    print(f"\n✓ Results saved to: {output_path}")
    
    # Save reorder list separately
    reorder_path = output_path.parent / "reorder_list.csv"
    reorder_df = results_df[results_df['Needs_Reorder']].copy()
    reorder_df = reorder_df.sort_values('Order_Quantity', ascending=False)
    reorder_df.to_csv(reorder_path, index=False)
    print(f"✓ Reorder list saved to: {reorder_path}")


if __name__ == "__main__":
    main()
