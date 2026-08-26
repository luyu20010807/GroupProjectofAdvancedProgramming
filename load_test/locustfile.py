from locust import HttpUser, between, task


class ShopVisitor(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.client.post("/login", data={"username": "user1", "password": "123456"})

    @task(5)
    def browse_home(self):
        self.client.get("/")

    @task(3)
    def view_orders(self):
        self.client.get("/orders")

    @task(2)
    def view_cart(self):
        self.client.get("/cart")

    @task(1)
    def health_check(self):
        self.client.get("/health")
