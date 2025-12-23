# ML – Inventory Optimization Module

This module provides **formula-based inventory optimization** using Economic Order Quantity (EOQ) and Reorder Point (ROP) calculations.

## Note on ML Models
The LSTM and feedforward neural network experiments (in `LSTM_attempt/` and `FEEDFORWARD_attempt/`) achieved only 50% relative error because the dataset's reorder quantities are manually/arbitrarily assigned with near-zero correlation to demand patterns. The formula-based optimizer in `inventory_optimizer/` provides superior, consistent results.

---

## Inventory Optimizer (Recommended)

### Installation
```bash
cd inventory_optimizer
# Dependencies: pandas, numpy (already in ml/requirements.txt)
```

### Single Product Optimization
Optimize inventory parameters for one product:

```bash
cd inventory_optimizer
python3 optimize.py "Product Name"
```

**Examples:**
```bash
python3 optimize.py "Arabica Coffee"
python3 optimize.py "Bell Pepper"
python3 optimize.py "Avocado Oil"
```

**Output:**
```
Demand Analysis:
  Monthly demand (mean): 54.62 units/month
  Daily demand (mean): 1.82 units/day
  Annual demand: 656 units/year

Inventory Parameters:
  Economic Order Quantity (EOQ): 114 units
  Reorder Point: 33 units
  Safety Stock: 20 units
  Current Stock: 74 units

Recommendation:
  Stock level is adequate
  No reorder needed at this time
```

### Batch Optimization (All Products)
Optimize all 121 products in the dataset:

```bash
cd inventory_optimizer
python3 batch_optimize.py
```

**Optional:** Specify custom output path:
```bash
python3 batch_optimize.py --output my_results.csv
```

**Output Files:**
- `../data/processed/optimizer_results/batch_optimization_results.csv` - Full results for all products
- `../data/processed/optimizer_results/reorder_list.csv` - Only products needing reorder (sorted by priority)

**Sample Output:**
```
Products optimized: 121
Products needing reorder: 40
Total order cost: $17,090.29

By Category:
                     Products  Need_Reorder   Total_Cost
Fruits & Vegetables        39            14  $3,194.17
Dairy                      24             9  $2,234.86
Beverages                   8             3  $5,174.69

Top 10 Reorder Priorities:
  Product_Name     Current_Stock  Reorder_Point  Order_Quantity
  Avocado Oil                 14             32             118
  Green Coffee                20             36             116
  Rice Flour                  15             31             116
```

### Configuration
Edit `inventory_optimizer/config.py` to adjust:
- **Holding cost rate**: 25% annual (default)
- **Order cost**: $50 per order (default)
- **Service level**: 95% (Z=1.65)
- **Lead time**: 7 days default
- **Category-specific safety multipliers**: Higher buffers for perishables
- **Perishability constraints**: Max order weeks by category

---

## ML Experiments (For Reference Only)

### LSTM Training
```bash
cd LSTM_attempt
python3 -m src.train
```
- Uses snapshot-based sequences (lookback=3 snapshots)
- Outputs: `models/demand_lstm/model.keras` and `best.keras`
- **Performance**: MAE ~26 units (50% relative error)

### Feedforward Training
```bash
cd FEEDFORWARD_attempt
python3 -m src.train
```
- Uses individual snapshots (no sequences)
- Outputs: `models/snapshot_reorder/model.keras` and `best.keras`
- **Performance**: MAE ~26 units (50% relative error)

**Why poor performance?**
- Target values (Reorder_Quantity) have near-zero correlation with features
- Data appears manually assigned, not following predictable inventory logic
- Formula-based approach is more reliable for this dataset