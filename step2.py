import pandas as pd
import os
import json

DATA_DIR = "data"
HISTORY_FILE = "history.json"
SCAN_FILE = "scan_results.json"

if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
else:
    history = []

active_trades = {}
for trade in history:
    if trade['status'] == 'OPEN':
        active_trades[trade['symbol']] = trade

results = {}

for file in os.listdir(DATA_DIR):
    if file.endswith(".csv"):
        symbol = file.replace(".csv", "")
        file_path = os.path.join(DATA_DIR, file)
        
        try:
            df = pd.read_csv(file_path)
            df['tr'] = pd.concat([df['high'] - df['low'], abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))], axis=1).max(axis=1)
            df['atr'] = df['tr'].rolling(window=14).mean()
            df['box_high'] = df['high'].rolling(window=20).max().shift(1)
            df['avg_vol'] = df['volume'].rolling(window=20).mean()
            
            today = df.iloc[-1]
            today_date = str(today['date'])
            today_close = float(today['close'])
            today_atr = float(today['atr'])
            
            is_breakout = today_close > today['box_high']
            is_volume_spike = today['volume'] > (today['avg_vol'] * 1.5)
            
            signal = "WAIT"
            current_stop = 0
            
            if symbol in active_trades:
                trade = active_trades[symbol]
                entry = trade['entry_price']
                hard_stop = entry * 0.92
                trail_stop = today_close - (today_atr * 3.0)
                current_stop = max(hard_stop, trail_stop)
                trade['current_stop_loss'] = current_stop
                
                if today_close <= current_stop:
                    signal = "EXIT (TRAIL HIT)"
                    trade['status'] = 'CLOSED'
                    trade['exit_price'] = today_close
                    trade['exit_date'] = today_date
                    trade['exit_reason'] = f"Hit Trailing Stop at {current_stop:.2f}"
                    trade['pnl'] = ((today_close - entry) / entry) * 100
                    del active_trades[symbol]
                else:
                    signal = "HOLD"
            
            elif is_breakout and is_volume_spike:
                signal = "BUY"
                current_stop = today_close * 0.92 
                new_trade = {"symbol": symbol, "entry_date": today_date, "entry_price": today_close, "current_stop_loss": current_stop, "status": "OPEN"}
                history.append(new_trade)
                active_trades[symbol] = new_trade
            
            results[symbol] = {"close": today_close, "signal": signal, "current_stop": current_stop}
        except Exception as e:
            pass

with open(HISTORY_FILE, "w") as f:
    json.dump(history, f, indent=4)
with open(SCAN_FILE, "w") as f:
    json.dump(results, f, indent=4)
print("✅ Scan complete. Trades updated.")