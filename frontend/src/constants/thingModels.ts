/* 物模型 (Thing Model) — 设备注册模板
 *
 * 物模型定义一类设备的「结构画像」: 业务域 / 类别 / 采集协议 / 厂商 / 型号,
 * 以及它标准产出的测点模板 (metric 列表)。运维人员在「采集器接入」页选择物模型后,
 * 注册表单自动带入这些结构化字段, 无需逐台手工填写; 结合批量添加可一次派生 N 台同类设备。
 *
 * 物模型与后端解耦: 这里只是前端注册时的「模板/默认值」, 最终仍按
 * POST /api/external/device/register 契约逐台上报, 后端无感知。
 */

export interface ThingModelMetric {
  name: string; // 测点名 (蛇形命名, 与 mLab 中文标签对应)
  unit: string; // 单位
  desc: string; // 中文说明
}

export interface ThingModel {
  key: string;
  name: string; // 物模型展示名
  category: string; // 设备类别 chiller/crac/ups/...
  domain: string; // 业务域 hvac_source/hvac_terminal/power_lv/...
  protocol: string; // 采集协议 modbus/snmp/kafka/...
  vendor: string;
  model: string;
  tags: string[];
  metrics: ThingModelMetric[]; // 该物模型标准测点模板
}

export const THING_MODELS: ThingModel[] = [
  {
    key: "chiller",
    name: "冷水机组",
    category: "chiller",
    domain: "hvac_source",
    protocol: "modbus",
    vendor: "Carrier",
    model: "Carrier-19XR",
    tags: ["cooling", "hvac"],
    metrics: [
      { name: "supply_temp", unit: "℃", desc: "送水温度" },
      { name: "return_temp", unit: "℃", desc: "回水温度" },
      { name: "power_kw", unit: "kW", desc: "机组功耗" },
      { name: "cpu_usage", unit: "%", desc: "控制器 CPU 使用率" },
    ],
  },
  {
    key: "crac",
    name: "精密空调",
    category: "crac",
    domain: "hvac_terminal",
    protocol: "snmp",
    vendor: "Emerson",
    model: "Emerson-DX",
    tags: ["cooling", "hvac"],
    metrics: [
      { name: "supply_temp", unit: "℃", desc: "送风温度" },
      { name: "return_temp", unit: "℃", desc: "回风温度" },
      { name: "power_kw", unit: "kW", desc: "机组功耗" },
      { name: "cpu_usage", unit: "%", desc: "控制器 CPU 使用率" },
    ],
  },
  {
    key: "ups",
    name: "UPS 电源",
    category: "ups",
    domain: "power_lv",
    protocol: "snmp",
    vendor: "Vertiv",
    model: "Vertiv-Liebert",
    tags: ["power"],
    metrics: [
      { name: "power_kw", unit: "kW", desc: "负载功率" },
      { name: "cpu_usage", unit: "%", desc: "控制器 CPU 使用率" },
    ],
  },
];
