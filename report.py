#!/usr/bin/env python3
"""
每日汇率观察报告生成器
运行方式: python report.py
"""

from datetime import datetime, timedelta
import sys
import os

# 尝试导入配置和数据获取模块
try:
    from config import FRED_API_KEY, ALPHA_VANTAGE_KEY, NASDAQ_API_KEY
    from fetch_data import get_usdcny, get_usdcny_history, get_treasury_yield, get_dxy, get_vix, analyze
    USE_REAL_API = True
except ImportError:
    USE_REAL_API = False

def get_demo_data():
    """演示数据（用于测试报告样式）"""
    import random
    random.seed(int(datetime.now().strftime("%Y%m%d")))
    
    base_rate = 7.2451
    history = []
    today = datetime.now()
    rate = base_rate * 0.985
    for i in range(30, 0, -1):
        date = today - timedelta(days=i)
        rate = rate * (1 + random.uniform(-0.003, 0.004))
        history.append({"date": date.strftime("%Y-%m-%d"), "rate": round(rate, 4)})
    history.append({"date": today.strftime("%Y-%m-%d"), "rate": base_rate})
    
    usdcny = {"rate": base_rate, "date": today.strftime("%Y-%m-%d"), "status": "ok"}
    treasury = {"yield": 4.32, "date": today.strftime("%Y-%m-%d"), "status": "ok"}
    dxy = {"dxy": 103.45, "eurusd": 1.0821, "date": today.strftime("%Y-%m-%d"), "note": "基于EUR/USD估算", "status": "ok"}
    vix = {"vix": 18.7, "vix_high": 20.1, "vix_low": 17.3, "date": today.strftime("%Y-%m-%d"), "status": "ok"}
    
    return usdcny, history, treasury, dxy, vix

def generate_html(usdcny, history, treasury, dxy, vix, analysis):
    """生成精美的HTML报告"""
    
    risk_colors = {"低": "#10b981", "中等": "#f59e0b", "高": "#ef4444"}
    risk_bg = {"低": "rgba(16,185,129,0.12)", "中等": "rgba(245,158,11,0.12)", "高": "rgba(239,68,68,0.12)"}
    risk_level = analysis["risk_level"]
    risk_score = analysis.get("risk_score", 50)
    rc = risk_colors.get(risk_level, "#888")
    rb = risk_bg.get(risk_level, "rgba(0,0,0,0.05)")

    # 历史汇率图表数据
    chart_labels = [h["date"][-5:] for h in history[-14:]]
    chart_data = [h["rate"] for h in history[-14:]]
    chart_labels_js = str(chart_labels).replace("'", '"')
    chart_data_js = str(chart_data)

    # 近10日历史表格
    history_rows = ""
    recent = history[-10:]
    for i, h in enumerate(reversed(recent)):
        if i > 0:
            prev = recent[-(i)]
            change = h["rate"] - prev["rate"]
            arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
            color = "#ef4444" if change > 0 else "#10b981" if change < 0 else "#888"
            change_html = f'<span style="color:{color}">{arrow} {abs(change):.4f}</span>'
        else:
            change_html = '<span style="color:#888">—</span>'
        
        is_today = i == 0
        row_style = 'style="background:rgba(99,102,241,0.06)"' if is_today else ''
        history_rows += f"""
        <tr {row_style}>
          <td>{'📅 ' if is_today else ''}{h['date']}</td>
          <td style="font-weight:{'700' if is_today else '400'}">{h['rate']:.4f}</td>
          <td>{change_html}</td>
        </tr>"""

    # 建议卡片
    suggestion_cards = ""
    for s in analysis["suggestions"]:
        suggestion_cards += f"""
        <div class="suggest-card">
          <div class="suggest-icon">{s['icon']}</div>
          <div class="suggest-body">
            <div class="suggest-title">{s['title']}</div>
            <div class="suggest-content">{s['content']}</div>
          </div>
        </div>"""

    # 状态徽章
    def status_badge(data, field, unit="", fmt=".2f"):
        val = data.get(field)
        status = data.get("status", "error")
        if val is not None:
            return f'<span class="badge-ok">{format(val, fmt)}{unit}</span>'
        else:
            return '<span class="badge-error">获取失败</span>'

    report_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    rate_val = usdcny.get('rate', 'N/A')
    yield_val = treasury.get('yield', 'N/A')
    dxy_val = dxy.get('dxy', 'N/A')
    vix_val = vix.get('vix', 'N/A')
    
    rates_30d = [h["rate"] for h in history] if history else []
    max_30d = max(rates_30d) if rates_30d else "N/A"
    min_30d = min(rates_30d) if rates_30d else "N/A"
    avg_30d = sum(rates_30d)/len(rates_30d) if rates_30d else "N/A"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>汇率观察日报 · {datetime.now().strftime('%Y/%m/%d')}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=JetBrains+Mono:wght@400;600&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg: #0f0f13;
      --bg2: #16161e;
      --bg3: #1e1e28;
      --border: rgba(255,255,255,0.07);
      --text: #e8e8f0;
      --muted: #7b7b8d;
      --accent: #818cf8;
      --accent2: #34d399;
      --danger: #f87171;
      --warn: #fbbf24;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'DM Sans', 'Noto Serif SC', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 0 0 60px;
    }}

    /* 顶部横幅 */
    .header {{
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      border-bottom: 1px solid rgba(129,140,248,0.2);
      padding: 40px 0 36px;
      position: relative;
      overflow: hidden;
    }}
    .header::before {{
      content: '';
      position: absolute;
      top: -60px; right: -60px;
      width: 300px; height: 300px;
      background: radial-gradient(circle, rgba(129,140,248,0.15) 0%, transparent 70%);
    }}
    .header-inner {{
      max-width: 960px;
      margin: 0 auto;
      padding: 0 24px;
      position: relative;
    }}
    .header-tag {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--accent);
      letter-spacing: 2px;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    .header h1 {{
      font-family: 'Noto Serif SC', serif;
      font-size: 32px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 8px;
    }}
    .header-sub {{
      color: rgba(255,255,255,0.45);
      font-size: 13px;
    }}
    .risk-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 600;
      background: {rb};
      border: 1px solid {rc}44;
      color: {rc};
      margin-top: 16px;
    }}
    .risk-dot {{
      width: 7px; height: 7px;
      border-radius: 50%;
      background: {rc};
      animation: pulse 2s ease-in-out infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.5; transform: scale(1.3); }}
    }}

    .container {{
      max-width: 960px;
      margin: 0 auto;
      padding: 0 24px;
    }}

    /* 四格指标卡 */
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin: 28px 0 20px;
    }}
    @media (max-width: 700px) {{
      .metrics {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    .metric-card {{
      background: var(--bg2);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px 18px;
      position: relative;
      overflow: hidden;
      transition: border-color 0.2s;
    }}
    .metric-card:hover {{ border-color: rgba(129,140,248,0.3); }}
    .metric-card::after {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 2px;
    }}
    .mc-usdcny::after {{ background: linear-gradient(90deg, #818cf8, #a78bfa); }}
    .mc-treasury::after {{ background: linear-gradient(90deg, #34d399, #6ee7b7); }}
    .mc-dxy::after {{ background: linear-gradient(90deg, #fbbf24, #fde68a); }}
    .mc-vix::after {{ background: linear-gradient(90deg, #f87171, #fca5a5); }}

    .metric-label {{
      font-size: 11px;
      color: var(--muted);
      letter-spacing: 0.5px;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    .metric-value {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 26px;
      font-weight: 600;
      color: #fff;
      line-height: 1;
      margin-bottom: 6px;
    }}
    .metric-meta {{
      font-size: 11px;
      color: var(--muted);
    }}

    /* 图表区 */
    .chart-section {{
      background: var(--bg2);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 24px;
      margin-bottom: 20px;
    }}
    .section-title {{
      font-family: 'Noto Serif SC', serif;
      font-size: 15px;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 18px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .section-title::before {{
      content: '';
      display: block;
      width: 3px;
      height: 16px;
      background: var(--accent);
      border-radius: 2px;
    }}
    .chart-stats {{
      display: flex;
      gap: 24px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }}
    .chart-stat {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .chart-stat-label {{ font-size: 11px; color: var(--muted); }}
    .chart-stat-val {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 15px;
      font-weight: 600;
    }}
    .chart-container {{ height: 180px; }}

    /* 两栏布局 */
    .two-col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 20px;
    }}
    @media (max-width: 650px) {{
      .two-col {{ grid-template-columns: 1fr; }}
    }}

    /* 建议卡片 */
    .suggests-section {{
      background: var(--bg2);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 24px;
      margin-bottom: 20px;
    }}
    .suggest-card {{
      display: flex;
      gap: 14px;
      padding: 14px 0;
      border-bottom: 1px solid var(--border);
    }}
    .suggest-card:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .suggest-card:first-child {{ padding-top: 0; }}
    .suggest-icon {{
      font-size: 22px;
      width: 36px;
      flex-shrink: 0;
      padding-top: 2px;
    }}
    .suggest-title {{
      font-size: 14px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 5px;
    }}
    .suggest-content {{
      font-size: 13px;
      color: var(--muted);
      line-height: 1.7;
    }}

    /* 历史表格 */
    .table-section {{
      background: var(--bg2);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 24px;
      margin-bottom: 20px;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{
      text-align: left;
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 0 12px 12px 12px;
    }}
    td {{
      font-size: 13px;
      padding: 10px 12px;
      border-top: 1px solid var(--border);
      font-family: 'JetBrains Mono', monospace;
    }}
    tr:first-child td {{ border-top: none; }}

    /* 免责声明 */
    .disclaimer {{
      background: var(--bg3);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 18px;
      font-size: 12px;
      color: var(--muted);
      line-height: 1.7;
      margin-bottom: 20px;
    }}

    /* 数据源脚注 */
    .footer {{
      text-align: center;
      font-size: 11px;
      color: #3a3a4a;
      padding-top: 10px;
    }}
    .footer span {{ margin: 0 8px; }}

    .badge-ok {{
      display: inline-block;
      background: rgba(52,211,153,0.1);
      border: 1px solid rgba(52,211,153,0.2);
      color: #34d399;
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
    }}
    .badge-error {{
      display: inline-block;
      background: rgba(248,113,113,0.1);
      border: 1px solid rgba(248,113,113,0.2);
      color: #f87171;
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 4px;
    }}

    /* 风险仪表 */
    .risk-meter {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 12px;
    }}
    .risk-bar-bg {{
      flex: 1;
      height: 4px;
      background: var(--bg3);
      border-radius: 2px;
      overflow: hidden;
    }}
    .risk-bar-fill {{
      height: 100%;
      width: {risk_score}%;
      background: linear-gradient(90deg, #10b981, #fbbf24, #ef4444);
      border-radius: 2px;
      transition: width 1s ease;
    }}
    .risk-pct {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--muted);
      width: 32px;
      text-align: right;
    }}
  </style>
</head>
<body>
  <!-- 顶部标题 -->
  <div class="header">
    <div class="header-inner">
      <div class="header-tag">FX Daily · Macro Dashboard</div>
      <h1>汇率观察日报</h1>
      <div class="header-sub">生成时间：{report_time} &nbsp;·&nbsp; 数据来源：ExchangeRate-API · FRED · Alpha Vantage · Nasdaq Data Link</div>
      <div class="risk-pill">
        <span class="risk-dot"></span>
        当前市场风险等级：{risk_level}
      </div>
      <div class="risk-meter">
        <div class="risk-bar-bg"><div class="risk-bar-fill"></div></div>
        <div class="risk-pct">{risk_score}分</div>
      </div>
    </div>
  </div>

  <div class="container">
    <!-- 四格指标 -->
    <div class="metrics">
      <div class="metric-card mc-usdcny">
        <div class="metric-label">💱 USD/CNY</div>
        <div class="metric-value">{rate_val if isinstance(rate_val, str) else f'{rate_val:.4f}'}</div>
        <div class="metric-meta">{usdcny.get('date', '')}</div>
      </div>
      <div class="metric-card mc-treasury">
        <div class="metric-label">🏦 10Y 美债收益率</div>
        <div class="metric-value">{yield_val if isinstance(yield_val, str) else f'{yield_val:.2f}'}{'%' if not isinstance(yield_val, str) else ''}</div>
        <div class="metric-meta">{treasury.get('date', '')}</div>
      </div>
      <div class="metric-card mc-dxy">
        <div class="metric-label">💵 DXY 美元指数</div>
        <div class="metric-value">{dxy_val if isinstance(dxy_val, str) else f'{dxy_val:.2f}'}</div>
        <div class="metric-meta">{dxy.get('note', '')} · {dxy.get('date', '')}</div>
      </div>
      <div class="metric-card mc-vix">
        <div class="metric-label">😱 VIX 恐慌指数</div>
        <div class="metric-value">{vix_val if (vix_val is None or isinstance(vix_val, str)) else f'{vix_val:.1f}'}</div>
        <div class="metric-meta">{vix.get('date', '')}</div>
      </div>
    </div>

    <!-- 汇率走势图 -->
    <div class="chart-section">
      <div class="section-title">USD/CNY 近14日走势</div>
      <div class="chart-stats">
        <div class="chart-stat">
          <span class="chart-stat-label">当前</span>
          <span class="chart-stat-val" style="color:var(--accent)">{rate_val if isinstance(rate_val, str) else f'{rate_val:.4f}'}</span>
        </div>
        <div class="chart-stat">
          <span class="chart-stat-label">30日均值</span>
          <span class="chart-stat-val">{avg_30d if isinstance(avg_30d, str) else f'{avg_30d:.4f}'}</span>
        </div>
        <div class="chart-stat">
          <span class="chart-stat-label">30日最高</span>
          <span class="chart-stat-val" style="color:var(--danger)">{max_30d if isinstance(max_30d, str) else f'{max_30d:.4f}'}</span>
        </div>
        <div class="chart-stat">
          <span class="chart-stat-label">30日最低</span>
          <span class="chart-stat-val" style="color:var(--accent2)">{min_30d if isinstance(min_30d, str) else f'{min_30d:.4f}'}</span>
        </div>
      </div>
      <div class="chart-container">
        <canvas id="rateChart"></canvas>
      </div>
    </div>

    <!-- 换汇建议 -->
    <div class="suggests-section">
      <div class="section-title">综合换汇分析建议</div>
      {suggestion_cards}
    </div>

    <!-- 历史汇率 -->
    <div class="two-col">
      <div class="table-section">
        <div class="section-title">近10日 USD/CNY 汇率</div>
        <table>
          <thead><tr>
            <th>日期</th>
            <th>汇率</th>
            <th>变动</th>
          </tr></thead>
          <tbody>{history_rows}</tbody>
        </table>
      </div>

      <div class="table-section">
        <div class="section-title">宏观指标说明</div>
        <table>
          <thead><tr><th>指标</th><th>参考区间</th></tr></thead>
          <tbody>
            <tr>
              <td>USD/CNY</td>
              <td>6.8–7.4 正常区间</td>
            </tr>
            <tr>
              <td>10Y 美债</td>
              <td>&lt;3.5% 偏低 / &gt;4.5% 偏高</td>
            </tr>
            <tr>
              <td>DXY</td>
              <td>&lt;100 偏弱 / &gt;105 偏强</td>
            </tr>
            <tr>
              <td>VIX</td>
              <td>&lt;20 平静 / 20-30 波动 / &gt;30 恐慌</td>
            </tr>
            <tr>
              <td>换汇时机</td>
              <td>低VIX + 低DXY = 相对有利</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 免责声明 -->
    <div class="disclaimer">
      ⚠️ <strong>免责声明：</strong>本报告由系统自动生成，所有内容仅供参考，不构成任何投资建议或换汇指导。汇率受宏观经济、政策变化、突发事件等多重因素影响，过去数据不代表未来走势。请结合自身实际情况、资金需求及风险承受能力做出决策，必要时咨询专业金融顾问。
    </div>

    <div class="footer">
      <span>ExchangeRate-API</span>·
      <span>FRED (St. Louis Fed)</span>·
      <span>Alpha Vantage</span>·
      <span>Nasdaq Data Link (CBOE VIX)</span>
    </div>
  </div>

  <script>
    const ctx = document.getElementById('rateChart').getContext('2d');
    const labels = {chart_labels_js};
    const data = {chart_data_js};
    
    const gradient = ctx.createLinearGradient(0, 0, 0, 180);
    gradient.addColorStop(0, 'rgba(129, 140, 248, 0.25)');
    gradient.addColorStop(1, 'rgba(129, 140, 248, 0)');

    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{
          label: 'USD/CNY',
          data: data,
          borderColor: '#818cf8',
          backgroundColor: gradient,
          borderWidth: 2,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointBackgroundColor: '#818cf8',
          pointBorderColor: '#0f0f13',
          pointBorderWidth: 2,
          fill: true,
          tension: 0.4,
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            backgroundColor: '#1e1e28',
            borderColor: 'rgba(129,140,248,0.3)',
            borderWidth: 1,
            titleColor: '#e8e8f0',
            bodyColor: '#818cf8',
            titleFont: {{ family: 'DM Sans', size: 11 }},
            bodyFont: {{ family: 'JetBrains Mono', size: 13, weight: '600' }},
            padding: 10,
          }}
        }},
        scales: {{
          x: {{
            grid: {{ color: 'rgba(255,255,255,0.04)' }},
            ticks: {{ color: '#7b7b8d', font: {{ size: 10 }} }}
          }},
          y: {{
            grid: {{ color: 'rgba(255,255,255,0.04)' }},
            ticks: {{
              color: '#7b7b8d',
              font: {{ family: 'JetBrains Mono', size: 10 }},
              callback: v => v.toFixed(3)
            }}
          }}
        }}
      }}
    }});
  </script>
</body>
</html>"""
    return html


def main():
    print("=" * 50)
    print("  📊 每日汇率观察报告生成器")
    print("=" * 50)

    if USE_REAL_API:
        print("\n🔄 正在从真实API获取数据...")
        print("  ⬇ USD/CNY 汇率...")
        usdcny = get_usdcny()
        print("  ⬇ 历史汇率（30日）...")
        history = get_usdcny_history()
        print("  ⬇ 美债收益率 (FRED)...")
        treasury = get_treasury_yield()
        print("  ⬇ DXY美元指数 (Alpha Vantage)...")
        dxy = get_dxy()
        print("  ⬇ VIX恐慌指数 (Nasdaq)...")
        vix = get_vix()
    else:
        print("\n📊 使用演示数据生成报告...")
        usdcny, history, treasury, dxy, vix = get_demo_data()

    # 如果真实API失败，填充演示数据
    if usdcny.get("status") in ("error", "mock") and treasury.get("status") == "error":
        print("  ⚠️  部分API连接失败，使用演示数据补充...")
        demo = get_demo_data()
        if usdcny.get("status") in ("error", "mock"):
            usdcny, history = demo[0], demo[1]
        if treasury.get("status") == "error":
            treasury = demo[2]
        if dxy.get("status") == "error":
            dxy = demo[3]
        if vix.get("status") == "error":
            vix = demo[4]

    print("\n  🧮 正在生成分析建议...")
    try:
        from fetch_data import analyze
    except ImportError:
        from report import _analyze as analyze
    analysis = analyze(usdcny, history, treasury, dxy, vix)

    print("  🎨 正在生成HTML报告...")
    html = generate_html(usdcny, history, treasury, dxy, vix, analysis)

    filename = f"fx_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅ 报告已生成：{filename}")
    print("   👆 双击该文件用浏览器打开即可查看！\n")
    print("📈 数据摘要：")
    print(f"   USD/CNY  : {usdcny.get('rate', 'N/A')}")
    print(f"   10Y 美债  : {treasury.get('yield', 'N/A')}%")
    print(f"   DXY      : {dxy.get('dxy', 'N/A')}")
    print(f"   VIX      : {vix.get('vix', 'N/A')}")
    print(f"   风险等级  : {analysis['risk_level']} ({analysis.get('risk_score', 50)}分)")

def _analyze(usdcny, history, treasury, dxy, vix):
    """内嵌分析函数（当fetch_data不可用时）"""
    suggestions = []
    risk_score = 50

    vix_val = vix.get("vix")
    if vix_val:
        if vix_val > 30:
            risk_score += 25
            suggestions.append({"icon": "⚠️", "title": "市场恐慌情绪浓厚",
                "content": f"VIX={vix_val:.1f}（高恐慌），建议分批换汇，避免一次性大额操作。"})
        elif vix_val > 20:
            risk_score += 10
            suggestions.append({"icon": "📊", "title": "市场存在一定波动",
                "content": f"VIX={vix_val:.1f}，市场不确定性上升，建议控制单次换汇金额。"})
        else:
            risk_score -= 10
            suggestions.append({"icon": "✅", "title": "市场情绪稳定",
                "content": f"VIX={vix_val:.1f}，市场波动较小，换汇时机相对稳定。"})

    yield_val = treasury.get("yield")
    if yield_val:
        if yield_val > 4.5:
            suggestions.append({"icon": "📈", "title": "美债收益率高位",
                "content": f"10Y美债={yield_val:.2f}%，美元资产吸引力强，USD/CNY可能维持高位。"})
        elif yield_val < 3.5:
            suggestions.append({"icon": "📉", "title": "美债收益率偏低",
                "content": f"10Y美债={yield_val:.2f}%，美元走弱压力上升，可适当提前换汇。"})
        else:
            suggestions.append({"icon": "📊", "title": "美债收益率中性",
                "content": f"10Y美债={yield_val:.2f}%，处于中性区间，关注后续美联储政策。"})

    rate = usdcny.get("rate")
    if history and len(history) >= 7 and rate:
        avg_30d = sum(h["rate"] for h in history) / len(history)
        pct = (rate - avg_30d) / avg_30d * 100
        if rate > avg_30d * 1.005:
            suggestions.append({"icon": "💹", "title": "美元偏强，高于均值",
                "content": f"当前{rate:.4f}，30日均值{avg_30d:.4f}（偏高{pct:+.2f}%），若需换人民币时机尚可。"})
        elif rate < avg_30d * 0.995:
            suggestions.append({"icon": "💹", "title": "美元偏弱，低于均值",
                "content": f"当前{rate:.4f}，30日均值{avg_30d:.4f}（偏低{pct:+.2f}%），若需换美元时机较佳。"})
        else:
            suggestions.append({"icon": "💹", "title": "汇率处于均值附近",
                "content": f"当前{rate:.4f}，30日均值{avg_30d:.4f}，汇率平稳，可按需换汇。"})

    risk_score = min(100, max(0, risk_score))
    if risk_score >= 70: rl = "高"
    elif risk_score >= 40: rl = "中等"
    else: rl = "低"
    return {"suggestions": suggestions, "risk_level": rl, "risk_score": risk_score}

if __name__ == "__main__":
    main()
