# 后端 API 端点清单（静态提取）

> `python gen_api.py` 静态 AST 扫描 `app/api/v1/endpoints/*.py`。

| 方法 | 路径 | 权限依赖 |
|------|------|-----------|
| GET    |  | - |
| GET    |  | - |
| GET    |  | - |
| GET    |  | - |
| GET    |  | - |
| GET    |  | - |
| GET    |  | - |
| GET    |  | - |
| GET    |  | - |
| GET    |  | - |
| GET    |  | - |
| POST   |  | - |
| POST   |  | require_role |
| POST   |  | - |
| POST   |  | require_role |
| POST   |  | - |
| POST   |  | - |
| GET    | /acs | - |
| GET    | /active | - |
| GET    | /active | - |
| POST   | /active/{alarm_id}/ack | - |
| POST   | /active/{alarm_id}/ack | - |
| POST   | /active/{alarm_id}/resolve | - |
| POST   | /active/{alarm_id}/resolve | - |
| GET    | /alarms | - |
| POST   | /ask | - |
| GET    | /bandwidth | - |
| GET    | /battery | - |
| GET    | /campus-comparison | - |
| GET    | /campuses | - |
| GET    | /capacity | - |
| GET    | /categories | - |
| GET    | /cctv | - |
| POST   | /change-password | - |
| GET    | /chiller-plant | - |
| GET    | /chiller-trends | - |
| GET    | /crac | - |
| GET    | /crac-trends | - |
| POST   | /device/register | - |
| GET    | /devices | - |
| GET    | /devices | - |
| DELETE | /devices/{device_id} | - |
| PUT    | /devices/{device_id} | - |
| GET    | /devices/{device_id}/metrics | - |
| GET    | /devices/{device_id}/metrics/history | - |
| GET    | /devices/{device_id}/metrics/realtime | - |
| GET    | /energy | - |
| GET    | /equipment-health | - |
| GET    | /findings | - |
| POST   | /findings | require_role |
| DELETE | /findings/{fid} | require_role |
| GET    | /findings/{fid} | - |
| PUT    | /findings/{fid} | require_role |
| GET    | /fire | - |
| POST   | /from-alarm/{alarm_id} | - |
| GET    | /fuel | - |
| GET    | /genset | - |
| GET    | /hv | - |
| GET    | /ids | - |
| POST   | /import | - |
| GET    | /liquid-cooling | - |
| POST   | /login | - |
| GET    | /lv | - |
| GET    | /maintain | - |
| GET    | /maintain/records | - |
| POST   | /maintain/records | require_role |
| DELETE | /maintain/records/{rid} | require_role |
| GET    | /maintain/records/{rid} | - |
| PUT    | /maintain/records/{rid} | require_role |
| GET    | /me | - |
| POST   | /metrics/upload | - |
| GET    | /overview | - |
| GET    | /overview | - |
| GET    | /overview | - |
| GET    | /ping | - |
| GET    | /records | - |
| POST   | /records | require_role |
| DELETE | /records/{rid} | require_role |
| GET    | /records/{rid} | - |
| PUT    | /records/{rid} | require_role |
| POST   | /refresh | - |
| GET    | /related | - |
| GET    | /roles | - |
| GET    | /routes | - |
| POST   | /routes | require_role |
| DELETE | /routes/{rid} | require_role |
| PUT    | /routes/{rid} | require_role |
| GET    | /sla | - |
| GET    | /state | - |
| GET    | /status | - |
| GET    | /thing-models | - |
| GET    | /topology/graph | - |
| GET    | /twin | - |
| GET    | /twin/ark | - |
| GET    | /twin/graph | - |
| GET    | /twin/scenarios | - |
| POST   | /twin/simulate | - |
| GET    | /twin/topology | - |
| GET    | /twin/topology/ark | - |
| GET    | /twin/topology/metrics | - |
| GET    | /twin/topology/scenarios | - |
| POST   | /twin/topology/simulate | - |
| GET    | /users | - |
| POST   | /users | - |
| PATCH  | /{alarm_id}/ack | - |
| PATCH  | /{alarm_id}/resolve | - |
| GET    | /{cabinet_id}/metrics | - |
| GET    | /{category} | - |
| GET    | /{equipment_id} | - |
| GET    | /{equipment_id}/metrics | - |
| DELETE | /{item_id} | - |
| DELETE | /{item_id} | - |
| GET    | /{item_id} | - |
| GET    | /{item_id} | - |
| PUT    | /{item_id} | - |
| PUT    | /{item_id} | - |
| DELETE | /{rid} | require_role |
| DELETE | /{rid} | require_role |
| GET    | /{rid} | - |
| GET    | /{rid} | - |
| PUT    | /{rid} | require_role |
| PUT    | /{rid} | require_role |
| DELETE | /{rule_id} | - |
| PUT    | /{rule_id} | - |
| PATCH  | /{rule_id}/silence | - |
| PATCH  | /{rule_id}/status | - |
| PATCH  | /{rule_id}/toggle | - |
| DELETE | /{ticket_id} | - |
| GET    | /{ticket_id} | - |
| PUT    | /{ticket_id} | - |
| PATCH  | /{ticket_id}/state | - |
