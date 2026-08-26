const { request } = require('../../utils/request')
Page({
  data: { username: 'user1', password: '123456' },
  onUsername(e) { this.setData({ username: e.detail.value }) },
  onPassword(e) { this.setData({ password: e.detail.value }) },
  async login() {
    const data = await request('/login', 'POST', this.data)
    wx.setStorageSync('token', data.token)
    wx.switchTab({ url: '/pages/home/home' })
  }
})
