# 五人团队分工与文件归属

> 将“成员A/B/C/D”替换为真实姓名。组长是唯一维护 `main` 分支和发布版本的人，但每位成员都必须通过自己的账号提交代码并保留至少三个不同时间点、覆盖不同工作类型的提交记录。

## 1. 组长：架构、核心状态机、集成与发布

负责文件：

- `app/models.py`
- `app/database.py`
- `app/config.py`
- `app/services/order_service.py`
- `app/services/refund_service.py`
- `app/main.py`
- `run.py`、`Dockerfile`、`docker-compose.yml`
- 全组接口规范、数据库合并、Pull Request 审核、最终 Release

建议三次提交：

1. `feat(core): define order and refund domain models`
2. `feat(workflow): implement order and after-sales state machines`
3. `fix(integration): resolve cross-role transition and transaction issues`

组长答辩重点：为什么跨商家拆单；为什么业务规则放在 service 而不是页面；怎样防止非法状态跳转；怎样处理超时和并发库存。

## 2. 成员A：用户网页端与 PWA

负责文件：

- `app/routers/shop.py`
- `app/routers/orders.py`
- `app/templates/user/**`
- `app/templates/base.html`
- `app/templates/login.html`
- `app/templates/shared/notifications.html`
- `app/static/css/style.css`
- `app/static/js/app.js`
- `app/static/manifest.json`、`app/static/sw.js`

建议三次提交：

1. `feat(user): add product search cart and responsive pages`
2. `feat(order-ui): add order detail and after-sales interactions`
3. `fix(ux): prevent duplicate submission and improve mobile layout`

答辩重点：移动端响应式、购物车错误提示、按钮随订单状态变化、用户催办频率限制的界面反馈。

## 3. 成员B：商家后台与履约

负责文件：

- `app/routers/merchant.py`
- `app/templates/merchant/**`
- 商家商品、库存、发货和售后审核相关测试

建议三次提交：

1. `feat(merchant): implement product and inventory management`
2. `feat(fulfillment): implement merchant order shipping workflow`
3. `fix(refund): validate merchant ownership and review status`

答辩重点：为何商家只能看本店数据；支付前不能发货；发货必须填写物流；商家拒绝必须给理由；商家超时的后果。

## 4. 成员C：管理员后台、RBAC、审计和超时治理

负责文件：

- `app/dependencies.py`
- `app/routers/admin.py`
- `app/services/audit.py`
- `app/services/notification.py`
- `app/templates/admin/**`
- `scripts/run_timeout_jobs.py`

建议三次提交：

1. `feat(rbac): define customer service business and tech admin permissions`
2. `feat(admin): add dispute resolution and account governance`
3. `feat(governance): add timeout inspection notifications and audit trail`

答辩重点：客服、业务、技术管理员为什么不能共用全权限；审计日志记录哪些字段；自动超时任务如何减少用户等待。

## 5. 成员D：小程序 API、微信端、测试与质量报告

负责文件：

- `app/routers/api.py`
- `app/schemas.py`
- `app/security.py`
- `miniprogram/**`
- `tests/**`
- `load_test/**`
- `scripts/seed_demo.py`
- `docs/TEST_CASES.md`、测试结果截图

建议三次提交：

1. `feat(api): add token authentication and mini-program APIs`
2. `feat(miniprogram): implement shopping cart orders and refund pages`
3. `test(workflow): cover permissions timeouts and full refund flow`

答辩重点：网页 Session 与小程序 Token 的区别；为什么小程序不能直接连 SQLite；如何设计等价类、边界值、越权和超时测试。

## 6. 公共文件如何修改

以下文件不允许多人直接同时修改：

- `app/models.py`
- `requirements*.txt`
- `README.md`
- `app/templates/base.html`
- `rules.md`、`agents.md`

需要修改时：

1. 在 GitHub Issue 写清原因和字段影响；
2. 组长确认后由指定成员修改；
3. 其他成员先基于新版本调整自己的分支；
4. Pull Request 中必须说明数据库兼容性、接口变更和测试结果。
