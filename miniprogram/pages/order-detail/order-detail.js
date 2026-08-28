const { request } = require('../../utils/request')
Page({
  data: { order: null },
  onLoad(options) { this.id = options.id },
  onShow() { this.load() },
  async load() { this.setData({ order: await request(`/orders/${this.id}`) }) },
  async pay() { await request(`/orders/${this.id}/pay`, 'POST'); this.load() },
  async confirm() { await request(`/orders/${this.id}/confirm`, 'POST'); this.load() },
  refund() { wx.navigateTo({ url: `/pages/refund/refund?orderId=${this.id}` }) }
})
