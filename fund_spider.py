import requests
import json
import re
from datetime import datetime

# ====================================================
# 💰 以后你只需要在这里修改你的基金和持仓（先用我的模板测试）
# 格式: "基金代码": {"name": "基金名称", "shares": 持仓份额, "cost_price": 买入成本价}
# ====================================================
MY_POSITIONS = {
    "001508": {"name": "富国富钱包货币", "shares": 10000.0, "cost_price": 1.0000},
    "161725": {"name": "招商中证白酒指数", "shares": 5000.0, "cost_price": 1.2500}
}

def get_fund_realtime_data(fund_code):
    url = f"http://fundgz.1234567.cn/js/{fund_code}.js"
    try:
        response = requests.get(url, timeout=5)
        match = re.search(r'jsonpgz\((.*)\);', response.text)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        print(f"获取基金 {fund_code} 失败: {e}")
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
    print("数据更新成功！")

if __name__ == "__main__":
    update_dashboard_data()
