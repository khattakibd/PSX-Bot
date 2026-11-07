import psxdata
import pandas as pd
import os

OUT_DIR = "data"
os.makedirs(OUT_DIR, exist_ok=True)

symbols = [
    "OGDC", "PPL", "PSO", "APL", "SHEL", "MARI", "POL", "ATRL", "CNERGY", "SNGP",
    "LUCK", "MLCF", "PIOC", "CHCC", "FCCL", "KOHC", "DGKC", "ACPL", "BWCL", "THCCL",
    "MEBL", "UBL", "HBL", "MCB", "BAHL", "BOP", "NBP", "AKBL", 
    "ENGRO", "ENGROH", "EFERT", "FFC", "FATIMA", "ICI", "LOTCHEM", "COLG", "NESTLE", 
    "SYS", "TRG", "AVN", "PTC", "SAZEW", "GAL", "GHNI", "NML", "GATM", "NCPL", "KTML", "UPFL", "FFL"
]

for symbol in symbols:
    print(f"Downloading {symbol}...")
    try:
        df = psxdata.stocks(symbol, start='2024-01-01')
        if df is not None and not df.empty:
            df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
            save_path = os.path.join(OUT_DIR, f"{symbol}.csv")
            df.to_csv(save_path, index=False)
            print(f"✅ Saved {symbol} ({len(df)} rows)")
        else:
            print(f"⚠️ No data for {symbol}")
    except Exception as e:
        print(f"❌ Failed {symbol}: {e}")