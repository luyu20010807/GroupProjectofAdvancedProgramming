const { request } = require('../../utils/request')
Page({
  data: { products: [], loading: true },
  onShow() { this.load() },
  async load() {
    try { this.setData({ products: await request('/products'), loading: false }) }
    catch (e) { this.setData({ loading: false }) }
  },
  open(e) { wx.navigateTo({ url: `/pages/product-detail/product-detail?id=${e.currentTarget.dataset.id}` }) }
})
