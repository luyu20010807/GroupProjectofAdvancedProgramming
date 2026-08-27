# 小程序 REST API 概要

基础地址：`/api/v1`。除登录和商品浏览外，请求头需携带：

```text
Authorization: Bearer <token>
```

| 方法 | 路径 | 作用 |
|---|---|---|
| POST | `/login` | 用户名密码换取 7 天 Token |
| GET | `/products` | 商品列表 |
| GET | `/products/{id}` | 商品详情 |
| GET | `/cart` | 当前用户购物车 |
| POST | `/cart` | 加入购物车 |
| DELETE | `/cart/{id}` | 删除条目 |
| POST | `/checkout` | 按商家拆单 |
| GET | `/orders` | 当前用户订单 |
| GET | `/orders/{id}` | 订单与售后详情 |
| POST | `/orders/{id}/pay` | 模拟支付 |
| POST | `/orders/{id}/confirm` | 确认收货 |
| POST | `/orders/{id}/refund` | 申请售后 |
| GET | `/me` | 当前 Token 用户 |

FastAPI 自动文档：应用启动后打开 `/docs`。
