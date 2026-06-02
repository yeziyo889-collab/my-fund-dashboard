import requests
import json
import re
from datetime import datetime

# ====================================================
# 💰 测试持仓：这里换成了两个一定有盘中实时估值的基金
# ====================================================
MY_POSITIONS = {
    "161725": {"name": "招商中证白酒指数", "shares": 5000.0, "cost_price": 1.2500},
    "320007": {"name": "诺安成长混合", "shares": 3000.0, "cost_price": 1.0000}
}

def get_fund_realtime_data(fund_code):
    url = f"http://fundgz.1234567.cn/js/{fund_code}.js"
    
    # 👑 核心改进：加入高级浏览器伪装和防盗链引用，防止被天天基金拦截
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://fund.eastmoney.com/",
        "Connection": "keep-alive"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"基金 {fund_code} 请求被拦截，状态码: {response.status_code}")
            return None
            
        match = re.search(r'jsonpgz\((.*)\);', response.text)
        if match:
            return json.loads(match.group(1))
        else:
            print(f"基金 {fund_code} 接口返回格式不匹配，收到内容: {response.text[:100]}")
    except Exception as e:
        print(f"获取基金 {fund_code} 异常: {e}")
    return None

def update_dashboard_data():
    total_value = 0
    total_cost = 0
    daily_profit = 0
    position_list = []

    for code, info in MY_POSITIONS.items():
        data = get_fund_realtime_data(code)
        if not data:
            continue
        
        # 安全检查：确保接口返回了估值数据
        if 'gsz' not in data or 'gszzl' not in data:
            print(f"基金 {data.get('name', code)} 当前无实时估值，跳过")
            continue

        current_nav = float(data['gsz']) # 当前估值
        daily_growth = float(data['gszzl']) # 今日涨跌幅 (%)
        
        cost = info['shares'] * info['cost_price']
        value = info['shares'] * current_nav
        profit = value - cost
        fund_daily_profit = value * (daily_growth / 100)
        
        total_value += value
        total_cost += cost
        daily_profit += fund_daily_profit
        
        position_list.append({
            "code": code,
            "name": data['name'],
            "shares": info['shares'],
            "cost_price": info['cost_price'],
            "current_nav": current_nav,
            "daily_growth": f"{daily_growth}%",
            "value": round(value, 2),
            "profit": round(profit, 2)
        })

    # 🔥 安全保护：如果全部抓取失败，不覆盖旧文件，防止把网页洗白
    if not position_list:
        print("⚠️ 未能成功抓取到任何有效的基金数据，本次不更新 data.json")
        return

    dashboard_data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_value": round(total_value, 2),
            "total_profit": round(total_value - total_cost, 2),
            "daily_profit": round(daily_profit, 2)
        },
        "positions": position_list
    }

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=4)
    print("🎉 恭喜！数据成功更新并写入 data.json！")

if __name__ == "__main__":
    update_dashboard_data()
