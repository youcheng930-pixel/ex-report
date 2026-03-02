import requests
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime, timedelta
from config import FRED_API_KEY, ALPHA_VANTAGE_KEY, NASDAQ_API_KEY

def get_usdcny():
    try:
        url = "https://api.frankfurter.app/latest?from=USD&to=CNY"
        r = requests.get(url, timeout=10)
        data = r.json()
        rate = data["rates"]["CNY"]
        return {"rate": round(rate, 4), "date": data["date"], "status": "ok"}
    except:
        pass
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        r = requests.get(url, timeout=10)
        data = r.json()
        rate = data["rates"]["CNY"]
        return {"rate": round(rate, 4), "date": data["date"], "status": "ok"}
    except Exception as e:
        return {"rate": None, "date": "", "status": "error", "error": str(e)}

def get_usdcny_history():
    try:
        today = datetime.now()
        start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
        url = f"https://api.frankfurter.app/{start}..{end}?from=USD&to=CNY"
        r = requests.get(url, timeout=10)
        data = r.json()
        history = []
        for date, rates in sorted(data["rates"].items()):
            history.append({"date": date, "rate": round(rates["CNY"], 4)})
        return history
    except Exception as e:
        return []

def get_treasury_yield():
    try:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id=DGS10"
            f"&api_key={FRED_API_KEY}"
            f"&sort_order=desc"
            f"&limit=5"
            f"&file_type=json"
        )
        r = requests.get(url, timeout=10)
        data = r.json()
        obs = [o for o in data["observations"] if o["value"] != "."]
        latest = obs[0]
        return {"yield": float(latest["value"]), "date": latest["date"], "status": "ok"}
    except Exception as e:
        return {"yield": None, "date": "", "status": "error", "error": str(e)}

def get_dxy():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?interval=1d&range=3d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        timestamps = result["timestamp"]
        valid = [(t, c) for t, c in zip(timestamps, closes) if c is not None]
        if not valid:
            raise ValueError("No valid DXY data")
        latest = valid[-1]
        date = datetime.fromtimestamp(latest[0]).strftime("%Y-%m-%d")
        return {"dxy": round(float(latest[1]), 2), "date": date, "note": "DX-Y.NYB", "status": "ok"}
    except Exception as e:
        return {"dxy": None, "date": "", "status": "error", "error": str(e)}
def get_vix():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=3d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        highs = result["indicators"]["quote"][0]["high"]
        lows = result["indicators"]["quote"][0]["low"]
        timestamps = result["timestamp"]
        valid = [(t, c, h, l) for t, c, h, l in zip(timestamps, closes, highs, lows) if c is not None]
        if not valid:
            raise ValueError("No valid VIX data")
        latest = valid[-1]
        date = datetime.fromtimestamp(latest[0]).strftime("%Y-%m-%d")
        return {"vix": round(float(latest[1]), 2), "vix_high": round(float(latest[2]), 2), "vix_low": round(float(latest[3]), 2), "date": date, "status": "ok"}
    except Exception as e:
        return {"vix": None, "date": "", "status": "error", "error": str(e)}

def analyze(usdcny, history, treasury, dxy, vix):
    suggestions = []
    risk_score = 50

    vix_val = vix.get("vix")
    if vix_val:
        if vix_val > 30:
            risk_score += 25
            suggestions.append({"icon": "⚠️", "title": "市场恐慌情绪浓厚",
                "content": f"VIX恐慌指数 {vix_val:.1f}（>30为高恐慌区间），市场剧烈波动。建议分批换汇，避免一次性大额操作。"})
        elif vix_val > 20:
            risk_score += 10
            suggestions.append({"icon": "📊", "title": "市场存在一定波动",
                "content": f"VIX={vix_val:.1f}（20-30为中等波动），市场不确定性上升，建议控制单次换汇金额。"})
        else:
            risk_score -= 10
            suggestions.append({"icon": "✅", "title": "市场情绪稳定",
                "content": f"VIX={vix_val:.1f}（<20为平静区间），市场波动较小，换汇时机相对稳定。"})

    yield_val = treasury.get("yield")
    if yield_val:
        if yield_val > 4.5:
            risk_score += 10
            suggestions.append({"icon": "📈", "title": "美债收益率处于高位",
                "content": f"10年期美债收益率 {yield_val:.2f}%（偏高），美元资产吸引力强，USD/CNY可能维持高位。"})
        elif yield_val < 3.5:
            risk_score -= 10
            suggestions.append({"icon": "📉", "title": "美债收益率偏低",
                "content": f"10年期美债收益率 {yield_val:.2f}%（偏低），美元走弱压力上升，可考虑观望或提前兑换。"})
        else:
            suggestions.append({"icon": "📊", "title": "美债收益率处于中性区间",
                "content": f"10年期美债收益率 {yield_val:.2f}%，处于3.5%-4.5%中性区间，对汇率影响中性。"})

    rate = usdcny.get("rate")
    if history and len(history) >= 10 and rate:
        rates_30d = [h["rate"] for h in history]
        avg_30d = sum(rates_30d) / len(rates_30d)
        max_30d = max(rates_30d)
        min_30d = min(rates_30d)
        pct = (rate - avg_30d) / avg_30d * 100
        if rate > avg_30d * 1.005:
            suggestions.append({"icon": "💹", "title": "美元近期偏强",
                "content": f"当前汇率 {rate:.4f}，30日均值 {avg_30d:.4f}（偏高 {pct:+.2f}%），区间[{min_30d:.4f}, {max_30d:.4f}]。美元处于相对高位，若需换成人民币时机尚可。"})
        elif rate < avg_30d * 0.995:
            suggestions.append({"icon": "💹", "title": "美元近期偏弱",
                "content": f"当前汇率 {rate:.4f}，30日均值 {avg_30d:.4f}（偏低 {pct:+.2f}%），区间[{min_30d:.4f}, {max_30d:.4f}]。美元处于相对低位，若需换成美元时机较佳。"})
        else:
            suggestions.append({"icon": "💹", "title": "汇率处于均值附近",
                "content": f"当前汇率 {rate:.4f}，30日均值 {avg_30d:.4f}（偏差 {pct:+.2f}%），汇率较平稳，可按需换汇。"})

    dxy_val = dxy.get("dxy")
    if dxy_val:
        if dxy_val > 105:
            suggestions.append({"icon": "💵", "title": "美元指数强势",
                "content": f"DXY={dxy_val}（>105为强势），美元对一篮子货币偏强，人民币面临贬值压力。"})
        elif dxy_val < 100:
            suggestions.append({"icon": "💵", "title": "美元指数偏弱",
                "content": f"DXY={dxy_val}（<100为偏弱），美元整体走弱，人民币相对受支撑。"})
        else:
            suggestions.append({"icon": "💵", "title": "美元指数中性",
                "content": f"DXY={dxy_val}，处于100-105中性区间，美元强弱适中。"})

    risk_score = min(100, max(0, risk_score))
    if risk_score >= 70: rl = "高"
    elif risk_score >= 40: rl = "中等"
    else: rl = "低"
    return {"suggestions": suggestions, "risk_level": rl, "risk_score": risk_score}

if __name__ == "__main__":
    print("测试数据获取...")
    print("USD/CNY:", get_usdcny())
    print("History:", get_usdcny_history()[-3:])
    print("Treasury:", get_treasury_yield())
    print("DXY:", get_dxy())
    print("VIX:", get_vix())