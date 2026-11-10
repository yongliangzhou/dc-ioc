import { defineComponent as m, computed as c, openBlock as n, createElementBlock as u, normalizeClass as b, createElementVNode as g, createTextVNode as f, toDisplayString as l, normalizeStyle as p, createCommentVNode as o } from "vue";
const C = {
  online: { cls: "dui-g", text: "在线" },
  running: { cls: "dui-g", text: "运行" },
  normal: { cls: "dui-g", text: "正常" },
  standby: { cls: "dui-a", text: "待机" },
  warning: { cls: "dui-a", text: "告警" },
  fault: { cls: "dui-r", text: "故障" },
  error: { cls: "dui-r", text: "异常" },
  offline: { cls: "dui-o", text: "离线" },
  stopped: { cls: "dui-o", text: "停机" },
  maintenance: { cls: "dui-b", text: "检修" },
  closing: { cls: "dui-b", text: "合闸" },
  opening: { cls: "dui-o", text: "分闸" }
}, y = "dui-o";
function h(t) {
  var s;
  const e = (t || "").toLowerCase();
  return ((s = C[e]) == null ? void 0 : s.cls) ?? y;
}
function L(t) {
  var s;
  const e = (t || "").toLowerCase();
  return ((s = C[e]) == null ? void 0 : s.text) || t || "-";
}
const w = /* @__PURE__ */ m({
  __name: "StatusBadge",
  props: {
    status: {},
    label: { default: "" }
  },
  setup(t) {
    const e = t, s = c(() => h(e.status)), r = c(() => e.label || L(e.status));
    return (v, i) => (n(), u("span", {
      class: b(["dui-status-badge", s.value])
    }, [
      i[0] || (i[0] = g("span", { class: "dui-status-dot" }, null, -1)),
      f(" " + l(r.value), 1)
    ], 2));
  }
}), x = (t, e) => {
  const s = t.__vccOpts || t;
  for (const [r, v] of e)
    s[r] = v;
  return s;
}, M = /* @__PURE__ */ x(w, [["__scopeId", "data-v-1babb185"]]), S = /* @__PURE__ */ m({
  __name: "AlarmBadge",
  props: {
    level: {},
    count: { default: 0 }
  },
  setup(t) {
    const e = t, s = {
      critical: { cls: "dui-critical", text: "紧急" },
      urgent: { cls: "dui-critical", text: "紧急" },
      major: { cls: "dui-major", text: "严重" },
      severe: { cls: "dui-major", text: "严重" },
      warning: { cls: "dui-warning", text: "警告" },
      info: { cls: "dui-info", text: "提示" }
    }, r = c(() => {
      var i, d;
      return ((d = s[(i = e.level) == null ? void 0 : i.toLowerCase()]) == null ? void 0 : d.cls) ?? "dui-info";
    }), v = c(() => {
      var d, a;
      const i = ((a = s[(d = e.level) == null ? void 0 : d.toLowerCase()]) == null ? void 0 : a.text) ?? e.level;
      return e.count > 0 ? `${i} ${e.count}` : i;
    });
    return (i, d) => (n(), u("span", {
      class: b(["dui-alarm-badge", r.value])
    }, l(v.value), 3));
  }
}), O = /* @__PURE__ */ x(S, [["__scopeId", "data-v-49f71c9c"]]), V = { class: "dui-kpi-ct" }, A = {
  key: 1,
  class: "dui-kpi-sub"
}, B = {
  key: 2,
  class: "dui-kpi-target"
}, $ = {
  key: 0,
  class: "dui-cv-prefix"
}, T = { key: 1 }, z = {
  key: 0,
  class: "dui-kpi-trend"
}, E = {
  key: 1,
  class: "dui-kpi-bar"
}, j = {
  key: 2,
  class: "dui-kpi-detail"
}, I = /* @__PURE__ */ m({
  __name: "KpiCard",
  props: {
    title: {},
    value: {},
    unit: {},
    prefix: {},
    subtitle: {},
    dot: {},
    trend: {},
    barValue: {},
    progress: {},
    progressColor: {},
    barColor: { default: "linear-gradient(90deg, var(--cyan), var(--blue))" },
    target: {},
    targetLabel: {},
    detail: {},
    size: { default: "md" },
    decimals: { default: 1 },
    status: {},
    clickable: { type: Boolean, default: !1 },
    valueClass: {}
  },
  emits: ["click"],
  setup(t) {
    const e = t, s = c(() => `dui-kpi-${e.size}`), r = c(() => e.barValue ?? e.progress), v = c(
      () => e.barColor ?? e.progressColor ?? "linear-gradient(90deg, var(--cyan), var(--blue))"
    ), i = c(() => {
      const a = e.value;
      return a == null || a === "" ? "-" : typeof a == "string" ? a : Number.isInteger(a) ? String(a) : a.toFixed(e.decimals);
    }), d = c(() => {
      const a = [];
      return e.status === "danger" && a.push("dui-cv-danger"), e.status === "warning" && a.push("dui-cv-warning"), e.valueClass && a.push(e.valueClass), a.join(" ");
    });
    return (a, k) => (n(), u("div", {
      class: b(["dui-kpi-card", [s.value, { "dui-kpi-clickable": t.clickable }]]),
      onClick: k[0] || (k[0] = (N) => t.clickable && a.$emit("click"))
    }, [
      g("div", V, [
        t.dot ? (n(), u("span", {
          key: 0,
          class: "dui-kpi-dot",
          style: p({ background: t.dot })
        }, null, 4)) : o("", !0),
        f(" " + l(t.title) + " ", 1),
        t.subtitle ? (n(), u("span", A, l(t.subtitle), 1)) : o("", !0),
        t.target !== void 0 && t.targetLabel ? (n(), u("span", B, l(t.targetLabel) + " " + l(t.target), 1)) : o("", !0)
      ]),
      g("div", {
        class: b(["dui-kpi-cv", d.value])
      }, [
        t.prefix ? (n(), u("span", $, l(t.prefix), 1)) : o("", !0),
        f(" " + l(i.value) + " ", 1),
        t.unit ? (n(), u("small", T, l(t.unit), 1)) : o("", !0)
      ], 2),
      t.trend !== void 0 ? (n(), u("div", z, [
        g("span", {
          class: b(t.trend >= 0 ? "dui-up" : "dui-down")
        }, l(t.trend >= 0 ? "▲" : "▼") + " " + l(Math.abs(t.trend).toFixed(1)) + "% ", 3)
      ])) : o("", !0),
      r.value !== void 0 ? (n(), u("div", E, [
        g("i", {
          style: p({ width: r.value + "%", background: v.value })
        }, null, 4)
      ])) : o("", !0),
      t.detail ? (n(), u("div", j, l(t.detail), 1)) : o("", !0)
    ], 2));
  }
}), U = /* @__PURE__ */ x(I, [["__scopeId", "data-v-30aca53b"]]);
export {
  O as AlarmBadge,
  y as DEFAULT_STATUS_CLASS,
  U as KpiCard,
  C as STATUS_MAP,
  M as StatusBadge,
  h as statusClassOf,
  L as statusLabelOf
};
