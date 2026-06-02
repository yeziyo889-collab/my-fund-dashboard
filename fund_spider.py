import requests
import json
from datetime import datetime

# ====================================================
# 💰 你的真实持仓配置（以后随时在这里修改数字即可）
# 格式: "基金代码": {"name": "自定义看板显示的名称", "shares": 持仓份额, "cost_price": 买入成本均价}
# ====================================================
MY_POSITIONS = {
    "161725": {"name": "招商中证白酒指数", "shares": 5000.0, "cost_price": 1.2500},
    "320007": {"name": "诺安成长混合", "shares": 3000.0, "cost_price": 1.0000}
}

def get_fund_realtime_data(fund_code):
    # 👑 改用新浪财经接口，对海外云服务器极度友好，绝不拦截
    url = f"https://hq.sinajs.cn/list=f_{fund_code}"
    headers = {
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'gbk' # 防止中文乱码
        
        text = response.text
        if '"' in text:
            content = text.split('"')[1]
            if content:
                data_list = content.split(',')
                if len(data_list) >= 5:
                    return {
                        "current_nav": float(data_list[1]),   # 当前最新估值
                        "yesterday_nav": float(data_list[3]), # 昨日单位净值
                    }
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
        if not data or data['current_nav'] == 0:
            print(f"⚠️ 基金 {code} 接口未返回有效数据，跳过")
            continue
        
        current_nav = data['current_nav']
        yesterday_nav = data['yesterday_nav']
        
        if yesterday_nav > 0:
            daily_growth = ((current_nav - yesterday_nav) / yesterday_nav) * 100
        else:
            daily_growth = 0.0
        
        cost = info['shares'] * info['cost_price']
        value = info['shares'] * current_nav
        profit = value - cost
        fund_daily_profit = info['shares'] * (current_nav - yesterday_nav)
        
        total_value += value
        total_cost += cost
        daily_profit += fund_daily_profit
        
        position_list.append({
            "code": code,
            "name": info['name'], 
            "shares": info['shares'],
            "cost_price": info['cost_price'],
            "current_nav": current_nav,
            "daily_growth": f"{round(daily_growth, 2)}%",
            "value": round(value, 2),
            "profit": round(profit, 2)
        })

    if not position_list:
        print("⚠️ 未能成功从新浪财经抓取到任何有效持仓，本次不更新文件")
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
    print("🎉 新浪财经数据源全自动更新成功！")

if __name__ == "__main__":
    update_dashboard_data()
