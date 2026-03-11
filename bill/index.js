// pages/bill/index.js
Page({
  data: {
    allRecords: [],    // 完整数据源
    displayList: [],   // 当前展示的数据（带滑动状态 x）
    
    // --- 筛选状态 ---
    // 日期筛选：拆分为月份和日期
    currentMonth: '',  // 格式：YYYY-MM
    dayOptions: [],    // 日期下拉列表 ['全部', '01', '02'...]
    dayIndex: 0,       // 选中的日期索引

    // 类型筛选：大类与小类组合
    categoryOptions: [
      '全部类型', 
      '餐饮', '餐饮-外卖', '餐饮-堂食', '餐饮-零食',
      '交通', '交通-打车', '交通-地铁', '交通-公交', '交通-加油', '交通-停车',
      '购物', '购物-服饰', '购物-日用', '购物-吃谷', '购物-猫用品',
      '娱乐', '娱乐-电影', '娱乐-游戏', '娱乐-会员', '娱乐-交易',
      '收入', '收入-工资', '收入-红包', '收入-转账', '收入-报销', '收入-其他'
    ],
    categoryIndex: 0,

    // 统计
    totalIncome: '0.00',
    totalExpense: '0.00',
    balance: '0.00'
  },

  onShow() {
    // 1. 初始化日期
    const now = new Date();
    const y = now.getFullYear();
    const m = (now.getMonth() + 1).toString().padStart(2, '0');
    
    // 2. 初始化天数选择器（全部，01-31）
    const days = ['全部'];
    for(let i=1; i<=31; i++) days.push(i.toString().padStart(2, '0'));

    this.setData({ 
      currentMonth: `${y}-${m}`,
      dayOptions: days,
      dayIndex: 0 // 默认显示全月
    });

    this.refreshData();
  },

  // === 1. 数据刷新与过滤 ===
  refreshData() {
    const rawData = wx.getStorageSync('records') || [];
    const processedData = rawData.map(item => ({ ...item, x: 0 }));
    this.setData({ allRecords: processedData });
    this.filterData();
  },

  filterData() {
    const { allRecords, currentMonth, dayOptions, dayIndex, categoryIndex, categoryOptions } = this.data;
    
    // 构造比对日期
    const selectedDay = dayOptions[dayIndex]; // '全部' 或 '01', '02'...
    const fullDateTarget = selectedDay === '全部' ? currentMonth : `${currentMonth}-${selectedDay}`;

    // 处理分类匹配逻辑
    const selectedTypestr = categoryOptions[categoryIndex]; // 例如 '餐饮-外卖' 或 '餐饮'

    const filtered = allRecords.filter(item => {
      // A. 日期过滤：如果是全部，匹配前缀(YYYY-MM)；否则全匹配(YYYY-MM-DD)
      const isDateMatch = selectedDay === '全部' ? 
                          item.date.startsWith(currentMonth) : 
                          item.date === fullDateTarget;

      // B. 类型过滤
      let isCatMatch = false;
      if (selectedTypestr === '全部类型') {
        isCatMatch = true;
      } else if (selectedTypestr.includes('-')) {
        // 匹配小类：'餐饮-外卖' -> 大类餐饮 & 小类外卖
        const [mainCat, subCat] = selectedTypestr.split('-');
        isCatMatch = (item.category === mainCat && item.subCategory === subCat);
      } else {
        // 匹配大类：'餐饮' -> 只要大类是餐饮就行
        isCatMatch = (item.category === selectedTypestr);
      }

      return isDateMatch && isCatMatch;
    });

    // 计算统计
    let income = 0;
    let expense = 0;
    filtered.forEach(item => {
      if (item.type === '收入') income += Math.abs(item.money);
      else expense += Math.abs(item.money);
    });

    this.setData({
      displayList: filtered,
      totalIncome: income.toFixed(2),
      totalExpense: expense.toFixed(2),
      balance: (income - expense).toFixed(2)
    });
  },

  // === 2. 筛选事件 ===
  // 月份切换
  onMonthChange(e) {
    this.setData({ currentMonth: e.detail.value });
    this.filterData();
  },

  //具体日期刻度切换（全部/01-31）
  onDayChange(e) {
    this.setData({ dayIndex: e.detail.value });
    this.filterData();
  },

  // 类型切换（含大类小类）
  onCategoryChange(e) {
    this.setData({ categoryIndex: e.detail.value });
    this.filterData();
  },

  // === 3. 滑动交互逻辑 ===
  handleSlide(e) {
    if (e.currentTarget.dataset.index !== undefined) {
      this.tempSlideX = e.detail.x;
    }
  },

  handleTouchEnd(e) {
    const index = e.currentTarget.dataset.index;
    const x = this.tempSlideX || 0;
    const threshold = -35; 
    let finalX = x < threshold ? -70 : 0;
    
    let key = `displayList[${index}].x`;
    this.setData({ [key]: finalX });

    if(finalX === -70) {
      const list = this.data.displayList.map((item, i) => {
        if (i !== index) item.x = 0;
        return item;
      });
      this.setData({ displayList: list });
    }
  },

  // === 4. 删除逻辑 ===
  onDelete(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '提示',
      content: '确定删除这条记录吗？',
      success: (res) => {
        if (res.confirm) {
          let records = wx.getStorageSync('records') || [];
          records = records.filter(item => item.id !== id);
          wx.setStorageSync('records', records);
          this.refreshData();
          wx.showToast({ title: '已删除', icon: 'none' });
        } else {
          this.refreshData();
        }
      }
    });
  }
});