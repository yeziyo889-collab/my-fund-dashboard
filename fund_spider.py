import requests
import json
import os
import csv
from datetime import datetime, timedelta, timezone

# ====================================================
# 🏛️ 6支国内核心资产费率规则、影子代码与自动定投计划字典
# ====================================================
FEE_RULES = {
    "011608": {
        "name": "易方达科创50联接A", "track_code": "sh588000", "is_domestic": True,
        "buy_fee": 0.0006, "dca_amount": 750.0, "dca_day": 10, "target_annual_rate": 0.10,
        "sell_rules": [(7, 0.015), (30, 0.005), (180, 0.001), (float('inf'), 0.0)]
    },
    "110026": {
        "name": "易方达创业板ETF联接A", "track_code": "sz159915", "is_domestic": True,
        "buy_fee": 0.0012, "dca_amount": 750.0, "dca_day": 10, "target_annual_rate": 0.10,
        "sell_rules": [(7, 0.015), (30, 0.005), (180, 0.001), (float('inf'), 0.0)]
    },
    "110020": {
        "name": "易方达沪深300ETF联接A", "track_code": "sh510300", "is_domestic": True,
        "buy_fee": 0.0012, "dca_amount": 500.0, "dca_day": 10, "target_annual_rate": 0.08,
        "sell_rules": [(7, 0.015), (365, 0.005), (730, 0.025), (float('inf'), 0.0)]
    },
    "007028": {
        "name": "易方达中证500ETF联接A", "track_code": "sh510500", "is_domestic": True,
        "buy_fee": 0.0005, "dca_amount": 500.0, "dca_day": 10, "target_annual_rate": 0.09,
        "sell_rules": [(7, 0.015), (30, 0.005), (180, 0.001), (float('inf'), 0.0)]
    },
    "009051": {
        "name": "易方达中证红利ETF联接A", "track_code": "sh515180", "is_domestic": True,
        "buy_fee": 0.0006, "dca_amount": 250.0, "dca_day": 10, "target_annual_rate": 0.07,
        "sell_rules": [(7, 0.015), (30, 0.005), (180, 0.001), (float('inf'), 0.0)]
    },
    "000216": {
        "name": "华安黄金ETF联接A", "track_code": "sh518880", "is_domestic": True,
        "buy_fee": 0.0006, "dca_amount": 250.0, "dca_day": 10, "target_annual_rate": 0.05,
        "sell_rules": [(7, 0.015), (365, 0.001), (float('inf'), 0.0)]
    }
}

CSV_FILE_NAME = "基金交易明细_转换版(1).xlsx - 交易明细.csv"

def get_market_data(fund_code, track_code):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    official_nav, official_yesterday_nav, daily_growth = 1.0, 1.0, 0.0
    try:
        url_jj = f"http://qt.gtimg.cn/q=jj{fund_code}"
        res_jj = requests.get(url_jj, headers=headers, timeout=5)
        res_jj.encoding = 'gbk'
        if '~' in res_jj.text:
            parts = res_jj.text.split('"')[1].split('~')
            valid_navs = [float(p) for p in parts[2:] if p and 0.1 < float(p) < 100.0]
            if len(valid_navs) >= 1:
                official_nav = valid_navs[0]
                official_yesterday_nav = valid_navs[1] if len(valid_navs) >= 2 else official_nav
    except Exception as e: print(f"⚠️ 行情接口异常 ({fund_code}): {e}")

    try:
        url_stock = f"http://qt.gtimg.cn/q={track_code}"
        res_stock = requests.get(url_stock, headers=headers, timeout=5)
        res_stock.encoding = 'gbk'
        if '~' in res_stock.text:
            parts = res_stock.text.split('"')[1].split('~')
            if len(parts) >= 5 and float(parts[4]) > 0:
                daily_growth = ((float(parts[3]) - float(parts[4])) / float(parts[4])) * 100
    except Exception as e: print(f"⚠️ 场内同步异常 ({track_code}): {e}")
    return {"official_nav": official_nav, "official_yesterday_nav": official_yesterday_nav, "estimated_nav": official_nav * (1 + daily_growth / 100), "daily_growth": daily_growth}

def parse_historical_ledger():
    fifo_pools = {code: [] for code in FEE_RULES.keys()}
    transaction_logs = []
    csv_dates_by_fund = {code: set() for code in FEE_RULES.keys()}
    tz_utc8 = timezone(timedelta(hours=8))
    total_realized_pnl = 0.0
    
    if os.path.exists(CSV_FILE_NAME):
        raw_records = []
        with open(CSV_FILE_NAME, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader: raw_records.append(row)
        raw_records.reverse()

        for row in raw_records:
            code = row.get('基金代码', '').strip().zfill(6)
            if code not in FEE_RULES: continue
            tx_date_str = row.get('交易日期', '').strip().replace('/', '-')
            tx_type = row.get('交易类型', '').strip()
            csv_dates_by_fund[code].add(tx_date_str)
            
            try:
                dt_obj = datetime.strptime(tx_date_str, "%Y-%m-%d").replace(tzinfo=tz_utc8)
                conf_amt = float(row['确认金额']) if row['确认金额'] else 0.0
                conf_shares = float(row['确认份额']) if row['确认份额'] else 0.0
                fee = float(row['手续费']) if row['手续费'] else 0.0
            except (ValueError, KeyError): continue

            if conf_shares <= 0: continue

            if "买入" in tx_type or "定投" in tx_type:
                calced_nav = (conf_amt - fee) / conf_shares
                fifo_pools[code].append({"dt": dt_obj, "shares": conf_shares, "price": calced_nav, "amt": conf_amt, "type": tx_type, "org_shares": conf_shares})
                transaction_logs.append({"date": tx_date_str, "name": FEE_RULES[code]['name'], "type": "买入", "amount": conf_amt, "price": round(calced_nav, 4), "shares": conf_shares, "pnl": 0.0})
            elif "卖出" in tx_type or "赎回" in tx_type:
                calced_nav = (conf_amt + fee) / conf_shares
                shares_to_deduct = conf_shares
                matched_cost = 0.0
                while shares_to_deduct > 0 and fifo_pools[code]:
                    oldest = fifo_pools[code][0]
                    if oldest['shares'] <= shares_to_deduct:
                        matched_cost += oldest['shares'] * oldest['price']
                        shares_to_deduct -= oldest['shares']
                        fifo_pools[code].pop(0)
                    else:
                        matched_cost += shares_to_deduct * oldest['price']
                        oldest['amt'] *= (oldest['shares'] - shares_to_deduct) / oldest['shares']
                        oldest['shares'] -= shares_to_deduct
                        shares_to_deduct = 0
                realized_pnl = conf_amt - matched_cost
                total_realized_pnl += realized_pnl
                transaction_logs.append({"date": tx_date_str, "name": FEE_RULES[code]['name'], "type": "卖出", "amount": conf_amt, "price": round(calced_nav, 4), "shares": conf_shares, "pnl": round(realized_pnl, 2)})

    # 智能每月 10 号全自动定投扣款引擎
    today_dt = datetime.now(tz_utc8)
    today_str = today_dt.strftime("%Y-%m-%d")
    for code, rule in FEE_RULES.items():
        if today_dt.day == rule['dca_day'] and today_str not in csv_dates_by_fund[code]:
            m_data = get_market_data(code, rule['track_code'])
            current_nav = m_data['official_nav']
            dca_amt = rule['dca_amount']
            net_amt = dca_amt / (1 + rule['buy_fee'])
            sim_shares = net_amt / current_nav
            fifo_pools[code].append({"dt": today_dt, "shares": sim_shares, "price": current_nav, "amt": dca_amt, "type": "定投买入", "org_shares": sim_shares})
            transaction_logs.append({"date": today_str, "name": f"🤖自动定投·{rule['name']}", "type": "买入", "amount": dca_amt, "price": round(current_nav, 4), "shares": round(sim_shares, 2), "pnl": 0.0})

    transaction_logs.reverse()
    return fifo_pools, transaction_logs, total_realized_pnl

def calculate_target_value(lots, annual_rate, today_dt):
    total_target = 0.0
    r_m = (1 + annual_rate) ** (1/12) - 1
    r_d_dca = (1 + annual_rate) ** (1/365) - 1
    r_d_manual = (1 + 2 * r_m) ** (12/365) - 1
    for lot in lots:
        days = (today_dt - lot['dt']).days
        if days < 0: days = 0
        r_d = r_d_manual if "手动" in lot['type'] else r_d_dca
        total_target += lot['amt'] * ((1 + r_d) ** days)
    return total_target

def push_to_feishu(summary_est, position_list):
    webhook_url = os.environ.get("FEISHU_WEBHOOK")
    if not webhook_url: return
    tz_utc8 = timezone(timedelta(hours=8))
    time_str = datetime.now(tz_utc8).strftime("%m-%d %H:%M")
    is_profit = summary_est['daily_profit'] >= 0
    header_template = "green" if is_profit else "red"
    position_list.sort(key=lambda x: x['daily_growth_raw'], reverse=True)
    
    detail_md = ""
    for pos in position_list:
        val = pos['daily_growth_raw']
        if val > 1.5: g_icon = "🟢"
        elif 0.5 < val <= 1.5: g_icon = "🍏"
        elif 0.0 < val <= 0.5: g_icon = "🌱"
        elif -0.5 <= val <= 0.0: g_icon = "🍂"
        elif -1.5 <= val < -0.5: g_icon = "🍎"
        else: g_icon = "🔴"
        
        detail_md += f"{g_icon} **{pos['name']}** (`{pos['code']}`)\n ├ 盘中涨跌：`{pos['daily_growth']}` | **预计收益**：**￥{pos['estimated_daily_profit']:,.2f}**\n ├ 目标差额：`￥{pos['value_difference']:,.2f}` | 实际权重：`{pos['actual_weight']}%` (偏离 `{pos['weight_diff']:+.2f}%`)\n └ 当前实际价值：`￥{pos['estimated_value']:,.0f}`\n\n"

    sign_diff = "+" if summary_est['total_diff'] >= 0 else ""
    sign_dp = "+" if summary_est['daily_profit'] >= 0 else ""
    sign_rp = "+" if summary_est['realized_pnl'] >= 0 else ""

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
                        "content": (
                            f"⏱️ **同步时间**: `{time_str}` (北京/马来西亚时间)\n\n"
                            f"💳 **资产账户总览**:\n"
                            f"• 当前持仓本金: **￥{summary_est['total_position_cost']:,.2f}** (含定投与手动买入)\n"
                            f"• 今日总预计损益: **{sign_dp}￥{summary_est['daily_profit']:,.2f}** (已锁定真实持仓数据)\n"
                            f"• 累计已实现损益: **{sign_rp}￥{summary_est['realized_pnl']:,.2f}**\n"
                            f"• 目标与实际价值总差额: **{sign_diff}{summary_est['total_diff_pct']:.2f}%**\n"
                            f"• 总体配置阵型总偏离度: **{summary_est['total_weight_deviation']:.2f}%** (方案A)"
                        )
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"📋 **持仓精简估值看板 (按涨幅降序)**:\n{detail_md}"}
                }
            ]
        }
    }
    try: requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
    except Exception as e: print("飞书推送异常:", e)

def update_dashboard_data():
    tz_utc8 = timezone(timedelta(hours=8))
    today_dt = datetime.now(tz_utc8)
    fifo_pools, transaction_logs, total_realized_pnl = parse_historical_ledger()
    
    total_dca_pool_amt = sum(r['dca_amount'] for r in FEE_RULES.values())
    raw_position_data = {}
    total_actual_value = 0.0
    total_position_cost = 0.0
    
    for code, lots in fifo_pools.items():
        total_shares = sum(lot['shares'] for lot in lots)
        if total_shares <= 0: continue
        m_data = get_market_data(code, FEE_RULES[code]['track_code'])
        
        # 精准统计持仓本金：FIFO所剩份额的真实原始投入金额（按比例结转）
        current_fund_cost = sum(lot['shares'] * (lot['amt'] / lot['org_shares']) for lot in lots)
        total_position_cost += current_fund_cost
        weighted_avg_cost = sum(lot['shares'] * lot['price'] for lot in lots) / total_shares
        
        target_val = calculate_target_value(lots, FEE_RULES[code]['target_annual_rate'], today_dt)
        est_val = total_shares * m_data['estimated_nav']
        total_actual_value += est_val
        
        raw_position_data[code] = {
            "lots": lots, "m_data": m_data, "shares": total_shares, "cost_price": weighted_avg_cost,
            "target_val": target_val, "est_val": est_val
        }

    position_list = []
    est_daily_profit, total_diff, total_weight_deviation = 0.0, 0.0, 0.0
    
    for code, p_data in raw_position_data.items():
        m_data = p_data['m_data']
        est_day_prof = p_data['shares'] * m_data['official_nav'] * (m_data['daily_growth'] / 100)
        est_daily_profit += est_day_prof
        
        diff = p_data['target_val'] - p_data['est_val']
        total_diff += diff
        
        act_weight = (p_data['est_val'] / total_actual_value) * 100 if total_actual_value > 0 else 0.0
        exp_weight = (FEE_RULES[code]['dca_amount'] / total_dca_pool_amt) * 100
        weight_diff = act_weight - exp_weight
        total_weight_deviation += abs(weight_diff)
        
        position_list.append({
            "code": code, "name": FEE_RULES[code]['name'], "shares": round(p_data['shares'], 2), "cost_price": round(p_data['cost_price'], 4),
            "estimated_nav": round(m_data['estimated_nav'], 4), "daily_growth": f"{round(m_data['daily_growth'], 2)}%", "daily_growth_raw": m_data['daily_growth'],
            "estimated_value": round(p_data['est_val'], 2), "estimated_profit": round(p_data['est_val'] - (p_data['shares'] * p_data['cost_price']), 2),
            "estimated_daily_profit": round(est_day_prof, 2), "target_value": round(p_data['target_val'], 2),
            "value_difference": round(diff, 2), "actual_weight": round(act_weight, 2), "expected_weight": round(exp_weight, 2),
            "weight_diff": weight_diff
        })

    total_target_value = total_actual_value + total_diff
    total_diff_pct = (total_diff / total_target_value) * 100 if total_target_value > 0 else 0.0

    summary_est = {
        "total_value": round(total_actual_value, 2), 
        "total_position_cost": round(total_position_cost, 2),
        "daily_profit": round(est_daily_profit, 2), 
        "realized_pnl": round(total_realized_pnl, 2),
        "total_diff": round(total_diff, 2),
        "total_diff_pct": total_diff_pct,
        "total_weight_deviation": total_weight_deviation
    }
    
    dashboard_data = {
        "update_time": today_dt.strftime("%Y-%m-%d %H:%M:%S"), "summary_estimated": summary_est,
        "positions": position_list, "transaction_logs": transaction_logs
    }

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=4)
        
    push_to_feishu(summary_est, position_list)
    print("🎉 高级多维策略对齐版 14:30 动态清算圆满成功！")

if __name__ == "__main__":
    update_dashboard_data()
