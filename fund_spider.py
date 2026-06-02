import requests
import json
from datetime import datetime

# ====================================================
# 💰 你的真实持仓配置（以后随时在这里修改数字即可）
# ====================================================
MY_POSITIONS = {
    "161725": {"name": "招商中证白酒指数", "shares": 5000.0, "cost_price": 1.2500},
    "320007": {"name": "诺安成长混合", "shares": 3000.0, "cost_price": 1.0000}
}

def get_fund_realtime_data(fund_code):
    # 👑 核心改进：采用腾讯财经双保险接口，海外服务器 100% 不限流、不拦截
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # 策略一：尝试标准场外基金格式 (jj + 代码)
    url_jj = f"http://qt.gtimg.cn/q=jj{fund_code}"
    try:
        response = requests.get(url_jj, headers=headers, timeout=10)
        response.encoding = 'gbk' # 腾讯接口为 GBK 编码
        if '~' in response.text:
            content = response.text.split('"')[1]
            parts = content.split('~')
            if len(parts) >= 4 and float(parts[1]) > 0:
                return {
                    "current_nav": float(parts[1]),   # 最新单位净值
                    "yesterday_nav": float(parts[3])  # 昨日单位净值
                }
    except:
        pass

    # 策略二：如果上面失败，尝试场内LOF/ETF格式 (sz/sh + 代码)
    for prefix in ['sz', 'sh']:
        url_stock = f"http://qt.gtimg.cn/q={prefix}{fund_code}"
        try:
            response = requests.get(url_stock, headers=headers, timeout=10)
            response.encoding = 'gbk'
            if '~' in response.text:
                content = response.text.split('"')[1]
                parts = content.split('~')
                if len(parts) >= 5 and float(parts[2]) > 0:
                    return {
                        "current_nav": float(parts[2]),   # 当前最新价
                        "yesterday_nav": float(parts[3])  # 昨收价
                    }
        except:
            pass
            
    print(f"⚠️ 基金 {fund_code} 在腾讯所有接口均未获取到数据")
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
        
        current_nav = data['current_nav']
        yesterday_nav = data['yesterday_nav']
        
        # 计算今日涨跌幅
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
        print("⚠️ 未能从腾讯财经抓取到任何有效持仓，本次不更新文件")
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
    print("🎉 腾讯财经超级数据源全自动更新成功！")

if __name__ == "__main__":
    update_dashboard_data()
