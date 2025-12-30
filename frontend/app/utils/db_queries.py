import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta


def get_client_id(email):
    """
    Query clients.db to get client_id from user email.
    
    Args:
        email: User's email address
        
    Returns:
        int: Client ID or None if not found
    """
    clients_db = os.path.join(
        os.path.dirname(__file__), 
        "../../../backend/clients/clients.db"
    )
    
    try:
        conn = sqlite3.connect(clients_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM clients WHERE email = ?", (email,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        return None
        
    except Exception as e:
        print(f"Error querying client_id: {e}")
        return None


def get_product_inventory_data(client_id, product_id, days_limit=None):
    """
    Fetch historical inventory data for a specific product from products.db.
    
    Args:
        client_id: Client ID from clients.db
        product_id: Product ID to fetch data for
        days_limit: Number of recent days to fetch (None = all time)
        
    Returns:
        pandas.DataFrame with columns: Date, Inventory_Level, Units_Sold, 
        Price, Discount, Holiday_Promotion
    """
    products_db = os.path.join(
        os.path.dirname(__file__),
        "../../../database/products.db"
    )
    
    print(f"DEBUG: Querying products.db at: {products_db}")
    print(f"DEBUG: client_id={client_id}, product_id={product_id}, days_limit={days_limit}")
    
    try:
        conn = sqlite3.connect(products_db)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory'")
        if not cursor.fetchone():
            print("inventory table does not exist. Please upload CSV data first.")
            conn.close()
            return pd.DataFrame()
        
        # Build query with optional date filter
        if days_limit:
            # First, get the maximum date for this product
            max_date_query = """
                SELECT MAX(Date) as max_date
                FROM inventory
                WHERE client_id = ? AND Product_ID = ?
            """
            max_date_df = pd.read_sql_query(max_date_query, conn, params=(client_id, product_id))
            max_date_str = max_date_df['max_date'].iloc[0] if not max_date_df.empty else None
            
            if max_date_str:
                # Calculate cutoff based on the last date in the data
                max_date = datetime.strptime(max_date_str, '%Y-%m-%d')
                cutoff_date = (max_date - timedelta(days=days_limit)).strftime('%Y-%m-%d')
                print(f"DEBUG: Data max date: {max_date_str}, cutoff for last {days_limit} days: {cutoff_date}")
                
                query = """
                    SELECT Date, Inventory_Level, Units_Sold, Price, Discount, Holiday_Promotion
                    FROM inventory
                    WHERE client_id = ? AND Product_ID = ? AND Date >= ?
                    ORDER BY Date ASC
                """
                df = pd.read_sql_query(query, conn, params=(client_id, product_id, cutoff_date))
            else:
                # No data found
                df = pd.DataFrame()
        else:
            query = """
                SELECT Date, Inventory_Level, Units_Sold, Price, Discount, Holiday_Promotion
                FROM inventory
                WHERE client_id = ? AND Product_ID = ?
                ORDER BY Date ASC
            """
            df = pd.read_sql_query(query, conn, params=(client_id, product_id))
        
        conn.close()
        
        print(f"DEBUG: Query returned {len(df)} rows")
        
        # Convert Date column to datetime
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
        
        return df
        
    except Exception as e:
        print(f"Error querying product inventory data: {e}")
        print("Please re-upload your CSV file to import data into the database.")
        return pd.DataFrame()
