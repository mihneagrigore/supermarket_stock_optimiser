"""
Core inventory optimization using EOQ and ROP formulas.
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional


def calculate_eoq(
    annual_demand: float,
    order_cost: float,
    unit_cost: float,
    holding_cost_rate: float
) -> float:
    """
    Calculate Economic Order Quantity.
    
    EOQ = sqrt((2 * D * S) / (H * C))
    where:
        D = Annual demand (units/year)
        S = Order cost ($/order)
        H = Holding cost rate (% of unit cost)
        C = Unit cost ($/unit)
    
    Returns:
        Optimal order quantity (units)
    """
    if annual_demand <= 0 or unit_cost <= 0:
        return 0.0
    
    numerator = 2 * annual_demand * order_cost
    denominator = holding_cost_rate * unit_cost
    
    if denominator <= 0:
        return 0.0
    
    eoq = np.sqrt(numerator / denominator)
    return float(eoq)


def calculate_safety_stock(
    daily_demand_std: float,
    lead_time_days: float,
    service_level_z: float,
    category_multiplier: float = 1.0
) -> float:
    """
    Calculate safety stock for demand variability.
    
    Safety Stock = Z * σ_daily * sqrt(Lead_Time) * Category_Multiplier
    where:
        Z = Service level z-score (1.65 for 95%)
        σ_daily = Standard deviation of daily demand
        Lead_Time = Lead time in days
        Category_Multiplier = Adjustment factor per product category
    
    Returns:
        Safety stock (units)
    """
    if daily_demand_std < 0 or lead_time_days <= 0:
        return 0.0
    
    safety_stock = service_level_z * daily_demand_std * np.sqrt(lead_time_days)
    safety_stock *= category_multiplier
    
    return float(safety_stock)


def calculate_reorder_point(
    daily_demand_mean: float,
    lead_time_days: float,
    safety_stock: float
) -> float:
    """
    Calculate Reorder Point.
    
    ROP = (Daily_Demand * Lead_Time) + Safety_Stock
    
    Returns:
        Reorder point (units)
    """
    if daily_demand_mean < 0 or lead_time_days <= 0:
        return safety_stock
    
    rop = (daily_demand_mean * lead_time_days) + safety_stock
    return float(rop)


def optimize_inventory(
    sales_history: np.ndarray,
    unit_price: float,
    current_stock: float,
    category: str,
    order_cost: float = 50.0,
    holding_cost_rate: float = 0.25,
    lead_time_days: int = 7,
    service_level_z: float = 1.65,
    category_safety_multipliers: Optional[Dict[str, float]] = None,
    max_order_weeks: Optional[Dict[str, int]] = None
) -> Dict:
    """
    Optimize inventory parameters for a single product.
    
    Args:
        sales_history: Array of historical sales (units)
        unit_price: Price per unit ($)
        current_stock: Current inventory level (units)
        category: Product category
        order_cost: Fixed cost per order ($)
        holding_cost_rate: Annual holding cost as fraction of unit cost
        lead_time_days: Days to receive order
        service_level_z: Z-score for service level (1.65 = 95%)
        category_safety_multipliers: Safety stock adjustments by category
        max_order_weeks: Maximum order quantity constraints by category
    
    Returns:
        Dictionary with optimization results
    """
    # Default values
    if category_safety_multipliers is None:
        category_safety_multipliers = {}
    if max_order_weeks is None:
        max_order_weeks = {}
    
    # Calculate demand statistics
    # Note: Sales_Volume appears to be monthly aggregates, convert to daily
    monthly_demand_mean = float(np.mean(sales_history))
    monthly_demand_std = float(np.std(sales_history))
    
    daily_demand_mean = monthly_demand_mean / 30.0  # Convert to daily
    daily_demand_std = monthly_demand_std / np.sqrt(30.0)  # Adjust std for daily
    annual_demand = monthly_demand_mean * 12  # 12 months
    
    # Get category-specific parameters
    category_multiplier = category_safety_multipliers.get(category, 1.0)
    max_weeks = max_order_weeks.get(category, 8)
    
    # Calculate EOQ
    eoq = calculate_eoq(
        annual_demand=annual_demand,
        order_cost=order_cost,
        unit_cost=unit_price,
        holding_cost_rate=holding_cost_rate
    )
    
    # Calculate safety stock
    safety_stock = calculate_safety_stock(
        daily_demand_std=daily_demand_std,
        lead_time_days=lead_time_days,
        service_level_z=service_level_z,
        category_multiplier=category_multiplier
    )
    
    # Calculate reorder point
    reorder_point = calculate_reorder_point(
        daily_demand_mean=daily_demand_mean,
        lead_time_days=lead_time_days,
        safety_stock=safety_stock
    )
    
    # Cap reorder point at 100 units (dataset constraint)
    reorder_point = min(reorder_point, 100.0)
    
    # Apply perishability constraint to EOQ
    max_order_qty = daily_demand_mean * 7 * max_weeks
    eoq_constrained = min(eoq, max_order_qty, 100.0)  # Also cap EOQ at 100
    
    # Determine if reorder is needed
    needs_reorder = current_stock <= reorder_point
    
    # Calculate order quantity if reorder needed
    if needs_reorder:
        # Order up to: ROP + EOQ - current_stock
        order_quantity = max(0, reorder_point + eoq_constrained - current_stock)
    else:
        order_quantity = 0.0
    
    # Calculate costs
    order_cost_total = order_cost if needs_reorder else 0.0
    inventory_cost = current_stock * unit_price * holding_cost_rate / 365  # Daily holding cost
    total_cost = order_cost_total + (order_quantity * unit_price)
    
    # Days of supply
    days_of_supply = current_stock / daily_demand_mean if daily_demand_mean > 0 else 999
    
    return {
        'monthly_demand_mean': monthly_demand_mean,
        'monthly_demand_std': monthly_demand_std,
        'daily_demand_mean': daily_demand_mean,
        'daily_demand_std': daily_demand_std,
        'annual_demand': annual_demand,
        'eoq': eoq,
        'eoq_constrained': eoq_constrained,
        'safety_stock': safety_stock,
        'reorder_point': reorder_point,
        'current_stock': current_stock,
        'needs_reorder': needs_reorder,
        'order_quantity': order_quantity,
        'order_cost': order_cost_total,
        'total_cost': total_cost,
        'days_of_supply': days_of_supply,
        'category_multiplier': category_multiplier,
        'max_weeks_constraint': max_weeks,
    }
