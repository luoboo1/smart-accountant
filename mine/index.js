// pages/mine/index.js
Page({

  data: {
    userInfo: null, 
    daysCount: 1,   
    currentYear: 2023, 
    
    // 功能菜单配置：只保留3个
    menuList: [
      { title: '数据备份', icon: '📂', type: 'backup' },
      { title: '导出账单', icon: '📊', type: 'export' },
      { title: '每日提醒', icon: '⏰', type: 'remind' }
    ]
  },

  onLoad() {
    this.setData({
      currentYear: new Date().getFullYear()
    })
    this.checkDays()

    // 尝试读取缓存的头像
    const cachedUser = wx.getStorageSync('userInfo')
    if (cachedUser) {
      this.setData({ userInfo: cachedUser })
    }
  },

  onShow() {
    this.checkDays()
  },

  // === 1. 计算天数逻辑 ===
  checkDays() {
    let start = wx.getStorageSync('start_date')
    const now = Date.now()

    if (!start) {
      wx.setStorageSync('start_date', now)
      this.setData({ daysCount: 1 })
    } else {
      const diff = now - start
      // Math.max 确保最少显示1天
      const days = Math.max(1, Math.floor(diff / (1000 * 60 * 60 * 24)) + 1)
      this.setData({ daysCount: days })
    }
  },

  // === 2. 模拟登录获取头像 ===
  handleLogin() {
    wx.getUserProfile({
      desc: '完善资料', 
      success: (res) => {
        this.setData({
          userInfo: res.userInfo
        })
        wx.setStorageSync('userInfo', res.userInfo)
        wx.showToast({ title: '已同步', icon: 'success' })
      },
      fail: () => {
        // 用户拒绝也不报错，不做处理
      }
    })
  },

  // === 3. 菜单点击处理 ===
  handleMenuTap(e) {
    const type = e.currentTarget.dataset.type
    
    switch (type) {
      case 'backup':
        // 模拟备份
        wx.showLoading({ title: '备份中...' })
        setTimeout(() => {
          wx.hideLoading()
          wx.showToast({ title: '数据安全', icon: 'success' })
        }, 1000)
        break;
        
      case 'export':
        // 模拟导出
        wx.showToast({ title: '账单已生成至剪贴板', icon: 'none' })
        break;
        
      case 'remind':
        // 模拟设置提醒
        wx.showModal({
          title: '提醒设置',
          content: '是否开启每日 20:00 记账提醒？',
          success: (res) => {
            if (res.confirm) {
              wx.showToast({ title: '设置成功' })
            }
          }
        })
        break;
    }
  },

  // === 4. 清除缓存 ===
  handleClearData() {
    wx.showModal({
      title: '操作确认',
      content: '确定要清除所有本地记录吗？(头像与天数将重置)',
      confirmColor: '#FF5252',
      success: (res) => {
        if (res.confirm) {
          wx.clearStorageSync() 
          this.setData({ 
            userInfo: null,
            daysCount: 1 
          })
          wx.showToast({ title: '已重置', icon: 'none' })
          
          // 重置开始时间
          wx.setStorageSync('start_date', Date.now())
        }
      }
    })
  }

})