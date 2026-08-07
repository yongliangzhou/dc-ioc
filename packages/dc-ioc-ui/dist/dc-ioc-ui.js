import { defineComponent as m, computed as d, openBlock as n, createElementBlock as u, normalizeClass as b, createElementVNode as g, createTextVNode as f, toDisplayString as i, normalizeStyle as p, createCommentVNode as o } from "vue";
const C = /* @__PURE__ */ m({
  __name: "StatusBadge",
  props: {
    status: {},
    label: { default: "" }
  },
  setup(t) {
    const e = t, c = {
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
    }, r = d(() => {
      var s;
      const l = (e.status || "").toLowerCase();
      return "dui-" + (((s = c[l]) == null ? void 0 : s.cls) ?? "dui-o");
    }), v = d(() => {
      var s;
      const l = (e.status || "").toLowerCase();
      return e.label || ((s = c[l]) == null ? void 0 : s.text) || e.status || "-";
    });
    return (l, s) => (n(), u("span", {
      class: b(["dui-status-badge", r.value])
    }, [
      s[0] || (s[0] = g("span", { class: "dui-status-dot" }, null, -1)),
      f(" " + i(v.value), 1)
    ], 2));
  }
}), x = (t, e) => {
  const c = t.__vccOpts || t;
  for (const [r, v] of e)
    c[r] = v;
  return c;
}, I = /* @__PURE__ */ x(C, [["__scopeId", "data-v-9abcf0bf"]]), y = /* @__PURE__ */ m({
  __name: "AlarmBadge",
  props: {
    level: {},
    count: { default: 0 }
  },
  setup(t) {
    const e = t, c = {
      critical: { cls: "dui-critical", text: "紧急" },
      urgent: { cls: "dui-critical", text: "紧急" },
      major: { cls: "dui-major", text: "严重" },
      severe: { cls: "dui-major", text: "严重" },
      warning: { cls: "dui-warning", text: "警告" },
      info: { cls: "dui-info", text: "提示" }
    }, r = d(() => {
      var l, s;
      return ((s = c[(l = e.level) == null ? void 0 : l.toLowerCase()]) == null ? void 0 : s.cls) ?? "dui-info";
    }), v = d(() => {
      var s, a;
      const l = ((a = c[(s = e.level) == null ? void 0 : s.toLowerCase()]) == null ? void 0 : a.text) ?? e.level;
      return e.count > 0 ? `${l} ${e.count}` : l;
    });
    return (l, s) => (n(), u("span", {
      class: b(["dui-alarm-badge", r.value])
    }, i(v.value), 3));
  }
}), N = /* @__PURE__ */ x(y, [["__scopeId", "data-v-49f71c9c"]]), h = { class: "dui-kpi-ct" }, w = {
  key: 1,
  class: "dui-kpi-sub"
}, L = {
  key: 2,
  class: "dui-kpi-target"
}, V = {
  key: 0,
  class: "dui-cv-prefix"
}, B = { key: 1 }, S = {
  key: 0,
  class: "dui-kpi-trend"
}, $ = {
  key: 1,
  class: "dui-kpi-bar"
}, z = {
  key: 2,
  class: "dui-kpi-detail"
}, A = /* @__PURE__ */ m({
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
    barColor: { default: "linear-gradient(90deg, var(--cyan, #06b6d4), var(--blue, #3b82f6))" },
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
    const e = t, c = d(() => `dui-kpi-${e.size}`), r = d(() => e.barValue ?? e.progress), v = d(
      () => e.barColor ?? e.progressColor ?? "linear-gradient(90deg, var(--cyan, #06b6d4), var(--blue, #3b82f6))"
    ), l = d(() => {
      const a = e.value;
      return a == null || a === "" ? "-" : typeof a == "string" ? a : Number.isInteger(a) ? String(a) : a.toFixed(e.decimals);
    }), s = d(() => {
      const a = [];
      return e.status === "danger" && a.push("dui-cv-danger"), e.status === "warning" && a.push("dui-cv-warning"), e.valueClass && a.push(e.valueClass), a.join(" ");
    });
    return (a, k) => (n(), u("div", {
      class: b(["dui-kpi-card", [c.value, { "dui-kpi-clickable": t.clickable }]]),
      onClick: k[0] || (k[0] = (j) => t.clickable && a.$emit("click"))
    }, [
      g("div", h, [
        t.dot ? (n(), u("span", {
          key: 0,
          class: "dui-kpi-dot",
          style: p({ background: t.dot })
        }, null, 4)) : o("", !0),
        f(" " + i(t.title) + " ", 1),
        t.subtitle ? (n(), u("span", w, i(t.subtitle), 1)) : o("", !0),
        t.target !== void 0 && t.targetLabel ? (n(), u("span", L, i(t.targetLabel) + " " + i(t.target), 1)) : o("", !0)
      ]),
      g("div", {
        class: b(["dui-kpi-cv", s.value])
      }, [
        t.prefix ? (n(), u("span", V, i(t.prefix), 1)) : o("", !0),
        f(" " + i(l.value) + " ", 1),
        t.unit ? (n(), u("small", B, i(t.unit), 1)) : o("", !0)
      ], 2),
      t.trend !== void 0 ? (n(), u("div", S, [
        g("span", {
          class: b(t.trend >= 0 ? "dui-up" : "dui-down")
        }, i(t.trend >= 0 ? "▲" : "▼") + " " + i(Math.abs(t.trend).toFixed(1)) + "% ", 3)
      ])) : o("", !0),
      r.value !== void 0 ? (n(), u("div", $, [
        g("i", {
          style: p({ width: r.value + "%", background: v.value })
        }, null, 4)
      ])) : o("", !0),
      t.detail ? (n(), u("div", z, i(t.detail), 1)) : o("", !0)
    ], 2));
  }
}), M = /* @__PURE__ */ x(A, [["__scopeId", "data-v-0ad7d1d7"]]);
export {
  N as AlarmBadge,
  M as KpiCard,
  I as StatusBadge
};
