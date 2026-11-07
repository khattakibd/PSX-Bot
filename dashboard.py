import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np
import os
import threading
import json
import warnings
import time
import pypsx_toolkit as pt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
SYMBOLS_FILE = os.path.join(BASE_DIR, "symbols.txt")
TRADES_FILE = os.path.join(BASE_DIR, "open_trades.json")

# --- INDICATORS ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

def calculate_macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    return macd, macd_signal

def log_message(msg):
    try:
        log_text.config(state=tk.NORMAL)
        log_text.insert(tk.END, f"{msg}\n")
        log_text.see(tk.END)
        log_text.config(state=tk.DISABLED)
        root.update()
    except: pass

def download_with_60s_timeout(symbol):
    result = [None]
    def target():
        try:
            result[0] = pt.download(symbol, period="5d", show_progress=False)
        except Exception as e:
            result[0] = e
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(60)
    if thread.is_alive(): return "TIMEOUT"
    if isinstance(result[0], Exception): raise result[0]
    return result[0]

# --- ACTIONS ---
def manual_update():
    btn_update.config(state=tk.DISABLED, text="Updating...")
    log_message("⏳ Starting data update...")
    try:
        with open(SYMBOLS_FILE, "r") as f:
            symbols = [line.strip() for line in f if line.strip()]
            
        for sym in symbols:
            file_path = os.path.join(DATA_FOLDER, f"{sym}.csv")
            if not os.path.exists(file_path): continue
            try:
                new_data = download_with_60s_timeout(sym)
                if isinstance(new_data, str) and new_data == "TIMEOUT": continue
                if new_data is None or new_data.empty: continue
                    
                if isinstance(new_data.columns, pd.MultiIndex):
                    new_data.columns = new_data.columns.get_level_values(1)
                
                new_data = new_data.reset_index()
                new_data.columns = [str(c).strip().lower() for c in new_data.columns]
                
                if 'date' in new_data.columns: new_data = new_data.rename(columns={'date': 'time'})
                elif 'index' in new_data.columns: new_data = new_data.rename(columns={'index': 'time'})
                if 'time' not in new_data.columns: continue
                    
                new_data['time'] = pd.to_datetime(new_data['time'], errors='coerce')
                new_data = new_data.dropna(subset=['time'])
                if new_data.empty: continue
                
                old_data = pd.read_csv(file_path)
                old_data.columns = [str(c).strip().lower() for c in old_data.columns]
                if 'date' in old_data.columns: old_data = old_data.rename(columns={'date': 'time'})
                if 'time' not in old_data.columns: continue
                    
                old_data['time'] = pd.to_datetime(old_data['time'], dayfirst=True, errors='coerce')
                old_data = old_data.dropna(subset=['time'])
                
                latest_date_in_file = old_data['time'].max()
                rows_to_add = new_data[new_data['time'] > latest_date_in_file].copy()
                
                if not rows_to_add.empty:
                    rows_to_add['time'] = rows_to_add['time'].dt.strftime('%d/%m/%Y')
                    expected_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
                    if all(c in rows_to_add.columns for c in expected_columns):
                        rows_to_add = rows_to_add[expected_columns]
                        rows_to_add.to_csv(file_path, mode='a', header=False, index=False)
                        log_message(f"📈 {sym} updated.")
            except: pass
            time.sleep(0.1)
        log_message("✅ Update Complete!")
    except Exception as e:
        log_message(f"❌ Fatal Error: {str(e)}")
    finally:
        btn_update.config(state=tk.NORMAL, text="Update Data & Trailing SL")
        update_history_table()

def run_scanner():
    btn_scan.config(state=tk.DISABLED, text="Scanning...")
    for item in tree.get_children(): tree.delete(item)
    root.update()
    
    try:
        with open(SYMBOLS_FILE, "r") as f:
            symbols = [line.strip() for line in f if line.strip()]
            
        results = []
        for sym in symbols:
            file_path = os.path.join(DATA_FOLDER, f"{sym}.csv")
            if not os.path.exists(file_path): continue
            try:
                df = pd.read_csv(file_path)
                if len(df) < 50: continue
                df['time'] = pd.to_datetime(df['time'], dayfirst=True, errors='coerce')
                df = df.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
                
                # Indicators
                df['SMA_20'] = df['close'].rolling(window=20).mean()
                df['SMA_50'] = df['close'].rolling(window=50).mean()
                df['RSI'] = calculate_rsi(df['close'])
                df['ATR'] = calculate_atr(df)
                df['Vol_SMA'] = df['volume'].rolling(window=20).mean()
                df['MACD'], df['MACD_Signal'] = calculate_macd(df['close'])
                
                latest = df.iloc[-1]
                prev = df.iloc[-2]
                
                # Strategy: SMA Uptrend + RSI 50-70 + MACD Bullish + Volume Spike
                if (latest['SMA_20'] > latest['SMA_50'] and 
                    50 < latest['RSI'] < 70 and 
                    latest['MACD'] > latest['MACD_Signal'] and
                    latest['volume'] > (latest['Vol_SMA'] * 1.2)): # Volume filter
                    
                    entry = latest['close']
                    atr = latest['ATR']
                    sl = entry - (1.5 * atr)
                    target = entry + (2.5 * (entry - sl))
                    
                    # Support & Resistance (Simple recent 20-day high/low)
                    support = df['low'].tail(20).min()
                    resistance = df['high'].tail(20).max()
                    
                    results.append({
                        "Symbol": sym, "Entry": round(entry, 2), "SL": round(sl, 2), 
                        "Target": round(target, 2), "Support": round(support, 2), 
                        "Resistance": round(resistance, 2), "RSI": round(latest['RSI'], 1)
                    })
            except: pass
                
        for r in results:
            tree.insert("", tk.END, values=(r["Symbol"], r["Entry"], r["SL"], r["Target"], r["Support"], r["Resistance"], r["RSI"]))
        log_message(f"✅ Found {len(results)} setups.")
    except Exception as e:
        log_message(f"❌ Scan Error: {str(e)}")
    finally:
        btn_scan.config(state=tk.NORMAL, text="Scan Market")
        root.update()

def export_excel():
    try:
        trades = load_trades()
        if not trades:
            messagebox.showinfo("Export", "No trades to export.")
            return
            
        export_data = []
        for t in trades:
            if t.get("Status") == "OPEN":
                file_path = os.path.join(DATA_FOLDER, f"{t['Symbol']}.csv")
                current_price = t["Entry"]
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    current_price = float(df.iloc[-1]['close'])
                pnl = ((current_price - t["Entry"]) / t["Entry"]) * 100
                export_data.append({
                    "Symbol": t["Symbol"], "Status": "OPEN", "Entry": t["Entry"], 
                    "Current": current_price, "SL": t["SL"], "Target": t["Target"], "P&L %": round(pnl, 2)
                })
            else:
                export_data.append({
                    "Symbol": t["Symbol"], "Status": "CLOSED", "Entry": t["Entry"], 
                    "Current": "-", "SL": t["SL"], "Target": t["Target"], "P&L %": "-"
                })
                
        df_export = pd.DataFrame(export_data)
        file_path = os.path.join(BASE_DIR, "Trade_History.xlsx")
        df_export.to_excel(file_path, index=False)
        log_message(f"✅ Exported to {file_path}")
        messagebox.showinfo("Export", "Trade History exported to Excel successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to export: {str(e)}")

def view_chart():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Wait", "Select a stock from the scanner first.")
        return
        
    sym = tree.item(selected[0], 'values')[0]
    file_path = os.path.join(DATA_FOLDER, f"{sym}.csv")
    
    try:
        df = pd.read_csv(file_path)
        df['time'] = pd.to_datetime(df['time'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['time']).sort_values('time').tail(50) # Last 50 days
        
        # Create Chart Window
        chart_win = tk.Toplevel(root)
        chart_win.title(f"{sym} - 50 Day Chart")
        chart_win.geometry("800x500")
        
        fig, ax = plt.subplots(figsize=(8, 4), facecolor="#121212")
        ax.set_facecolor("#1e1e1e")
        
        ax.plot(df['time'], df['close'], color='#00FF00', linewidth=2, label="Close Price")
        ax.set_title(f"{sym} Price Action", color="white")
        ax.tick_params(colors="white")
        ax.grid(True, color="#333333")
        ax.legend()
        
        canvas = FigureCanvasTkAgg(fig, master=chart_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    except Exception as e:
        messagebox.showerror("Error", f"Could not load chart: {str(e)}")

def load_trades():
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, "r") as f: 
                data = json.load(f)
                if isinstance(data, list): return data
                return []
        except: return []
    return []

def save_trades(trades):
    try:
        with open(TRADES_FILE, "w") as f: json.dump(trades, f, indent=4)
    except: pass

def execute_trade():
    selected = tree.selection()
    if not selected: return
    trades = load_trades()
    for item in selected:
        try:
            v = tree.item(item, 'values')
            trade = {"Symbol": str(v[0]), "Entry": float(v[1]), "SL": float(v[2]), "Target": float(v[3]), "Status": "OPEN"}
            trades.append(trade)
            log_message(f"🟢 Bought {v[0]} at {v[1]}")
        except: pass
    save_trades(trades)
    update_history_table()

def close_trade():
    selected = history_tree.selection()
    if not selected: return
    trades = load_trades()
    for item in selected:
        v = history_tree.item(item, 'values')
        for t in trades:
            if isinstance(t, dict) and t.get("Symbol") == v[0] and t.get("Status") == "OPEN":
                t["Status"] = "CLOSED"
                log_message(f"🔴 Closed trade for {v[0]}")
    save_trades(trades)
    update_history_table()

def update_history_table():
    try:
        for item in history_tree.get_children(): history_tree.delete(item)
        trades = load_trades()
        for t in trades:
            if not isinstance(t, dict): continue
            if t.get("Status") == "OPEN":
                file_path = os.path.join(DATA_FOLDER, f"{t['Symbol']}.csv")
                current_price = t["Entry"]
                if os.path.exists(file_path):
                    try:
                        df = pd.read_csv(file_path)
                        if not df.empty: current_price = float(df.iloc[-1]['close'])
                    except: pass
                
                pnl_pct = ((current_price - t["Entry"]) / t["Entry"]) * 100
                if current_price > t["Entry"]:
                    new_sl = current_price * 0.95
                    if new_sl > t["SL"]: t["SL"] = new_sl
                
                history_tree.insert("", tk.END, values=(t["Symbol"], t["Entry"], round(current_price, 2), round(t["SL"],2), t["Target"], f"{pnl_pct:+.2f}%"))
            else:
                history_tree.insert("", tk.END, values=(t["Symbol"], t["Entry"], "-", t["SL"], t["Target"], "CLOSED"))
        save_trades(trades)
        root.update()
    except: pass

# --- GUI ---
root = tk.Tk()
root.title("PSX Ultimate Pro Terminal")
root.geometry("1200x850")
root.configure(bg="#121212")

tk.Label(root, text="PSX ULTIMATE PRO TERMINAL", font=("Arial", 22, "bold"), fg="#00FF00", bg="#121212").pack(pady=10)

frame_btns = tk.Frame(root, bg="#121212")
frame_btns.pack(pady=5)

btn_update = tk.Button(frame_btns, text="Update Data", font=("Arial", 11, "bold"), bg="#ff9800", fg="white", padx=10, pady=5, command=lambda: threading.Thread(target=manual_update).start())
btn_update.pack(side=tk.LEFT, padx=5)

btn_scan = tk.Button(frame_btns, text="Scan Market", font=("Arial", 11, "bold"), bg="#0078D7", fg="white", padx=10, pady=5, command=lambda: threading.Thread(target=run_scanner).start())
btn_scan.pack(side=tk.LEFT, padx=5)

btn_chart = tk.Button(frame_btns, text="View Chart", font=("Arial", 11, "bold"), bg="#17a2b8", fg="white", padx=10, pady=5, command=view_chart)
btn_chart.pack(side=tk.LEFT, padx=5)

btn_exec = tk.Button(frame_btns, text="Execute Buy", font=("Arial", 11, "bold"), bg="#28a745", fg="white", padx=10, pady=5, command=execute_trade)
btn_exec.pack(side=tk.LEFT, padx=5)

btn_close = tk.Button(frame_btns, text="Close Trade", font=("Arial", 11, "bold"), bg="#dc3545", fg="white", padx=10, pady=5, command=close_trade)
btn_close.pack(side=tk.LEFT, padx=5)

btn_export = tk.Button(frame_btns, text="Export Excel", font=("Arial", 11, "bold"), bg="#6c757d", fg="white", padx=10, pady=5, command=export_excel)
btn_export.pack(side=tk.LEFT, padx=5)

style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview", background="#1e1e1e", foreground="white", rowheight=25, fieldbackground="#1e1e1e", font=("Arial", 10))
style.configure("Treeview.Heading", background="#333333", foreground="#00FF00", font=("Arial", 11, "bold"))

tk.Label(root, text="Market Scanner (Advanced Strategy)", font=("Arial", 12, "bold"), fg="white", bg="#121212").pack(pady=(10,0))
cols = ("Symbol", "Entry", "SL", "Target", "Support", "Resistance", "RSI")
tree = ttk.Treeview(root, columns=cols, show="headings", height=8)
for c in cols:
    tree.heading(c, text=c)
    tree.column(c, anchor=tk.CENTER, width=120)
tree.pack(fill=tk.X, padx=20, pady=5)

tk.Label(root, text="Trade History & Live P&L", font=("Arial", 12, "bold"), fg="white", bg="#121212").pack(pady=(10,0))
cols_hist = ("Symbol", "Entry", "Current", "SL", "Target", "P&L %")
history_tree = ttk.Treeview(root, columns=cols_hist, show="headings", height=6)
for c in cols_hist:
    history_tree.heading(c, text=c)
    history_tree.column(c, anchor=tk.CENTER, width=120)
history_tree.pack(fill=tk.X, padx=20, pady=5)

log_frame = tk.LabelFrame(root, text="Terminal Log", fg="#00FF00", bg="#121212", font=("Arial", 10, "bold"))
log_frame.pack(fill=tk.BOTH, padx=20, pady=10, expand=True)
log_text = tk.Text(log_frame, bg="#000000", fg="#00FF00", font=("Consolas", 10), height=5)
log_text.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)
log_text.insert(tk.END, "System Ready. Advanced Strategy Active.\n")
log_text.config(state=tk.DISABLED)

update_history_table()
root.mainloop()