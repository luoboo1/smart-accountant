// cloudfunctions/addBill/index.js
const cloud = require('wx-server-sdk')
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

exports.main = async (event, context) => {
  const { category, money, type, remark, dateStr, monthStr } = event
  const wxContext = cloud.getWXContext()

  try {
    return await db.collection('finance').add({
      data: {
        _openid: wxContext.OPENID,
        category: category || '一般消费', // 默认分类
        money: Number(money),            // 确保是数字
        type: type,                      // 1收入，0支出
        remark: remark || '',
        dateStr: dateStr,                // 格式 2023-10-24
        monthStr: monthStr,              // 格式 2023-10
        createTime: db.serverDate()      // 服务器时间
      }
    })
  } catch (e) {
    console.error(e)
    return { success: false, errMsg: e }
  }
}