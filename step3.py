import json
import os
from datetime import datetime

SCAN_FILE = "scan_results.json"
HISTORY_FILE = "history.json"
OUTPUT_HTML = "index.html"

with open(SCAN_FILE, "r") as f:
    scan_data = json.load(f)
with open(HISTORY_FILE, "r") as f:
    history_data = json.load(f)

buys, holds, exits, waits = [], [], [], []
for sym, data in scan_data.items():
    if data['signal'] == 'BUY': buys.append((sym, data))
    elif data['signal'] == 'HOLD': holds.append((sym, data))
    elif 'EXIT' in data['signal']: exits.append((sym, data))
    else: waits.append((sym, data))

html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>PSX Trailing Stop Bot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 15px; }}
        h1 {{ text-align: center; color: #38bdf8; font-size: 24px; margin-bottom: 5px; }}
        .datetime {{ text-align: center; color: #94a3b8; font-size: 14px; margin-bottom: 20px; }}
        .search-box {{ text-align: center; margin-bottom: 20px; }}
        input {{ padding: 12px; width: 90%; max-width: 400px; border-radius: 8px; border: 1px solid #334155; background-color: #1e293b; color: white; font-size: 16px; outline: none; }}
        .section {{ margin-bottom: 15px; }}
        .toggle-btn {{ background-color: #1e293b; color: white; cursor: pointer; padding: 15px; width: 100%; border: none; text-align: left; outline: none; font-size: 16px; border-radius: 8px; font-weight: bold; display: flex; justify-content: space-between; }}
        .content {{ padding: 0 10px; max-height: 0; overflow: hidden; transition: max-height 0.3s ease-out; background-color: #1e293b; border-radius: 0 0 8px 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 10px; font-size: 13px; }}
        th, td {{ padding: 10px 4px; text-align: center; border-bottom: 1px solid #334155; }}
        th {{ color: #94a3b8; font-weight: normal; }}
        .buy-btn {{ background: #22c55e; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }}
        .hold-btn {{ background: #3b82f6; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }}
        .exit-btn {{ background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }}
        .wait-btn {{ background: #64748b; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }}
        .sl {{ color: #ef4444; font-weight: bold; }}
        .reason {{ font-size: 11px; color: #94a3b8; }}
    </style>
</head>
<body>
    <h1>PSX Trailing Stop Bot</h1>
    <div class="datetime" id="datetime"></div>
    <div class="search-box">
        <input type="text" id="searchInput" onkeyup="filterTable()" placeholder="🔍 Search stock...">
    </div>
"""

def generate_section(title, list_data, btn_class, is_history=False, is_trade=False):
    count = len(list_data)
    section_html = f"""
    <div class="section">
        <button class="toggle-btn" onclick="toggleSection('{title}')">{title} ({count}) <span>▼</span></button>
        <div class="content" id="{title}"><table>
    """
    if is_history:
        section_html += "<tr><th>Symbol</th><th>Entry Date</th><th>Entry</th><th>Exit</th><th>Reason</th><th>PnL</th></tr>"
        for trade in list_data:
            if trade['status'] == 'CLOSED':
                pnl = trade.get('pnl', 0)
                pnl_color = "#22c55e" if pnl > 0 else "#ef4444"
                reason = trade.get('exit_reason', 'Unknown')
                section_html += f"<tr><td><b>{trade['symbol']}</b></td><td>{trade['entry_date']}</td><td>{trade['entry_price']:.2f}</td><td>{trade['exit_price']:.2f}</td><td class='reason'>{reason}</td><td style='color:{pnl_color}'>{pnl:.1f}%</td></tr>"
    elif is_trade:
        section_html += "<tr><th>Symbol</th><th>Entry</th><th>Live Stop</th><th>Action</th></tr>"
        if not list_data: section_html += "<tr><td colspan='4'>None</td></tr>"
        for sym, data in list_data:
            section_html += f"""
                <tr class="stock-row">
                    <td><b>{sym}</b></td>
                    <td>{data['entry_price'] if 'entry_price' in data else data['close']:.2f}</td>
                    <td class="sl">{data['current_stop']:.2f}</td>
                    <td><span class="{btn_class}">{data['signal']}</span></td>
                </tr>
            """
    else:
        section_html += "<tr><th>Symbol</th><th>Close</th><th>Action</th></tr>"
        if not list_data: section_html += "<tr><td colspan='3'>None</td></tr>"
        for sym, data in list_data:
            section_html += f"""
                <tr class="stock-row">
                    <td><b>{sym}</b></td>
                    <td>{data['close']:.2f}</td>
                    <td><span class="{btn_class}">{data['signal']}</span></td>
                </tr>
            """
    section_html += "</table></div></div>"
    return section_html

html += generate_section("🟢 BUY SIGNALS", buys, "buy-btn", is_trade=True)
html += generate_section("🔵 HOLDING (Trailing)", holds, "hold-btn", is_trade=True)
html += generate_section("🔴 EXIT ALERTS", exits, "exit-btn")
html += generate_section("⚪ WATCHLIST (WAIT)", waits, "wait-btn")
html += generate_section("📜 TRADE HISTORY", history_data, "", is_history=True)

html += """
    <script>
        function updateTime() { document.getElementById('datetime').innerHTML = "Last Scanned: " + new Date().toLocaleString(); }
        setInterval(updateTime, 1000); updateTime();
        function toggleSection(id) {
            var content = document.getElementById(id);
            var btn = content.previousElementSibling;
            if (content.style.maxHeight) { content.style.maxHeight = null; btn.querySelector('span').innerHTML = '▼'; }
            else { content.style.maxHeight = content.scrollHeight + "px"; btn.querySelector('span').innerHTML = '▲'; }
        }
        window.onload = function() { toggleSection('⚪ WATCHLIST (WAIT)'); };
        function filterTable() {
            var input = document.getElementById("searchInput");
            var filter = input.value.toUpperCase();
            var rows = document.getElementsByClassName("stock-row");
            for (var i = 0; i < rows.length; i++) {
                var td = rows[i].getElementsByTagName("td")[0];
                if (td) { rows[i].style.display = (td.textContent || td.innerText).toUpperCase().indexOf(filter) > -1 ? "" : "none"; }
            }
        }
    </script>
</body>
</html>
"""
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)
print("✅ Dashboard generated. Trade History now shows reasons!")