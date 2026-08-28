const app = getApp()

function request(path, method = 'GET', data = {}) {
  const token = wx.getStorageSync('token')
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${app.globalData.baseUrl}${path}`,
      method,
      data,
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) return resolve(res.data)
        if (res.statusCode === 401) wx.reLaunch({ url: '/pages/login/login' })
        wx.showToast({ title: res.data.detail || '请求失败', icon: 'none' })
        reject(res)
      },
      fail(err) {
        wx.showToast({ title: '无法连接后端', icon: 'none' })
        reject(err)
      }
    })
  })
}

module.exports = { request }
