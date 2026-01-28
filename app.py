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
    # 增加 created_at 精确记录入库时间
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
    # 按从新到旧排序
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date_str DESC, time_str DESC", conn)
    conn.close()
    return df

# ================= 2. 核心逻辑：规则引擎 =================

def smart_parse(text):
    text_work = text.lower().strip() # 备份一个用于处理的文本
    
    # --- A. 识别日期 (支持简单的昨天/今天) ---
    target_date = datetime.now()
    if '昨天' in text_work:
        target_date = target_date - timedelta(days=1)
        text_work = text_work.replace('昨天', '') # 移除关键词防止干扰
    elif '今天' in text_work:
        text_work = text_work.replace('今天', '')

    date_str = target_date.strftime("%Y-%m-%d")
    time_str = target_date.strftime("%H:%M:%S")

    # --- B. 提取金额 ---
    # 匹配整数或小数
    amounts = re.findall(r'\d+\.?\d*', text_work)
    if not amounts:
        return None # 没数字，不处理
    
    money_val = float(amounts[0])
    
    # 从待处理文本中移除金额数字，方便后续提取备注
    text_work = text_work.replace(amounts[0], '')

    # --- C. 判断收支方向 ---
    income_keywords = ['工资', '收入', '转给我', '发钱', '红包', '退款', '报销']
    is_income = any(kw in text_work for kw in income_keywords)
    final_amount = money_val if is_income else -money_val

    # --- D. 关键词分类 (含优先级逻辑) ---
    # 字典定义：'关键词': ('大类', '小类')
    keywords = {
        # === 优先级高的长词放在前面，或者让系统自动排序 ===
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

    # === 关键步骤：按关键词长度降序排列 ===
    # 这样 "外卖" (2字) 会在 "饭" (1字) 之前被匹配
    sorted_keys = sorted(keywords.keys(), key=len, reverse=True)

    cat_main = "其他"
    cat_sub = "未分类"
    matched_keyword = ""

    for key in sorted_keys:
        if key in text_work:
            cat_main, cat_sub = keywords[key]
            matched_keyword = key # 记录匹配到的词，比如"外卖"
            break # 找到最高优先级的词，停止匹配

    # --- E. 智能生成备注 ---
    # 原始文本剔除掉：金额、日期词、匹配到的分类关键词
    # 剩下的就是备注。例如："外卖点了红烧肉饭20" -> 去掉"20" -> 去掉"外卖" -> 剩下的 "点了红烧肉饭"
    clean_desc = text_work.replace(matched_keyword, '').strip()
    
    # 去除一些无意义的连接词 (可选)
    for garbage in ['了', '花了', '买', '个', '只', '元', '块', '，', '。']:
        if clean_desc.startswith(garbage):
            clean_desc = clean_desc[len(garbage):]
        if clean_desc.endswith(garbage):
            clean_desc = clean_desc[:-len(garbage)]
            
    if not clean_desc:
        clean_desc = text # 如果删完了，就用原话

    return {
        "date": date_str,
        "time": time_str,
        "category_main": cat_main,
        "category_sub": cat_sub,
        "desc": clean_desc,
        "amount": final_amount,
        "raw": text
    }

# ================= 3. 界面逻辑 (Streamlit) =================
st.set_page_config(page_title="智能记账Pro", layout="wide", initial_sidebar_state="collapsed")
init_db()

# 侧边栏说明
with st.sidebar:
    st.markdown("### 💡 使用小贴士")
    st.markdown("- **优先匹配长词**：输入“吃外卖”，会优先匹配“外卖”而不是“吃”。")
    st.markdown("- **日期处理**：支持输入“昨天买菜20”，会自动记录为昨天的日期。")
    st.markdown("- **自动备注**：会自动提取除了关键词和金额之外的文字作为备注。")

st.title("💰 智能记账助手")

# 两个主要标签页
tab1, tab2 = st.tabs(["📝 记账对话", "📈 收支报表"])

with tab1:
    # 聊天记录容器
    chat_container = st.container()
    
    # 底部输入框
    user_input = st.chat_input("例如：昨天外卖点了红烧肉饭25元...")

    # 管理 Session State
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 处理用户输入
    if user_input:
        # 1. 记录用户的话
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # 2. 系统分析
        result = smart_parse(user_input)
        
        if result:
            # 入库
            add_transaction(result)
            
            # 生成回复
            amount_display = f"{result['amount']}元"
            if result['amount'] > 0: amount_display =f"+{result['amount']}元"
            
            reply = (f"✅ **已记录** | 📅 {result['date']}\n\n"
                     f"🏷️ **{result['category_main']} - {result['category_sub']}** : {amount_display}\n\n"
                     f"📝 备注：{result['desc']}")
            st.session_state.messages.append({"role": "assistant", "content": reply})
        else:
            fail_msg = "❌ 无法识别金额，请确保输入中包含数字（例如：20）。"
            st.session_state.messages.append({"role": "assistant", "content": fail_msg})

    # 渲染聊天记录
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

with tab2:
    st.subheader("📊 财务概览")
    df = get_data()
    
    if not df.empty:
        # 数据清洗与类型转换
        df['amount'] = pd.to_numeric(df['amount'])
        df['datetime'] = pd.to_datetime(df['date_str'] + ' ' + df['time_str'])
        
        # 1. 指标卡片
        total_in = df[df['amount'] > 0]['amount'].sum()
        total_out = df[df['amount'] < 0]['amount'].sum()
        balance = total_in + total_out
        
        c1, c2, c3 = st.columns(3)
        c1.metric("总收入", f"¥{total_in:,.2f}", delta_color="normal")
        c2.metric("总支出", f"¥{abs(total_out):,.2f}", delta_color="inverse")
        c3.metric("当前结余", f"¥{balance:,.2f}")
        
        st.divider()
        
        # 2. 图表分析
        col_charts1, col_charts2 = st.columns([1, 2])
        
        with col_charts1:
            st.caption("支出构成 (按大类)")
            exp_df = df[df['amount'] < 0].copy()
            if not exp_df.empty:
                exp_df['abs_amt'] = exp_df['amount'].abs()
                # 饼图数据
                pie_data = exp_df.groupby('category_main')['abs_amt'].sum()
                st.dataframe(pie_data, use_container_width=True) # 简单表格展示分类汇总
            else:
                st.info("暂无支出数据")
                
        with col_charts2:
            st.caption("近期账单明细")
            # 展示好看的表格
            st.dataframe(
                df[['date_str', 'category_main', 'category_sub', 'desc', 'amount']],
                column_config={
                    "date_str": "日期",
                    "category_main": "大类",
                    "category_sub": "小类",
                    "desc": "备注",
                    "amount": st.column_config.NumberColumn("金额", format="¥%.2f")
                },
                use_container_width=True,
                hide_index=True
            )
            
    else:
        st.info("还没有任何账单，快去对话框记一笔吧！")