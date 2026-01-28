import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import re

# ================= 1. 数据库配置 =================
DB_FILE = 'finance_pro.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY, 
                  date_str TEXT, 
                  time_str TEXT,
                  category_main TEXT, 
                  category_sub TEXT, 
                  description TEXT, 
                  amount REAL)''')
    conn.commit()
    conn.close()

def add_transaction(data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO transactions (date_str, time_str, category_main, category_sub, description, amount) VALUES (?, ?, ?, ?, ?, ?)",
              (data['date'], data['time'], data['category_main'], data['category_sub'], data['desc'], data['amount']))
    conn.commit()
    conn.close()

def get_data():
    conn = sqlite3.connect(DB_FILE)
    # 按时间倒序
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date_str DESC, time_str DESC", conn)
    conn.close()
    return df

# ================= 2. 核心逻辑：规则引擎 =================

def smart_parse(text):
    text_work = text.lower().strip()
    
    # --- A. 识别日期 ---
    target_date = datetime.now()
    if '昨天' in text_work:
        target_date = target_date - timedelta(days=1)
        text_work = text_work.replace('昨天', '') 
    elif '今天' in text_work:
        text_work = text_work.replace('今天', '')

    date_str = target_date.strftime("%Y-%m-%d")
    time_str = target_date.strftime("%H:%M:%S")

    # --- B. 提取金额 ---
    amounts = re.findall(r'\d+\.?\d*', text_work)
    if not amounts:
        return None
    
    money_val = float(amounts[0])
    text_work = text_work.replace(amounts[0], '')

    # --- C. 判断收支 ---
    income_keywords = ['工资', '收入', '转给我', '发钱', '红包', '退款', '报销']
    is_income = any(kw in text_work for kw in income_keywords)
    final_amount = money_val if is_income else -money_val

    # --- D. 关键词分类 ---
    keywords = {
        # 餐饮
        '外卖': ('餐饮', '外卖'), '美团': ('餐饮', '外卖'), '饿了么': ('餐饮', '外卖'),
        '早饭': ('餐饮', '堂食'), '早餐': ('餐饮', '堂食'),
        '午饭': ('餐饮', '堂食'), '午餐': ('餐饮', '堂食'),
        '晚饭': ('餐饮', '堂食'), '晚餐': ('餐饮', '堂食'),
        '夜宵': ('餐饮', '堂食'), '烧烤': ('餐饮', '堂食'),
        '饭': ('餐饮', '堂食'), '面': ('餐饮', '堂食'), '粉': ('餐饮', '堂食'), '吃': ('餐饮', '堂食'),
        '水': ('餐饮', '堂食'), '奶茶': ('餐饮', '堂食'),
        '零食': ('餐饮', '零食'),

        # 交通
        '打车': ('交通', '打车'), '滴滴': ('交通', '打车'), '出租': ('交通', '打车'),
        '地铁': ('交通', '地铁'), '公交': ('交通', '公交'), 
        '加油': ('交通', '加油'), '停车': ('交通', '停车'), '油': ('交通', '加油'),

        # 购物
        '衣服': ('购物', '服饰'), '短袖': ('购物', '服饰'), '裤子': ('购物', '服饰'), '鞋': ('购物', '服饰'),
        '纸巾': ('购物', '日用'), '洗发水': ('购物', '日用'), '谷子':('购物','吃谷'), '猫': ('购物', '猫用品'),

        # 娱乐
        '电影': ('娱乐', '电影'), '游戏': ('娱乐', '游戏'), '充值': ('娱乐', '游戏'), '会员': ('娱乐', '会员'),
        '充': ('娱乐', '游戏'), '账号': ('娱乐', '交易'),
    }

    sorted_keys = sorted(keywords.keys(), key=len, reverse=True)
    cat_main = "其他"
    cat_sub = "未分类"
    matched_keyword = ""

    for key in sorted_keys:
        if key in text_work:
            cat_main, cat_sub = keywords[key]
            matched_keyword = key
            break

    # --- E. 备注提取 ---
    clean_desc = text_work.replace(matched_keyword, '').strip()
    for garbage in ['了', '花了', '买', '个', '只', '元', '块', '，', '。', '点']:
        clean_desc = clean_desc.strip(garbage)
            
    if not clean_desc: clean_desc = text # 如果没备注，用原话

    return {
        "date": date_str, "time": time_str,
        "category_main": cat_main, "category_sub": cat_sub,
        "desc": clean_desc, "amount": final_amount, "raw": text
    }

# ================= 3. 界面逻辑 (已更新) =================
st.set_page_config(page_title="智能记账Pro", layout="wide", initial_sidebar_state="collapsed")
init_db()

# 在这里添加下载按钮，方便你备份数据
with open(DB_FILE, "rb") as f:
    st.sidebar.download_button("📥 备份数据库", f, file_name="finance_backup.db")

st.title("💰 智能记账助手")

# === 这里变成了 3 个标签页 ===
tab1, tab2, tab3 = st.tabs(["📝 记账对话", "🔍 明细查询", "📈 收支报表"])

# --- Tab 1: 记账对话 ---
with tab1:
    chat_container = st.container()
    user_input = st.chat_input("例：昨天外卖点了红烧肉饭25元...")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        result = smart_parse(user_input)
        
        if result:
            add_transaction(result)
            sign = "+" if result['amount'] > 0 else ""
            reply = f"✅ 已记：**{result['category_main']}-{result['category_sub']}** ({sign}{result['amount']}元)\n备注：{result['desc']}"
            st.session_state.messages.append({"role": "assistant", "content": reply})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "❌ 没看懂金额，请重试。"})

    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

# --- Tab 2: 明细查询 (新增功能) ---
with tab2:
    st.subheader("📋 账单明细筛选")
    df = get_data()
    
    if not df.empty:
        # 数据转换
        df['amount'] = pd.to_numeric(df['amount'])
        df['datetime_obj'] = pd.to_datetime(df['date_str'])

        # === 筛选区 ===
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            # 获取所有大类并去重
            all_cats = df['category_main'].unique().tolist()
            selected_cats = st.multiselect("📌 筛选分类", all_cats, default=all_cats)
            
        with col_filter2:
            # 日期选择器
            min_date = df['datetime_obj'].min().date()
            max_date = df['datetime_obj'].max().date()
            date_range = st.date_input("📅 选择日期范围", value=(min_date, max_date))

        # === 执行筛选 ===
        mask_cat = df['category_main'].isin(selected_cats)
        
        # 处理日期筛选逻辑 (防止报错)
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            mask_date = (df['datetime_obj'].dt.date >= start_date) & (df['datetime_obj'].dt.date <= end_date)
            current_df = df[mask_cat & mask_date]
        else:
            current_df = df[mask_cat] # 如果日期没选完，只按分类筛

        st.divider()
        st.caption(f"共找到 {len(current_df)} 条记录")

        # === 列表展示区 ===
        for index, row in current_df.iterrows():
            # 定义颜色：收入红色，支出绿色
            amount_color = "red" if row['amount'] > 0 else "green"
            amount_str = f"{row['amount']}"
            if row['amount'] > 0: amount_str = f"+{row['amount']}"

            # 使用 Expander 做成卡片样式
            with st.expander(f"**{row['date_str']}** | {row['category_main']} - {row['desc']}   Running: :{amount_color}[{amount_str}]"):
                st.markdown(f"""
                - 🕒 **时间**: {row['time_str']}
                - 📂 **分类**: {row['category_main']} > {row['category_sub']}
                - 💰 **金额**: {amount_str} 元
                - 📝 **原始输入**: "{row['description']}" # 数据库里存的是 description
                """)
    else:
        st.info("暂无数据")

# --- Tab 3: 收支报表 ---
with tab3:
    st.subheader("📊 财务概览")
    # (这里代码和之前一样复用 Tab2 的逻辑，稍微简化显示)
    df = get_data()
    if not df.empty:
        df['amount'] = pd.to_numeric(df['amount'])
        total_balance = df['amount'].sum()
        st.metric("总资产结余", f"¥{total_balance:.2f}")
        
        st.caption("支出分布")
        exp_df = df[df['amount'] < 0].copy()
        if not exp_df.empty:
            exp_df['abs_amt'] = exp_df['amount'].abs()
            st.bar_chart(exp_df.groupby('category_main')['abs_amt'].sum())
    else:
        st.info("暂无数据")
