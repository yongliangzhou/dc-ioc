import type { EChartsOption } from "@/hooks/useECharts";
import { themeMode } from "@/theme";

/* 主题调色板 (暗/亮) */
export const PALETTE = ["#22e3ff", "#3b82f6", "#9b6bff", "#2bd47a", "#ffb020", "#ff5fa2", "#ff4d5e"];
const PALETTE_LIGHT = ["#0891b2", "#2563eb", "#7c3aed", "#16a34a", "#d97706", "#db2777", "#dc2626"];

interface ChartVars {
  palette: string[];
  axisLine: string;
  axisLabel: string;
  splitLine: string;
  legendTxt: string;
  tooltipBg: string;
  tooltipBorder: string;
  tooltipTxt: string;
  track: string;
  strong: string;
  pieBorder: string;
  accent: string;
}

const DARK: ChartVars = {
  palette: PALETTE,
  axisLine: "#1d2f4f", axisLabel: "#7e93b8", splitLine: "rgba(29,47,79,.6)",
  legendTxt: "#7e93b8",
  tooltipBg: "rgba(15,27,51,.95)", tooltipBorder: "#1d2f4f", tooltipTxt: "#cfe0ff",
  track: "#13233f", strong: "#fff", pieBorder: "#0a1220", accent: "#22e3ff",
};
const LIGHT: ChartVars = {
  palette: PALETTE_LIGHT,
  axisLine: "#d4deec", axisLabel: "#5a6c88", splitLine: "rgba(212,222,236,.8)",
  legendTxt: "#5a6c88",
  tooltipBg: "rgba(255,255,255,.97)", tooltipBorder: "#d4deec", tooltipTxt: "#1e2a3c",
  track: "#dbe4f0", strong: "#0b1524", pieBorder: "#ffffff", accent: "#0891b2",
};

/** 读取当前主题取色 (访问 themeMode.value => 在 computed 中调用可响应主题切换) */
export function chartVars(): ChartVars {
  return themeMode.value === "light" ? LIGHT : DARK;
}

function baseParts() {
  const v = chartVars();
  return {
    v,
    axis: {
      axisLine: { lineStyle: { color: v.axisLine } },
      axisLabel: { color: v.axisLabel, fontSize: 10 },
      splitLine: { lineStyle: { color: v.splitLine } },
      axisTick: { show: false },
    },
    legend: { textStyle: { color: v.legendTxt, fontSize: 11 }, itemWidth: 12, itemHeight: 8, top: 0 },
    tooltip: {
      trigger: "axis",
      backgroundColor: v.tooltipBg,
      borderColor: v.tooltipBorder,
      textStyle: { color: v.tooltipTxt, fontSize: 11 },
    },
    grid: { left: 8, right: 12, top: 32, bottom: 4, containLabel: true },
  };
}

/* 折线/面积图 */
export function lineOption(
  x: string[],
  series: { name: string; data: (number | null)[]; color?: string; dashed?: boolean; area?: boolean }[]
): EChartsOption {
  const { v, axis, legend, tooltip, grid } = baseParts();
  return ({
    backgroundColor: "transparent",
    color: v.palette, tooltip, legend, grid,
    xAxis: { type: "category", boundaryGap: false, data: x, ...axis },
    yAxis: { type: "value", ...axis },
    series: series.map((s, i) => ({
      name: s.name, type: "line", smooth: true, showSymbol: false,
      data: s.data,
      lineStyle: { width: 2, type: s.dashed ? "dashed" : "solid", color: s.color ?? v.palette[i] },
      itemStyle: { color: s.color ?? v.palette[i] },
      areaStyle: s.area ? { opacity: 0.18 } : undefined,
    })),
  } as EChartsOption);
}

/* 饼图/环图 */
export function pieOption(data: { name: string; value: number }[], radius: [string, string] = ["42%", "68%"]): EChartsOption {
  const { v, legend, tooltip } = baseParts();
  return ({
    backgroundColor: "transparent",
    color: v.palette,
    tooltip: { ...tooltip, trigger: "item" },
    legend: { ...legend, orient: "vertical", right: 6, top: "center" },
    series: [{
      type: "pie", radius, center: ["38%", "52%"],
      avoidLabelOverlap: true, label: { show: false },
      itemStyle: { borderColor: v.pieBorder, borderWidth: 2 },
      emphasis: { label: { show: true, color: v.strong, fontSize: 12, formatter: "{b}\n{d}%" } },
      data,
    }],
  } as EChartsOption);
}

/* 横向柱状图 */
export function barOption(y: string[], data: number[], unit = "%"): EChartsOption {
  const { v, axis, tooltip } = baseParts();
  return ({
    backgroundColor: "transparent",
    tooltip: { ...tooltip, trigger: "item", formatter: (p: any) => `${p.name}: ${p.value}${unit}` },
    grid: { left: 8, right: 30, top: 10, bottom: 4, containLabel: true },
    xAxis: { type: "value", max: 100, ...axis, splitLine: { show: false } },
    yAxis: { type: "category", data: y, ...axis },
    series: [{
      type: "bar", data, barWidth: 10,
      itemStyle: {
        borderRadius: [0, 5, 5, 0],
        color: (p: any) => (p.value > 85 ? "#ff4d5e" : p.value > 70 ? "#ffb020" : v.accent),
      },
      label: { show: true, position: "right", color: v.axisLabel, fontSize: 10, formatter: `{c}${unit}` },
    }],
  } as EChartsOption);
}

/* 单值环形图 (健康度, 中心显示百分比) */
export function ringOption(pct: number, color?: string): EChartsOption {
  const v = chartVars();
  const c = color ?? v.accent;
  return ({
    backgroundColor: "transparent",
    series: [{
      type: "pie", radius: ["70%", "88%"], center: ["50%", "50%"],
      avoidLabelOverlap: true, label: { show: false }, silent: true,
      data: [
        { value: pct, itemStyle: { color: c, shadowBlur: 8, shadowColor: c } },
        { value: 100 - pct, itemStyle: { color: v.track } },
      ],
    }],
    graphic: [{
      type: "text", left: "center", top: "middle",
      style: { text: `${pct}%`, fill: v.strong, fontSize: 16, fontWeight: 800 },
    }],
  } as EChartsOption);
}

/* 仪表盘 */
export function gaugeOption(name: string, value: number, max = 100, unit = "%", color?: string): EChartsOption {
  const v = chartVars();
  const c = color ?? v.accent;
  return ({
    backgroundColor: "transparent",
    series: [{
      type: "gauge", startAngle: 210, endAngle: -30, min: 0, max,
      radius: "100%", center: ["50%", "58%"],
      progress: { show: true, width: 8, itemStyle: { color: c } },
      axisLine: { lineStyle: { width: 8, color: [[1, v.track]] } },
      axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
      pointer: { show: false }, anchor: { show: false },
      title: { show: true, offsetCenter: [0, "32%"], color: v.axisLabel, fontSize: 11 },
      detail: { valueAnimation: true, offsetCenter: [0, "-2%"], color: v.strong, fontSize: 22, fontWeight: 800, formatter: `{value}${unit}` },
      data: [{ value, name }],
    }],
  } as EChartsOption);
}
