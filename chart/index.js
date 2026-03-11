// pages/chart/index.js
Page({
  data: {
    currentMonth: '', // 当前选择月份 (例如 2023-10)
    totalExpense: '0.00',  // 总支出
    categoryList: [], // 用于渲染下方列表
    maxMoney: 1,      // 用于进度条基准
    pieStyle: '',     // 饼图 CSS 样式
    
    // 【关键修正】：将 colorMap 移入 data 内部，这样才能通过 this.data.colorMap 访问到
    colorMap: {
      '餐饮': '#FF6B6B',
      '交通': '#4ECDC4',
      '购物': '#FFD93D',
      '娱乐': '#6BCB77',
      '其他': '#A6A6A6',
      '医疗': '#FF9F43',
      '居住': '#5D9CEC'
    }
  },

  // 每次切到这个 Tab 时触发
  onShow() {
    // 1. 初始化月份（如果还没选过）
    if (!this.data.currentMonth) {
      const now = new Date();
      const y = now.getFullYear();
      const m = (now.getMonth() + 1).toString().padStart(2, '0');
      this.setData({ 
        currentMonth: `${y}-${m}` 
      }, () => {
        // 确保月份设置成功后再计算
        this.calculateData();
      });
    } else {
      // 如果已经有月份，直接执行计算以同步最新数据
      this.calculateData();
    }
  },

  // 月份选择器回调
  onMonthChange(e) {
    this.setData({ currentMonth: e.detail.value });
    this.calculateData();
  },

  // === 核心功能：跳转到记录页（首页） ===
  goToInput() {
    // 确保这里的 url 与你的 app.json 路径一致
    wx.switchTab({
      url: '/pages/home/index', 
      fail: (err) => {
        console.error('跳转失败，请检查 pages/home/index 是否在 tabBar 中', err);
      }
    });
  },

  // === 计算逻辑：从缓存读取并汇总 ===
  calculateData() {
    // 确保从 this.data 正确解构
    const { currentMonth, colorMap } = this.data;
    
    // 1. 从缓存获取数据
    const records = wx.getStorageSync('records') || [];

    // 2. 筛选：当月 + 支出
    const filtered = records.filter(item => {
      // 检查数据完整性
      return item.date && 
             item.date.startsWith(currentMonth) && 
             item.type === '支出';
    });

    // 如果没数据，恢复默认状态并返回
    if (filtered.length === 0) {
      this.setData({
        totalExpense: '0.00',
        categoryList: [],
        pieStyle: '',
        maxMoney: 1
      });
      return;
    }

    // 3. 按大类汇总
    let stats = {};
    let total = 0;

    filtered.forEach(item => {
      const money = Math.abs(parseFloat(item.money)) || 0;
      // 优先取 category(大类)，没有则归类为其他
      const cat = item.category || '其他'; 
      
      if (!stats[cat]) stats[cat] = 0;
      stats[cat] += money;
      total += money;
    });

    // 4. 转换为数组并排序
    let result = [];
    for (let cat in stats) {
      if (stats[cat] > 0) {
        result.push({
          name: cat,
          money: stats[cat].toFixed(2),
          value: stats[cat],
          // 这里的 colorMap[cat] 现在不会报错了，因为 colorMap 已在 data 中定义
          color: colorMap[cat] || colorMap['其他'] || '#999'
        });
      }
    }

    // 按金额从大到小排序
    result.sort((a, b) => b.value - a.value);

    // 5. 生成饼图 (Conic-Gradient) 和百分比
    if (result.length > 0) {
      let gradientStr = 'conic-gradient(';
      let currentPercent = 0;

      result = result.map(item => {
        const p = (item.value / total) * 100;
        item.percent = p.toFixed(1);

        let start = currentPercent;
        let end = currentPercent + p;
        gradientStr += `${item.color} ${start}% ${end}%, `;
        currentPercent = end;
        return item;
      });

      const finalPieStyle = `background: ${gradientStr.slice(0, -2) + ')'}`;

      // 6. 更新视图层
      this.setData({
        totalExpense: total.toFixed(2),
        categoryList: result,
        maxMoney: result[0].value, // 第一名作为进度条 100% 基准值
        pieStyle: finalPieStyle
      });
    }
  }
});