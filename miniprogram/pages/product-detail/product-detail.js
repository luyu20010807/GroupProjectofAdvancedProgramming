const { request } = require('../../utils/request')
Page({
  data: { product: null, quantity: 1 },
  onLoad(options) { this.id = options.id; this.load() },
  async load() { this.setData({ product: await request(`/products/${this.id}`) }) },
  onQty(e) { this.setData({ quantity: Number(e.detail.value) || 1 }) },
  async add() {
    await request('/cart', 'POST', { product_id: Number(this.id), quantity: this.data.quantity })
    wx.showToast({ title: '已加入购物车' })
  }
})
