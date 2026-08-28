const { request } = require('../../utils/request')
Page({
  data: { refund_type: 'return_refund', reason: '商品质量问题', description: '' },
  onLoad(options) { this.orderId = options.orderId },
  onType(e) { this.setData({ refund_type: e.detail.value }) },
  onReason(e) { this.setData({ reason: e.detail.value }) },
  onDescription(e) { this.setData({ description: e.detail.value }) },
  async submit() {
    await request(`/orders/${this.orderId}/refund`, 'POST', this.data)
    wx.showToast({ title: '申请已提交' })
    setTimeout(() => wx.navigateBack(), 600)
  }
})
