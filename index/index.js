// pages/home/index.js
Page({
  data: {
    inputValue: "",
    tips: null, // 展示识别结果
    recentRecords: []
  },

  onShow() {
    this.loadRecent();
  },

  loadRecent() {
    const allRecords = wx.getStorageSync('records') || [];
    this.setData({ recentRecords: allRecords.slice(0, 3) });
  },

  onInput(e) {
    this.setData({ inputValue: e.detail.value });
  },

  // === 核心：智能解析函数 (支持大类/小类) ===
  parseInput(text) {
    if (!text) return null;
    let workText = text.trim();

    // 1. 日期识别 (昨天、前天)
    let targetDate = new Date();
    let dateKeyword = "";
    if (workText.includes("昨天")) {
      targetDate.setDate(targetDate.getDate() - 1);
      dateKeyword = "昨天";
    } else if (workText.includes("前天")) {
      targetDate.setDate(targetDate.getDate() - 2);
      dateKeyword = "前天";
    }
    workText = workText.replace(dateKeyword, "");

    // 2. 提取金额
    const moneyMatch = workText.match(/(\d+(\.\d+)?)/);
    if (!moneyMatch) return null;
    const amountStr = moneyMatch[0];
    let money = parseFloat(amountStr);
    workText = workText.replace(amountStr, "");

    // 3. 定义大类与小类词库 (由你提供的映射关系转换)
    const library = {
      // 餐饮类
      '外卖': ['餐饮', '外卖'], '美团': ['餐饮', '外卖'], '饿了么': ['餐饮', '外卖'],
      '早饭': ['餐饮', '堂食'], '早餐': ['餐饮', '堂食'],
      '午饭': ['餐饮', '堂食'], '午餐': ['餐饮', '堂食'],
      '晚饭': ['餐饮', '堂食'], '晚餐': ['餐饮', '堂食'],
      '夜宵': ['餐饮', '堂食'], '烧烤': ['餐饮', '堂食'],
      '饭': ['餐饮', '堂食'], '面': ['餐饮', '堂食'], '粉': ['餐饮', '堂食'], 
      '吃': ['餐饮', '堂食'], '水': ['餐饮', '堂食'], '奶茶': ['餐饮', '堂食'],
      '零食': ['餐饮', '零食'],

      // 交通类
      '打车': ['交通', '打车'], '滴滴': ['交通', '打车'], '出租': ['交通', '打车'],
      '地铁': ['交通', '地铁'], '公交': ['交通', '公交'],
      '加油': ['交通', '加油'], '停车': ['交通', '停车'], '油': ['交通', '加油'],

      // 购物类
      '衣服': ['购物', '服饰'], '短袖': ['购物', '服饰'], '裤子': ['购物', '服饰'], '鞋': ['购物', '服饰'],
      '纸巾': ['购物', '日用'], '洗发水': ['购物', '日用'], '谷子': ['购物', '吃谷'], '猫': ['购物', '猫用品'],

      // 娱乐类
      '电影': ['娱乐', '电影'], '游戏': ['娱乐', '游戏'], '充值': ['娱乐', '游戏'], '会员': ['娱乐', '会员'],
      '充': ['娱乐', '游戏'], '账号': ['娱乐', '交易'],

      // 收入类 (特殊处理)
      '工资': ['收入', '工资'], '发钱': ['收入', '工资'], '红包': ['收入', '红包'], 
      '转账': ['收入', '转账'], '报销': ['收入', '报销'], '收入': ['收入', '其他']
    };

    // 4. 执行匹配逻辑
    let category = "其他";
    let subCategory = "其他";
    let type = "支出";
    let matchedWord = "";

    // 寻找匹配的关键词
    for (let word in library) {
      if (workText.includes(word)) {
        category = library[word][0];    // 大类
        subCategory = library[word][1]; // 小类
        matchedWord = word;
        break;
      }
    }

    // 5. 修正收支类型 (根据大类是否为“收入”)
    if (category === '收入') {
      type = '收入';
    }

    // 6. 备注清理
    let desc = workText
      .replace(matchedWord, "")
      .replace(/元|块|钱|了|花了|买个|点个|去/g, "")
      .trim();

    // 如果备注被删光了，用小类名称代替
    if (!desc) desc = subCategory === "其他" ? "日常记录" : subCategory;

    // 7. 返回结果
    return {
      id: Date.now(),
      date: this.formatDate(targetDate),
      rawDate: targetDate.getTime(),
      desc: desc,
      category: category,      // 大类：如“餐饮”
      subCategory: subCategory, // 小类：如“外卖”
      type: type,              // 类型：收入/支出
      money: type === '支出' ? -money : money,
      displayMoney: money
    };
  },

  formatDate(date) {
    const y = date.getFullYear();
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const d = date.getDate().toString().padStart(2, '0');
    return `${y}-${m}-${d}`;
  },

  // === 提交按钮点击 ===
  commit() {
    const result = this.parseInput(this.data.inputValue);
    
    if (!result) {
      wx.showToast({ title: '没看懂金额', icon: 'none' });
      return;
    }

    let records = wx.getStorageSync('records') || [];
    records.unshift(result);
    
    // 提交后按日期排序，确保昨天记的账排在今天后面
    records.sort((a, b) => b.rawDate - a.rawDate);

    wx.setStorageSync('records', records);

    this.setData({
      inputValue: "",
      tips: result,
      recentRecords: records.slice(0, 3)
    });

    wx.showToast({ title: '记账成功', icon: 'success' });
  }
});