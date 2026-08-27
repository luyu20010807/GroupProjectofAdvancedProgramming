from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.models import Order, OrderItem, Product, RefundRequest, User, utcnow  # noqa: E402
from app.security import hash_password  # noqa: E402


def add_order(db, user, merchant, product, status: str, suffix: str) -> Order:
    now = utcnow()
    order = Order(
        order_no=f"DEMO{now.strftime('%m%d%H%M')}{suffix}",
        user_id=user.id,
        merchant_id=merchant.id,
        status=status,
        total_cents=product.price_cents,
        receiver_name="张同学",
        receiver_phone="13800000000",
        receiver_address="某某大学学生公寓 1 号楼 101",
        remark="课程演示订单",
        paid_at=now - timedelta(days=3) if status != "pending_payment" else None,
        shipped_at=now - timedelta(days=2) if status in {"shipped", "completed"} else None,
        completed_at=now - timedelta(days=1) if status == "completed" else None,
        tracking_no="SF1234567890" if status in {"shipped", "completed"} else "",
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=1,
            unit_price_cents=product.price_cents,
            subtotal_cents=product.price_cents,
        )
    )
    return order


def seed(reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    try:
        if db.scalar(select(User.id).limit(1)):
            print("数据库已有数据，跳过初始化。使用 --reset 可重置。")
            return

        password = hash_password("123456")
        users = [
            User(username="user1", display_name="普通用户·张同学", password_hash=password, role="user"),
            User(username="user2", display_name="普通用户·李同学", password_hash=password, role="user"),
            User(username="merchant1", display_name="星云数码旗舰店", password_hash=password, role="merchant"),
            User(username="merchant2", display_name="拾光生活馆", password_hash=password, role="merchant"),
            User(username="admin", display_name="平台超级管理员", password_hash=password, role="super_admin"),
            User(username="service", display_name="平台客服小王", password_hash=password, role="customer_service"),
            User(username="business", display_name="平台业务管理员", password_hash=password, role="business_admin"),
            User(username="tech", display_name="平台技术管理员", password_hash=password, role="tech_admin"),
        ]
        db.add_all(users)
        db.flush()
        user1, _, merchant1, merchant2, *_ = users

        products = [
            Product(merchant_id=merchant1.id, name="Aurora X 智能手机", category="数码家电", description="6.7 英寸高刷屏、长续航和夜景影像，适合作为跨端商城的高价值商品演示。", price_cents=399900, stock=28, image_url="/static/icons/products/phone.svg"),
            Product(merchant_id=merchant1.id, name="CloudBuds 降噪耳机", category="数码家电", description="支持主动降噪与多设备切换，可用于测试购物车数量、库存和退款流程。", price_cents=69900, stock=80, image_url="/static/icons/products/headphone.svg"),
            Product(merchant_id=merchant1.id, name="机械键盘 Pro 87", category="电脑办公", description="热插拔轴体、三模连接与可编程按键，适合办公和游戏场景。", price_cents=45900, stock=45, image_url="/static/icons/products/keyboard.svg"),
            Product(merchant_id=merchant1.id, name="便携显示器 15.6", category="电脑办公", description="1080P 全贴合屏幕，支持 Type-C 一线直连。", price_cents=89900, stock=16, image_url="/static/icons/products/monitor.svg"),
            Product(merchant_id=merchant2.id, name="城市通勤双肩包", category="箱包服饰", description="分区收纳与防泼水面料，适合校园和通勤使用。", price_cents=23900, stock=62, image_url="/static/icons/products/bag.svg"),
            Product(merchant_id=merchant2.id, name="护眼阅读台灯", category="家居生活", description="无频闪调光与定时休息提醒，适合宿舍书桌。", price_cents=18900, stock=34, image_url="/static/icons/products/lamp.svg"),
            Product(merchant_id=merchant2.id, name="冷萃咖啡随行杯", category="家居生活", description="双层隔热杯体与可拆洗滤芯，支持冷萃和日常饮水。", price_cents=9900, stock=100, image_url="/static/icons/products/cup.svg"),
            Product(merchant_id=merchant2.id, name="年度计划手账套装", category="文具图书", description="包含月计划、项目页和复盘页，可演示低价商品下单。", price_cents=6900, stock=120, image_url="/static/icons/products/notebook.svg"),
        ]
        db.add_all(products)
        db.flush()

        order_paid = add_order(db, user1, merchant1, products[1], "paid", "01")
        order_shipped = add_order(db, user1, merchant2, products[4], "shipped", "02")
        order_completed = add_order(db, user1, merchant1, products[2], "completed", "03")
        order_rejected = add_order(db, user1, merchant2, products[5], "completed", "04")

        db.add(
            RefundRequest(
                refund_no="RDEMO-PENDING-01",
                order_id=order_completed.id,
                user_id=user1.id,
                merchant_id=merchant1.id,
                refund_type="return_refund",
                status="pending_merchant",
                reason="商品与描述不符",
                description="键盘右侧按键偶发失灵，希望退货退款。",
                amount_cents=order_completed.total_cents,
                user_evidence="keyboard_issue.jpg",
                merchant_deadline=utcnow() + timedelta(hours=20),
            )
        )
        db.add(
            RefundRequest(
                refund_no="RDEMO-REJECTED-01",
                order_id=order_rejected.id,
                user_id=user1.id,
                merchant_id=merchant2.id,
                refund_type="return_refund",
                status="merchant_rejected",
                reason="商品质量问题",
                description="台灯连续使用十分钟后闪烁。",
                amount_cents=order_rejected.total_cents,
                user_evidence="lamp_video.mp4",
                merchant_comment="暂未复现故障，先拒绝申请。",
                merchant_deadline=utcnow() - timedelta(hours=2),
            )
        )
        db.commit()
        print("演示数据初始化完成。")
        print("账号：user1 / merchant1 / admin / service / business / tech，密码均为 123456")
        print(f"示例订单：{order_paid.order_no}, {order_shipped.order_no}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="初始化课程项目演示数据")
    parser.add_argument("--reset", action="store_true", help="删除现有数据库并重新生成")
    args = parser.parse_args()
    seed(reset=args.reset)
