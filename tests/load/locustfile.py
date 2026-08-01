"""DC-IOC 压测脚本 — Locust 负载测试

覆盖核心端点:
- /health (readiness probe)
- /api/dashboard/overview (驾驶舱概览)
- /api/hvac/overview (暖通概览)
- /api/power/overview (电力概览)
- /api/security/overview (安防概览)
- /api/ops/overview (运营概览)
- /api/equipment/list (设备列表)
- /api/alarms/list (告警列表)
- /api/auth/login (登录)

运行:
    # 本地开发
    locust -f tests/load/locustfile.py --host=http://localhost:8000

    # Docker
    docker run -p 8089:8089 -v $(pwd)/tests/load/locustfile.py:/mnt/locustfile.py \\
        locustio/locust -f /mnt/locustfile.py --host=http://host.docker.internal:8000

    # 无 Web UI 模式 (headless, CI 用)
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \\
        --users 100 --spawn-rate 10 --run-time 5m --headless --html=report.html
"""
import random

from locust import HttpUser, TaskSet, between, task


class ReadTasks(TaskSet):
    """只读用户行为集 (viewer 角色典型流量)"""

    def on_start(self):
        """用户登录, 获取 token。"""
        resp = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token", "")
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(10)
    def dashboard(self):
        """驾驶舱概览 — 最频繁"""
        self.client.get("/api/dashboard/overview", name="dashboard/overview")

    @task(5)
    def equipment_list(self):
        """设备列表"""
        self.client.get("/api/equipment/list", name="equipment/list")

    @task(5)
    def alarms_list(self):
        """告警列表"""
        self.client.get("/api/alarms/list", name="alarms/list")

    @task(4)
    def health(self):
        """健康检查"""
        self.client.get("/health", name="health")

    @task(3)
    def hvac_overview(self):
        """暖通概览"""
        self.client.get("/api/hvac/overview", name="hvac/overview")

    @task(3)
    def power_overview(self):
        """电力概览"""
        self.client.get("/api/power/overview", name="power/overview")

    @task(3)
    def security_overview(self):
        """安防概览"""
        self.client.get("/api/security/overview", name="security/overview")

    @task(3)
    def ops_overview(self):
        """运营概览"""
        self.client.get("/api/ops/overview", name="ops/overview")

    @task(2)
    def equipment_detail(self):
        """设备详情 — 随机设备"""
        equipment_ids = [
            "MOCK-CHILLER-01", "MOCK-CRAC-01", "MOCK-UPS-01",
            "MOCK-GENSET-01", "MOCK-TRANSFORMER-01",
        ]
        eid = random.choice(equipment_ids)
        self.client.get(f"/api/equipment/{eid}", name="equipment/detail")

    @task(2)
    def metrics(self):
        """Prometheus 指标"""
        self.client.get("/metrics", name="metrics")


class WriteTasks(TaskSet):
    """写入用户行为集 (operator 角色典型流量)"""

    def on_start(self):
        resp = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token", "")
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(5)
    def dashboard(self):
        self.client.get("/api/dashboard/overview", name="dashboard/overview")

    @task(4)
    def alarms_write(self):
        """外部采集测点写入 (模拟设备上报)"""
        points = [
            {
                "device_id": f"MOCK-CHILLER-{random.randint(1,30):02d}",
                "metric_name": random.choice(["supply_temp", "return_temp", "power_kw"]),
                "value": round(random.uniform(5.0, 15.0), 2),
                "unit": "degC",
                "quality": "good",
                "ts": "2026-01-01T00:00:00Z",
            }
            for _ in range(random.randint(1, 5))
        ]
        self.client.post(
            "/api/external/metrics/upload",
            json={"points": points},
            name="external/upload",
        )

    @task(2)
    def equipment_list(self):
        self.client.get("/api/equipment/list", name="equipment/list")


class ReadOnlyUser(HttpUser):
    """只读用户 (模拟 viewer)"""
    weight = 8
    tasks = [ReadTasks]
    wait_time = between(1, 3)


class WriteUser(HttpUser):
    """写入用户 (模拟 operator / 采集器)"""
    weight = 2
    tasks = [WriteTasks]
    wait_time = between(2, 5)
