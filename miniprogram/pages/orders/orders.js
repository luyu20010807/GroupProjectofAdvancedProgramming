const { request } = require('../../utils/request')
Page({
  data: { orders: [] },
  onShow() { this.load() },
  async load() { this.setData({ orders: await request('/orders') }) },
  open(e) { wx.navigateTo({ url: `/pages/order-detail/order-detail?id=${e.currentTarget.dataset.id}` }) }
})
