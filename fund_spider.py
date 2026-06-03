import requests
import json
import os
from datetime import datetime

# ====================================================
# 💰 你的 8 支真实指数化基金持仓配置（全线精准对齐官方代码）
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

TRANSACTION_LOGS = [] # 个人买卖记录留空，等待你随时发我追加

def get_data(fund_code, track_code, is_domestic):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    official_nav = 1.0
    official_yesterday_nav = 1.0
    daily_growth = 0.0

    # 1. 安全抓取场外官方最新已公开净值
    try:
        url_jj = f"http://qt.gtimg.cn/q=jj{fund_code}"
        res_jj = requests.get(url_jj, headers=headers, timeout=5)
        res_jj.encoding = 'gbk'
        if '~' in res_jj.text:
            parts = res_jj.text.split('"')[1].split('~')
            if len(parts) >= 3:
                # 🛡️ 逻辑修正：parts[0]是代码，parts[1]是中文名，parts[2]才是真正的单位净值数字
                official_nav = float(parts[2])
            
            # 尝试安全抓取前一日净值，防范非数字异常
            if len(parts) >= 5:
                try:
                    official_yesterday_nav = float(parts[4])
                except ValueError:
                    official_yesterday_nav = official_nav
            else:
                official_yesterday_nav = official_nav
    except Exception as e:
        print(f"⚠️ 场外官方数据解析提示 ({fund_code}): {e}")

    # 2. 联动场内动态涨跌幅
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
            print(f"⚠️ 场内影子网路同步提示 ({track_code}): {e}")
    else:
        daily_growth = 0.0  # 海外QDII在14:30保持静态资产

    estimated_nav = official_nav * (1 + daily_growth / 100)
    return {
        "official_nav": official_nav, 
        "official_yesterday_nav": official_yesterday_nav, 
        "estimated_nav": estimated_nav, 
        "daily_growth": daily_growth
    }

def push_to_wechat(summary_est, position_list):
    app_token = os.environ.get("WXPUSHER_APP_TOKEN")
    uid = os.environ.get("WXPUSHER_UID")
    
    if not app_token or not uid:
        print("⚠️ 未检测到加密密钥，跳过微信推送流程。")
        return

    time_str = datetime.now().strftime("%m-%d %H:%M")
    color_dp = "#ef4444" if summary_est['daily_profit'] >= 0 else "#22c55e"
    sign_dp = "+" if summary_est['daily_profit'] >= 0 else ""
    
    html_content = f"""
    <div style="font-family: sans-serif; padding: 12px; background-color: #f8fafc; border-radius: 10px;">
        <h3 style="color: #0f172a; margin-bottom: 4px; font-size: 16px;">📊 14:30 盘中资产动态快报</h3>
        <p style="font-size: 11px; color: #64748b; margin-top:0; margin-bottom:12px;">同步时间: {time_str}</p>
        
        <div style="background: #1e293b; color: #fff; padding: 16px; border-radius: 8px; margin-bottom: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <div style="font-size: 12px; color: #cbd5e1;">预估总资产 (元)</div>
            <div style="font-size: 26px; font-weight: bold; margin: 6px 0; font-family: monospace;">￥{summary_est['total_value']:,.2f}</div>
            <div style="font-size: 13px; color: {color_dp}; font-weight: bold;">
                今日预计损益: {sign_dp}{summary_est['daily_profit']:,.2f}
            </div>
        </div>
        
        <h4 style="color: #475569; margin-bottom: 6px; font-size: 13px;">📋 A股持仓实时估值明细:</h4>
        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
    """
    
    for pos in position_list:
        if pos['is_domestic']:
            p_color = "#ef4444" if "-" not in pos['daily_growth'] and pos['daily_growth'] != "0.0%" else "#22c55e"
            html_content += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; height: 36px;">
                <td style="color: #334155; font-weight: bold;">{pos['name']}</td>
                <td style="text-align: right; color: {p_color}; font-weight: bold; font-family: monospace; width: 70px;">{pos['daily_growth']}</td>
                <td style="text-align: right; color: #1e293b; font-weight: bold; font-family: monospace; width: 90px;">￥{pos['estimated_value']:,.0f}</td>
            </tr>
            """
            
    html_content += """
        </table>
        <p style="font-size: 10px; color: #94a3b8; margin-top: 16px; text-align: center; font-style: italic;">💡 提示：美股QDII时差已在14:30推送中自动隐藏</p>
    </div>
    """

    url = "https://wxpusher.zjiecode.com/api/send/message"
    payload = {
        "appToken": app_token,
        "content": html_content,
        "contentType": 2, 
        "uids": [uid]
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        print("微信投递结果日志:", res.json())
    except Exception as e:
        print("微信推送网络异常:", e)

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
            "estimated_nav": round(data['estimated_nav'], 4),
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
        
    push_to_wechat(summary_est, position_list)

if __name__ == "__main__":
    update_dashboard_data()
