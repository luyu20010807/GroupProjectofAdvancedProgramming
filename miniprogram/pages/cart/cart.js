const { request } = require('../../utils/request')
Page({
  data: { items: [], total: 0 },
  onShow() { this.load() },
  async load() {
    const items = await request('/cart')
    const total = items.reduce((sum, x) => sum + x.product.price * x.quantity, 0).toFixed(2)
    this.setData({ items, total })
  },
  async remove(e) { await request(`/cart/${e.currentTarget.dataset.id}`, 'DELETE'); this.load() },
  checkout() {
    wx.showModal({
      title: '确认提交订单', content: '使用预设演示收货信息，系统会按商家拆单。',
      success: async (res) => {
        if (!res.confirm) return
        await request('/checkout', 'POST', { receiver_name: '张同学', receiver_phone: '13800000000', receiver_address: '某某大学学生公寓 1 号楼 101', remark: '小程序订单' })
        wx.showToast({ title: '下单成功' }); wx.switchTab({ url: '/pages/orders/orders' })
      }
    })
  }
})
