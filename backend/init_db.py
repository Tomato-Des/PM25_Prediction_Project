"""
Initialize database with ALL historical data (2018-2025).
Run this ONCE before deployment to Railway.

Usage:
    python -m backend.init_db --csv path/to/all_historical_data.csv
"""

import pandas as pd
import argparse
from datetime import datetime
from backend.database import Database
from backend.config import Config

def init_from_csv(csv_path: str):
    """
    Initialize database with ALL historical PM2.5 data.
    CSV format: createdAt, pm25
    
    Args:
        csv_path: Path to PM2.5 CSV file (all years 2018-2025)
    """
    print("\n" + "="*60)
    print("🚀 DATABASE INITIALIZATION - FULL HISTORICAL DATA")
    print("="*60)
    
    # Initialize database
    db = Database()
    db.init_schema()
    
    # Read CSV
    print(f"📂 Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path, encoding='utf-8')
    print(f"   Total rows: {len(df):,}")
    
    # Convert datetime
    df['datetime'] = pd.to_datetime(df['createdAt'])
    
    # Sort by datetime ascending (oldest first)
    df = df.sort_values('datetime', ascending=True)
    
    start_dt = df['datetime'].iloc[0]
    end_dt = df['datetime'].iloc[-1]
    total_hours = len(df)
    
    print(f"\n📊 Data Range:")
    print(f"   Start: {start_dt}")
    print(f"   End:   {end_dt}")
    print(f"   Total: {total_hours:,} hours ({total_hours/24:.1f} days)")
    
    # Prepare data for insertion with robust validation
    print(f"\n⚙️  Processing data...")
    data_to_insert = []
    skipped = 0
    
    for _, row in df.iterrows():
        pm25_val = row['pm25']
        
        # Robust validation: try converting to float
        try:
            pm25_clean = float(pm25_val)
            if pd.isna(pm25_clean):  # Catches NaN after conversion
                pm25_clean = None
                skipped += 1
        except (ValueError, TypeError):
            pm25_clean = None  # Invalid (will be forward-filled)
            skipped += 1
        
        # Keep ALL rows (don't skip) to maintain continuous time series
        data_to_insert.append({
            'datetime': row['datetime'].strftime('%Y-%m-%d %H:%M'),
            'pm25': pm25_clean,
            'sitename': Config.SITE_NAME,
            'source': 'history'
        })
    
    print(f"   Valid records: {len(data_to_insert):,}")
    print(f"   Skipped (NaN): {skipped}")
    
    # Apply forward-fill for any gaps
    print(f"\n🔧 Applying forward-fill...")
    data_to_insert.sort(key=lambda x: x['datetime'])
    last_valid = None
    filled_data = []
    filled_count = 0
    
    for record in data_to_insert:
        if record['pm25'] is not None:
            last_valid = record['pm25']
            filled_data.append(record)
        elif last_valid is not None:
            record['pm25'] = last_valid
            filled_data.append(record)
            filled_count += 1
    
    if filled_count > 0:
        print(f"   Forward-filled: {filled_count} records")
    
    # Insert into database in batches
    print(f"\n💾 Inserting into database...")
    batch_size = 1000
    total = len(filled_data)
    
    for i in range(0, total, batch_size):
        batch = filled_data[i:i+batch_size]
        db.insert_measurements_bulk(batch)
        progress = min(i+batch_size, total)
        print(f"   Progress: {progress:,}/{total:,} ({progress/total*100:.1f}%)")
    
    # Verify
    count = db.get_measurement_count()
    latest_dt = db.get_latest_datetime()
    
    print(f"\n✅ Database initialized successfully!")
    print(f"   Total measurements: {count:,}")
    print(f"   Latest datetime: {latest_dt}")
    print(f"   Database size: ~{count * 50 / 1024 / 1024:.2f} MB (estimated)")
    
    # Check if we have enough for model inference
    if count >= 720:
        print(f"\n✅ Ready for model inference (≥720 hours)")
    else:
        print(f"\n⚠️  Warning: Only {count} hours, need 720 for predictions")
    
    print("="*60)
    print("✅ INITIALIZATION COMPLETE")
    print("="*60 + "\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Initialize PM2.5 database with full historical data')
    parser.add_argument('--csv', required=True, help='Path to PM2.5 CSV file (all years)')
    
    args = parser.parse_args()
    init_from_csv(args.csv)