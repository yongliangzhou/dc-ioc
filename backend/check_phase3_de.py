import asyncio, httpx, json

BASE = "http://localhost:8000"
AUTH = ("", "")  # 容器内需确认鉴权; 先试不带 token

async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        # 先尝试登录拿 token (沿用既有凭证)
        token = None
        for cred in [("admin", "admin123"), ("admin", "admin"), ("operator", "operator123")]:
            try:
                r = await c.post("/api/auth/login", json={"username": cred[0], "password": cred[1]})
                if r.status_code == 200:
                    token = r.json().get("access_token") or r.json().get("token")
                    print("login ok as", cred[0])
                    break
            except Exception as e:
                print("login err", e)
        h = {"Authorization": f"Bearer {token}"} if token else {}
        for path in ["/api/ops/equipment-health", "/api/equipment?limit=2000", "/api/cabinets?size=5&page=1"]:
            try:
                r = await c.get(path, headers=h)
                print("\n===", path, r.status_code)
                j = r.json()
                if isinstance(j, dict):
                    if "byDomain" in j:
                        print("avgHealth", j.get("avgHealth"), "count", j.get("count"), "summary", j.get("summary"))
                        print("byDomain:", [(d["label"], d["avgHealth"], d["grade"]) for d in j.get("byDomain", [])][:5])
                        print("worst[0]:", j.get("worst", [{}])[0].get("code"), j.get("worst", [{}])[0].get("health"), j.get("worst", [{}])[0].get("issues"))
                    else:
                        print("keys:", list(j.keys())[:10], "| n items:", len(j.get("items", j if isinstance(j, list) else [])))
                else:
                    print("list len", len(j))
            except Exception as e:
                print(path, "ERR", e)

asyncio.run(main())
