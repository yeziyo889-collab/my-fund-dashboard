import requests
import json
import os
from datetime import datetime, timedelta, timezone

# ====================================================
# 💰 你的 8 支指数化基金持仓配置
# ====================================================
MY_POSITIONS = {
    "000216": {"name": "华安黄金ETF联接A", "track_code": "sh518880", "shares": 10000.0, "cost_price": 1.0300, "is_domestic": True},
    "017641": {"name": "摩根标普500指数(QDII)A", "track_code": "sh513500", "shares": 5000.0, "cost_price": 1.2500, "is_domestic": False},
    "018043": {"name": "天弘纳斯达克100指数(QDII)A", "track_code": "sh513100", "shares": 8000.0, "cost_price": 1.4200, "is_domestic": False},
    "110026": {"name": "易方达创业板ETF联接A", "track_code": "sz159915", "shares": 12000.0, "cost_price": 1.8500, "is_domestic": True},
    "110020": {"name": "易方达沪深300ETF联接A", "track_code": "sh510300", "shares": 15000.0, "cost_price": 2.1500, "is_domestic": True},
    "011608": {"name": "易方达科创50联接A", "track_code": "sh588000", "shares": 6000.0, "cost_price": 0.9500, "is_domestic": True},
    "007028": {"name": "易方达中证500ETF联接A", "track_code": "sh510500", "shares": 7000.0, "cost_price": 1.3500, "is_domestic": True},
    "009051": {"name": "易方达中证红利ETF联接A", "track_code": "sh515180", "shares": 10000.0, "cost_price": 1.1000, "is_domestic": True}
}

TRANSACTION_LOGS = [] # 个人买卖记录留空

def get_data(fund_code, track_code, is_domestic):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    official_nav = 1.0
    official_yesterday_nav = 1.0
    daily_growth = 0.0

    try:
        url_jj = f"http://qt.gtimg.cn/q=jj{fund_code}"
        res_jj = requests.get(url_jj, headers=headers, timeout=5)
        res_jj.encoding = 'gbk'
        if '~' in res_jj.text:
            parts = res_jj.text.split('"')[1].split('~')
            
            valid_navs = []
            for p in parts[2:]:
                try:
                    val = float(p)
                    if 0.1 < val < 100.0:
                        valid_navs.append(val)
                except ValueError:
                    continue
            
            if len(valid_navs) >= 1:
                official_nav = valid_navs[0]
                official_yesterday_nav = valid_navs[1] if len(valid_navs) >= 2 else official_nav
    except Exception as e:
        print(f"⚠️ 场外官方数据解析提示 ({fund_code}): {e}")

    if is_domestic:
        try:
            url_stock = f"http://qt.gtimg.cn/q={track_code}"
            res_stock = requests.get(url_stock, headers=headers, timeout=5)
            res_stock.encoding = 'gbk'
            if '~' in res_stock.text:
                parts = res_stock.text.split('"')[1].split('~')
                if len(parts) >= 5:
                    current_price = float(parts[3])
                    yesterday_close = float(parts[4])
                    if yesterday_close > 0:
                        daily_growth = ((current_price - yesterday_close) / yesterday_close) * 100
        except Exception as e:
            print(f"⚠️ 场内影子网路同步提示 ({track_code}): {e}")
    else:
        daily_growth = 0.0

    estimated_nav = official_nav * (1 + daily_growth / 100)
    return {
        "official_nav": official_nav, 
        "official_yesterday_nav": official_yesterday_nav, 
        "estimated_nav": estimated_nav, 
        "daily_growth": daily_growth
    }

# 👑 核心改进：极致无感视觉排版 + 单基预估损益透出
def push_to_feishu(summary_est, position_list):
    webhook_url = os.environ.get("FEISHU_WEBHOOK")
    if not webhook_url:
        print("⚠️ 未检测到加密密钥，跳过飞书推送流程。")
        return

    tz_utc8 = timezone(timedelta(hours=8))
    time_str = datetime.now(tz_utc8).strftime("%m-%d %H:%M")
    
    is_profit = summary_est['daily_profit'] >= 0
    sign_dp = "+" if is_profit else ""
    header_template = "red" if is_profit else "green"
    
    # ✨ 改进点一：采用高对比度独立区块结构，消灭视觉混乱
    detail_md = ""
    for pos in position_list:
        if pos['is_domestic']:
            fund_pnl = pos['estimated_daily_profit']
            is_fund_up = fund_pnl >= 0
            
            # 使用强烈色块标志：红圆形(🔴)代表上涨，绿圆形(🟢)代表下跌
            g_icon = "🔴" if is_fund_up else "🟢"
            f_sign = "+" if is_fund_up else ""
            
            detail_md += f"{g_icon} **{pos['name']}** (`{pos['code']}`)\n"
            detail_md += f" ├ 盘中涨跌：`{pos['daily_growth']}`\n"
            detail_md += f" ├ **今日损益**：**{f_sign}￥{fund_pnl:,.2f}**\n" # 🌟 新增核心诉求：单只基金今日盈亏
            detail_md += f" └ 当前市值：`￥{pos['estimated_value']:,.0f}`\n\n"

    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "📊 14:30 盘中资产动态快报"},
                "template": header_template
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"⏱️ **同步时间**: `{time_str}` (北京/马来西亚时间)\n\n💳 **资产账户总览**:\n• 预估总资产: **￥{summary_est['total_value']:,.2f}**\n• 今日总损益: **{sign_dp}￥{summary_est['daily_profit']:,.2f}**"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"📋 **持仓精简估值看板**:\n{detail_md}"}
                },
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": "💡 提示：美股QDII标的时差已在14:30推送中自动隐藏"}]
                }
            ]
        }
    }
    
    try:
        res = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        print("飞书接口回执:", res.json())
    except Exception as e:
        print("飞书推送网络异常:", e)

def update_dashboard_data():
    est_total_value, est_total_cost, est_daily_profit = 0, 0, 0
    off_total_value, off_total_cost, off_daily_profit = 0, 0, 0
    position_list = []

    for code, info in MY_POSITIONS.items():
        data = get_data(code, info['track_code'], info['is_domestic'])
        cost = info['shares'] * info['cost_price']
        
        if info['is_domestic']:
            est_val = info['shares'] * data['estimated_nav']
            # ✨ 改进点二：底层算法完美重构，直接算出各基金当日精准预估绝对盈亏数字
            est_day_prof = info['shares'] * data['official_nav'] * (data['daily_growth'] / 100)
            est_growth_str = f"{round(data['daily_growth'], 2)}%"
        else:
            est_val = info['shares'] * data['official_nav']
            est_day_prof = 0
            est_growth_str = "-"

        est_prof = est_val - cost
        est_total_value += est_val
        est_total_cost += cost
        est_daily_profit += est_day_prof

        off_val = info['shares'] * data['official_nav']
        off_prof = off_val - cost
        off_day_prof = info['shares'] * (data['official_nav'] - data['official_yesterday_nav'])
        
        off_total_value += off_val
        off_total_cost += cost
        off_daily_profit += off_day_prof
        
        position_list.append({
            "code": code, "name": info['name'], "is_domestic": info['is_domestic'], "shares": info['shares'], "cost_price": info['cost_price'],
            "estimated_nav": round(data['estimated_nav'], 4),
            "daily_growth": est_growth_str, "estimated_value": round(est_val, 2), "estimated_profit": round(est_prof, 2),
            "estimated_daily_profit": round(est_day_prof, 2), # 🌟 新增字段向下游传递
            "official_nav": round(data['official_nav'], 4),
            "official_growth": f"{round(((data['official_nav']-data['official_yesterday_nav'])/data['official_yesterday_nav'])*100, 2)}%" if data['official_yesterday_nav'] > 0 else "0.0%",
            "official_value": round(off_val, 2), "official_profit": round(off_prof, 2)
        })

    summary_est = {"total_value": round(est_total_value, 2), "total_profit": round(est_total_value - est_total_cost, 2), "daily_profit": round(est_daily_profit, 2)}
    
    dashboard_data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary_estimated": summary_est,
        "summary_official": {"total_value": round(off_total_value, 2), "total_profit": round(off_total_value - off_total_cost, 2), "daily_profit": round(off_daily_profit, 2)},
        "positions": position_list, "transaction_logs": TRANSACTION_LOGS
    }

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=4)
        
    push_to_feishu(summary_est, position_list)
    print("🎉 飞书高保真卡片优化版交割完毕！")

if __name__ == "__main__":
    update_dashboard_data()
