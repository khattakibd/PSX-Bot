import psxdata
import pandas as pd
import os

OUT_DIR = r"C:\PSX_Bot\data"
os.makedirs(OUT_DIR, exist_ok=True)

# Your list of stocks
symbols = ["LUCK", "MEBL", "OGDC"]

for symbol in symbols:
    print(f"Downloading {symbol}...")
    try:
        df = psxdata.stocks(symbol, start='2024-01-01')
        
        # THIS IS THE FIX: Sort by date so oldest is first, newest is last
        df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
        
        # Save to CSV
        save_path = os.path.join(OUT_DIR, f"{symbol}.csv")
        df.to_csv(save_path, index=False)
        print(f"✅ Saved {symbol} ({len(df)} rows)")
        
    except Exception as e:
        print(f"❌ Failed {symbol}: {e}")