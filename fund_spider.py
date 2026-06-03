import requests
import json
import os
from datetime import datetime

# ====================================================
# 💰 你的 8 支基础持仓配置
# ====================================================
MY_POSITIONS = {
    "000216": {"name": "华安黄金ETF联接A", "track_code": "sh518880", "shares": 10000.0, "cost_price": 1.0300, "is_domestic": True},
    "007671": {"name": "摩根标普500指数(QDII)A", "track_code": "sh513500", "shares": 5000.0, "cost_price": 1.2500, "is_domestic": False},
    "004342": {"name": "天弘纳斯达克100指数(QDII)A", "track_code": "sh513100", "shares": 8000.0, "cost_price": 1.4200, "is_domestic": False},
    "110026": {"name": "易方达创业板ETF联接A", "track_code": "sz159915", "shares": 12000.0, "cost_price": 1.8500, "is_domestic": True},
    "110020": {"name": "易方达沪深300ETF联接A", "track_code": "sh510300", "shares": 15000.0, "cost_price": 2.1500, "is_domestic": True},
    "011608": {"name": "易方达科创50联接A", "track_code": "sh588000", "shares": 6000.0, "cost_price": 0.9500, "is_domestic": True},
    "002736": {"name": "易方达中证500ETF联接A", "track_code": "sh510500", "shares": 7000.0, "cost_price": 1.3500, "is_domestic": True},
    "009051": {"name": "易方达中证红利ETF联接A", "track_code": "sh515180", "shares": 10000.0, "cost_price": 1.1000, "is_domestic": True}
}

TRANSACTION_LOGS = [] # 留空，等待后续你发给我统一追加

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
            if len(parts) >= 4:
                official_nav = float(parts[1])
                official_yesterday_nav = float(parts[3])
    except Exception as e:
        print(f"异常 {fund_code}: {e}")

    if is_domestic:
        try:
            url_stock = f"http://qt.gtimg.cn/q={track_code}"
            res_stock = requests.get(url_stock, headers=headers, timeout=5)
            res_stock.encoding = 'gbk'
            if '~' in res_stock.text:
                parts = res_stock.text.split('"')[1].split('~')
                current_price = float(parts[2])
                yesterday_close = float(parts[3])
                if yesterday_close > 0:
                    daily_growth = ((current_price - yesterday_close) / yesterday_close) * 100
        except Exception as e:
            print(f"异常 {track_code}: {e}")
    else:
        daily_growth = 0.0

    estimated_nav = official_nav * (1 + daily_growth / 100)
    return {"official_nav": official_nav, "official_yesterday_nav": official_yesterday_nav, "estimated_nav": estimated_nav, "daily_growth": daily_growth}

# 👑 核心新增：WxPusher 微信发送模块，读取 GitHub 保险箱数据
def push_to_wechat(summary_est, position_list):
    app_token = os.environ.get("WXPUSHER_APP_TOKEN")
    uid = os.environ.get("WXPUSHER_UID")
    
    if not app_token or not uid:
        print("⚠️ GitHub 保险箱中未检测到 WxPusher 凭证，跳过微信推送。")
        return

    # 制作精美的 HTML 微信推文卡片排版
    time_str = datetime.now().strftime("%m-%d %H:%M")
    color_dp = "#ef4444" if summary_est['daily_profit'] >= 0 else "#22c55e"
    sign_dp = "+" if summary_est['daily_profit'] >= 0 else ""
    
    html_content = f"""
    <div style="font-family: sans-serif; padding: 10px; background-color: #f8fafc;">
        <h3 style="color: #0f172a; margin-bottom: 5px;">📊 14:30 盘中动态资产快报</h3>
        <p style="font-size: 11px; color: #64748b; margin-top:0;">生成时间: {time_str}</p>
        
        <div style="background: #0f172a; color: #fff; padding: 15px; rounded-corners: 8px; border-radius: 8px; margin-bottom: 15px;">
            <div style="font-size: 12px; color: #94a3b8;">估算总资产 (元)</div>
            <div style="font-size: 24px; font-weight: bold; margin: 5px 0;">￥{summary_est['total_value']:,.2f}</div>
            <div style="font-size: 13px; color: {color_dp}; font-weight: bold;">
                今日动态预计损益: {sign_dp}{summary_est['daily_profit']:,.2f}
            </div>
        </div>
        
        <h4 style="color: #334155; margin-bottom: 8px;">📋 A股标的实时估值明细:</h4>
        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
    """
    
    for pos in position_list:
        if pos['is_domestic']:
            p_color = "#ef4444" if "-" not in pos['daily_growth'] and pos['daily_growth'] != "0.0%" else "#22c55e"
            html_content += f"""
            <tr style="border-b: 1px solid #e2e8f0; height: 35px;">
                <td style="color: #1e293b; font-weight: bold;">{pos['name']}</td>
                <td style="text-align: right; color: {p_color}; font-weight: bold;">{pos['daily_growth']}</td>
                <td style="text-align: right; color: #475569; font-weight: bold;">￥{pos['estimated_value']:,.0f}</td>
            </tr>
            """
            
    html_content += """
        </table>
        <p style="font-size: 11px; color: #94a3b8; margin-top: 15px; text-align: center;">💡 提示：美股标的时差已在推送中自动隐藏</p>
    </div>
    """

    url = "https://wxpusher.zjiecode.com/api/send/message"
    payload = {
        "appToken": app_token,
        "content": html_content,
        "contentType": 2, # 代表 HTML 格式
        "uids": [uid]
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        print("微信投递结果日志:", res.json())
    except Exception as e:
        print("微信推送失败:", e)

def update_dashboard_data():
    est_total_value, est_total_cost, est_daily_profit = 0, 0, 0
    off_total_value, off_total_cost, off_daily_profit = 0, 0, 0
    position_list = []

    for code, info in MY_POSITIONS.items():
        data = get_data(code, info['track_code'], info['is_domestic'])
        cost = info['shares'] * info['cost_price']
        
        if info['is_domestic']:
            est_val = info['shares'] * data['estimated_nav']
            est_day_prof = est_val * (data['daily_growth'] / (100 + data['daily_growth'])) if (100 + data['daily_growth']) != 0 else 0
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
            "estimated_nav": round(data['estimated_nav'], 4) if info['is_domestic'] else round(data['official_nav'], 4),
            "daily_growth": est_growth_str, "estimated_value": round(est_val, 2), "estimated_profit": round(est_prof, 2),
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
        
    # 🚀 执行推送
    push_to_wechat(summary_est, position_list)
    print("🎉 过滤美股版双轨数据重构并推送成功！")

if __name__ == "__main__":
    update_dashboard_data()
