import sys
import time
sys.path.insert(0, "/app")
from app.services import manual_import as m
t0 = time.time()
p = m.build_payload("/app/_m.pdf")
print("ELAPSED", round(time.time() - t0, 2), "s")
print("CONTENT_LEN", len(p["content"]))
