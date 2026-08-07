<template>
  <div class="power-fuel">
    <!-- Header -->
    <div class="view-head">
      <h1>{{ tl('燃油监控系统') }}</h1>
      <span class="sub">{{
        tl('储油罐液位 · 日用油箱 · 供回油泵 · 消耗趋势 · 续航预测 · 补给管理')
      }}</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="grid cols-6">
      <SkeletonCard v-for="i in 6" :key="i" />
    </div>

    <!-- Error -->
    <Panel v-else-if="error" class="err-card">
      <div class="err-title">{{ tl('加载失败') }}</div>
      <div class="err-detail">{{ error }}</div>
      <button class="btn" @click="loadData()">{{ tl('重试') }}</button>
    </Panel>

    <template v-else-if="s">
      <!-- ======== KPI 总览 ======== -->
      <div class="grid cols-6">
        <KpiCard
          :title="tl('储油总量')"
          :value="totalVolume"
          unit="L"
          :decimals="0"
          dot="var(--cyan)"
          size="sm"
          :detail="tl('总容量') + ' ' + fmtInt(totalCapacity) + ' L'"
        />
        <KpiCard
          :title="tl('主油罐均位')"
          :value="avgMainLevel"
          unit="%"
          :decimals="1"
          size="sm"
          :bar-value="avgMainLevel"
          bar-color="var(--cyan)"
          :status="
            avgMainLevel < LOW_LEVEL ? 'danger' : avgMainLevel < WARN_LEVEL ? 'warning' : 'normal'
          "
        />
        <KpiCard
          :title="tl('日用箱均位')"
          :value="avgDayLevel"
          unit="%"
          :decimals="1"
          size="sm"
          :bar-value="avgDayLevel"
          bar-color="var(--violet)"
          :status="
            avgDayLevel < LOW_LEVEL ? 'danger' : avgDayLevel < WARN_LEVEL ? 'warning' : 'normal'
          "
        />
        <KpiCard
          :title="tl('运行油泵')"
          :value="pumpRunCount"
          :unit="'/' + (s.pumps?.length || 0)"
          :decimals="0"
          size="sm"
          :status="pumpFaultCount > 0 ? 'danger' : 'normal'"
        />
        <KpiCard
          :title="tl('管道压力')"
          :value="s.pipeline?.pressure ?? 0"
          unit="MPa"
          :decimals="2"
          size="sm"
          :status="(s.pipeline?.pressure ?? 0) > 0.5 ? 'warning' : 'normal'"
          :detail="s.pipeline?.state || '-'"
        />
        <KpiCard
          :title="tl('活跃告警')"
          :value="alarms.length"
          :unit="tl('项')"
          :decimals="0"
          size="sm"
          :status="criticalCount > 0 ? 'danger' : alarms.length > 0 ? 'warning' : 'normal'"
        />
      </div>

      <!-- ======== 3.4.1 油罐示意图 (SVG + 液位动画) ======== -->
      <Panel title="储油系统示意图">
        <template #extra>
          <div class="legend">
            <span class="lg"><i class="dot g"></i>{{ tl('正常液位') }}</span>
            <span class="lg"><i class="dot a"></i>{{ tl('低位预警') }}</span>
            <span class="lg"><i class="dot r"></i>{{ tl('低位报警/高位') }}</span>
            <span class="lg muted">{{ tl('点击油罐 / 油泵查看详情') }}</span>
          </div>
        </template>
        <div class="schematic-wrap">
          <svg
            :viewBox="`0 0 ${SVG_W} ${SVG_H}`"
            class="fuel-svg"
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <!-- 液面波浪渐变 -->
              <linearGradient id="oilG" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#22c55e" stop-opacity="0.95" />
                <stop offset="100%" stop-color="#15803d" stop-opacity="0.75" />
              </linearGradient>
              <linearGradient id="oilA" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#f59e0b" stop-opacity="0.95" />
                <stop offset="100%" stop-color="#b45309" stop-opacity="0.75" />
              </linearGradient>
              <linearGradient id="oilR" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#ef4444" stop-opacity="0.95" />
                <stop offset="100%" stop-color="#991b1b" stop-opacity="0.75" />
              </linearGradient>
              <clipPath v-for="(t, ti) in mainTanks" :key="'cp' + t.id" :id="'clip-main-' + ti">
                <rect :x="mainX(ti)" :y="TANK_Y" :width="TANK_W" :height="TANK_H" rx="10" />
              </clipPath>
              <clipPath v-for="(d, di) in dayTanks" :key="'cpd' + d.id" :id="'clip-day-' + di">
                <rect :x="dayX(di)" :y="DAY_Y" :width="DAY_W" :height="DAY_H" rx="6" />
              </clipPath>
            </defs>

            <!-- ── 主储油罐 ── -->
            <g
              v-for="(t, ti) in mainTanks"
              :key="'m' + t.id"
              class="tank-node"
              @click="selectTank(t, 'main')"
            >
              <!-- 罐体 -->
              <rect
                :x="mainX(ti)"
                :y="TANK_Y"
                :width="TANK_W"
                :height="TANK_H"
                rx="10"
                class="tank-shell"
              />
              <!-- 液体 (动画) -->
              <g :clip-path="`url(#clip-main-${ti})`">
                <rect
                  :x="mainX(ti)"
                  :y="oilTop(t.level, TANK_Y, TANK_H)"
                  :width="TANK_W"
                  :height="oilH(t.level, TANK_H)"
                  :fill="oilFill(t.level)"
                  class="oil-body"
                />
                <!-- 波浪 -->
                <path
                  :d="wavePath(mainX(ti), oilTop(t.level, TANK_Y, TANK_H), TANK_W)"
                  :fill="oilFill(t.level)"
                  class="oil-wave"
                  opacity="0.55"
                />
                <path
                  :d="wavePath(mainX(ti) - 20, oilTop(t.level, TANK_Y, TANK_H) + 3, TANK_W)"
                  :fill="oilFill(t.level)"
                  class="oil-wave slow"
                  opacity="0.35"
                />
              </g>
              <!-- 刻度线 -->
              <g v-for="mk in [10, 30, 70, 90]" :key="'mk' + mk">
                <line
                  :x1="mainX(ti)"
                  :y1="TANK_Y + TANK_H * (1 - mk / 100)"
                  :x2="mainX(ti) + TANK_W"
                  :y2="TANK_Y + TANK_H * (1 - mk / 100)"
                  class="tick-line"
                />
                <text
                  :x="mainX(ti) + TANK_W + 4"
                  :y="TANK_Y + TANK_H * (1 - mk / 100) + 3"
                  class="tick-text"
                >
                  {{ mk }}
                </text>
              </g>
              <!-- 数值 -->
              <text
                :x="mainX(ti) + TANK_W / 2"
                :y="TANK_Y + TANK_H / 2 + 2"
                class="tank-pct"
                :class="levelTextCls(t.level)"
              >
                {{ fmt(t.level, 1) }}%
              </text>
              <text :x="mainX(ti) + TANK_W / 2" :y="TANK_Y + TANK_H / 2 + 18" class="tank-vol">
                {{ fmtInt((t.cap * t.level) / 100) }} L
              </text>
              <text :x="mainX(ti) + TANK_W / 2" :y="TANK_Y - 10" class="tank-id">{{ t.id }}</text>
              <!-- 出油管 → 供油泵 -->
              <line
                :x1="mainX(ti) + TANK_W / 2"
                :y1="TANK_Y + TANK_H"
                :x2="mainX(ti) + TANK_W / 2"
                :y2="PIPE_Y"
                class="pipe"
              />
              <line
                :x1="mainX(ti) + TANK_W / 2"
                :y1="PIPE_Y"
                :x2="PUMP_X"
                :y2="PIPE_Y"
                class="pipe"
              />
            </g>

            <!-- ── 供油主管 + 泵 ── -->
            <rect
              :x="PUMP_X - 40"
              :y="PIPE_Y - 16"
              width="80"
              height="32"
              rx="6"
              class="pump-box"
              @click="selectPump()"
            />
            <text :x="PUMP_X" :y="PIPE_Y + 4" class="pump-text">{{ tl('供油泵组') }}</text>
            <line :x1="PUMP_X + 40" :y1="PIPE_Y" :x2="DAY_BUS_X" :y2="PIPE_Y" class="pipe active" />
            <line
              :x1="DAY_BUS_X"
              :y1="PIPE_Y"
              :x2="DAY_BUS_X"
              :y2="DAY_Y - 26"
              class="pipe active"
            />
            <text :x="PUMP_X + 100" :y="PIPE_Y - 8" class="pipe-label">
              {{ fmt(s.pipeline?.pressure ?? 0, 2) }} MPa
            </text>

            <!-- ── 日用油箱 ── -->
            <g
              v-for="(d, di) in dayTanks"
              :key="'d' + d.id"
              class="tank-node"
              @click="selectTank(d, 'day')"
            >
              <line
                :x1="DAY_BUS_X"
                :y1="DAY_Y - 26"
                :x2="dayX(di) + DAY_W / 2"
                :y2="DAY_Y - 26"
                class="pipe active"
              />
              <line
                :x1="dayX(di) + DAY_W / 2"
                :y1="DAY_Y - 26"
                :x2="dayX(di) + DAY_W / 2"
                :y2="DAY_Y"
                class="pipe active"
              />
              <rect
                :x="dayX(di)"
                :y="DAY_Y"
                :width="DAY_W"
                :height="DAY_H"
                rx="6"
                class="tank-shell"
              />
              <g :clip-path="`url(#clip-day-${di})`">
                <rect
                  :x="dayX(di)"
                  :y="oilTop(d.level, DAY_Y, DAY_H)"
                  :width="DAY_W"
                  :height="oilH(d.level, DAY_H)"
                  :fill="oilFill(d.level)"
                  class="oil-body"
                />
                <path
                  :d="wavePath(dayX(di), oilTop(d.level, DAY_Y, DAY_H), DAY_W)"
                  :fill="oilFill(d.level)"
                  class="oil-wave"
                  opacity="0.5"
                />
              </g>
              <text
                :x="dayX(di) + DAY_W / 2"
                :y="DAY_Y + DAY_H / 2 + 4"
                class="day-pct"
                :class="levelTextCls(d.level)"
              >
                {{ fmt(d.level, 0) }}%
              </text>
              <text :x="dayX(di) + DAY_W / 2" :y="DAY_Y - 6" class="day-id">{{ d.id }}</text>
              <!-- 至柴发机组 -->
              <line
                :x1="dayX(di) + DAY_W / 2"
                :y1="DAY_Y + DAY_H"
                :x2="dayX(di) + DAY_W / 2"
                :y2="DAY_Y + DAY_H + 20"
                class="pipe"
              />
              <text :x="dayX(di) + DAY_W / 2" :y="DAY_Y + DAY_H + 32" class="day-load">
                {{ tl('柴发') }}
              </text>
            </g>
          </svg>
        </div>

        <!-- 节点详情 -->
        <transition name="fade">
          <div v-if="selectedNode" class="node-detail">
            <div class="nd-head">
              <span class="nd-code" :class="selectedNode.cls">{{ selectedNode.code }}</span>
              <span class="nd-title">{{ selectedNode.label }}</span>
              <button class="nd-close" @click="selectedNode = null">×</button>
            </div>
            <div class="nd-grid">
              <div v-for="(kv, ki) in selectedNode.kvs" :key="ki" class="nd-kv">
                <span class="nd-k">{{ kv.k }}</span>
                <span class="nd-v" :class="kv.cls">{{ kv.v }}</span>
              </div>
            </div>
          </div>
        </transition>
      </Panel>

      <!-- ======== 3.4.2 燃油消耗趋势 (日/周/月) ======== -->
      <Panel title="燃油消耗趋势">
        <template #extra>
          <div class="range-tabs">
            <button
              v-for="r in RANGES"
              :key="r.key"
              class="rt-btn"
              :class="{ on: rangeKey === r.key }"
              @click="switchRange(r.key)"
            >
              {{ tl(r.label) }}
            </button>
          </div>
        </template>
        <div class="grid cols-3 sub-grid">
          <div class="stat-box">
            <span class="sb-k">{{ tl('区间总消耗') }}</span>
            <span class="sb-v mono">{{ fmtInt(rangeTotal) }} <small>L</small></span>
          </div>
          <div class="stat-box">
            <span class="sb-k">{{ tl('平均消耗') }}</span>
            <span class="sb-v mono"
              >{{ fmtInt(rangeAvg) }} <small>L/{{ tl(rangeUnitLabel) }}</small></span
            >
          </div>
          <div class="stat-box">
            <span class="sb-k">{{ tl('峰值消耗') }}</span>
            <span class="sb-v mono a-text">{{ fmtInt(rangePeak) }} <small>L</small></span>
          </div>
        </div>
        <TrendChart
          :title="''"
          :x-axis-data="consumeTrend.labels"
          :series="consumeTrend.series"
          :height="260"
        />
      </Panel>

      <!-- ======== 3.4.3 低油量预警 + 3.4.4 续航预测 ======== -->
      <div class="grid cols-2">
        <!-- 低油量预警面板 -->
        <Panel title="低油量预警">
          <template #extra>
            <AlarmBadge v-if="criticalCount" level="critical" :count="criticalCount" />
            <AlarmBadge v-else-if="warningCount" level="warning" :count="warningCount" />
            <span v-else class="pill g">{{ tl('全部正常') }}</span>
          </template>
          <div class="warn-list">
            <div v-for="w in levelWarnings" :key="w.id" class="warn-row" :class="w.level">
              <span class="w-dot" :class="w.level"></span>
              <span class="w-id">{{ w.id }}</span>
              <div class="w-bar">
                <i
                  :style="{
                    width: Math.min(100, w.level_pct) + '%',
                    background: barColorOf(w.level_pct),
                  }"
                ></i>
              </div>
              <span class="w-pct mono" :class="levelTextCls(w.level_pct)"
                >{{ fmt(w.level_pct, 1) }}%</span
              >
              <span class="w-msg">{{ w.message }}</span>
              <span class="w-th muted">{{ tl('阈值') }} {{ w.threshold }}%</span>
            </div>
            <div v-if="!levelWarnings.length" class="empty-tip muted">
              {{ tl('所有油罐 / 油箱液位正常') }}
            </div>
          </div>

          <div class="thr-bar">
            <span class="thr"><i class="dot r"></i>{{ tl('低位报警') }} &lt; {{ LOW_LEVEL }}%</span>
            <span class="thr"
              ><i class="dot a"></i>{{ tl('低位预警') }} &lt; {{ WARN_LEVEL }}%</span
            >
            <span class="thr"
              ><i class="dot g"></i>{{ tl('正常') }} {{ WARN_LEVEL }}~{{ HIGH_LEVEL }}%</span
            >
            <span class="thr"
              ><i class="dot r"></i>{{ tl('高位溢流') }} &gt; {{ HIGH_LEVEL }}%</span
            >
          </div>
        </Panel>

        <!-- 续航时间预测 -->
        <Panel title="续航时间预测">
          <template #extra>
            <span class="pill" :class="enduranceHours >= 12 ? 'g' : 'a'"
              >{{ tl('设计要求') }} ≥ 12h</span
            >
          </template>
          <div class="gauge-row">
            <div class="gauge-item">
              <ProgressGauge
                :value="Math.min(100, (enduranceHours / 24) * 100)"
                :max="100"
                size="lg"
                :label="tl('满载续航')"
                unit="h"
                :status="enduranceHours < 8 ? 'danger' : enduranceHours < 12 ? 'warning' : 'normal'"
              />
              <span class="gauge-num mono" :class="enduranceHours < 12 ? 'a-text' : 'g-text'"
                >{{ fmt(enduranceHours, 1) }} h</span
              >
              <span class="gauge-cap muted">{{ tl('满载') }} {{ fmtInt(FULL_LOAD_RATE) }} L/h</span>
            </div>
            <div class="gauge-item">
              <ProgressGauge
                :value="Math.min(100, (enduranceHalf / 48) * 100)"
                :max="100"
                size="lg"
                :label="tl('半载续航')"
                unit="h"
                :status="enduranceHalf < 24 ? 'warning' : 'normal'"
              />
              <span class="gauge-num mono g-text">{{ fmt(enduranceHalf, 1) }} h</span>
              <span class="gauge-cap muted"
                >{{ tl('半载') }} {{ fmtInt(FULL_LOAD_RATE / 2) }} L/h</span
              >
            </div>
            <div class="gauge-item">
              <ProgressGauge
                :value="dayTankPct"
                :max="100"
                size="lg"
                :label="tl('日用箱续航')"
                unit="%"
                :status="dayTankHours < 4 ? 'danger' : dayTankHours < 8 ? 'warning' : 'normal'"
              />
              <span class="gauge-num mono" :class="dayTankHours < 8 ? 'a-text' : 'g-text'"
                >{{ fmt(dayTankHours, 1) }} h</span
              >
              <span class="gauge-cap muted">{{ tl('日用油箱独立供油') }}</span>
            </div>
          </div>
          <div class="pred-list">
            <div class="pred-row">
              <span class="k">{{ tl('可用油量') }}</span
              ><span class="v mono">{{ fmtInt(totalVolume) }} L</span>
            </div>
            <div class="pred-row">
              <span class="k">{{ tl('预计耗尽时刻') }}</span
              ><span class="v mono">{{ exhaustTime }}</span>
            </div>
            <div class="pred-row">
              <span class="k">{{ tl('建议补油时刻') }}</span
              ><span class="v mono a-text">{{ refuelTime }}</span>
            </div>
            <div class="pred-row">
              <span class="k">{{ tl('应急供油合同') }}</span
              ><span class="v">{{ s.contract || '-' }}</span>
            </div>
            <div class="pred-row">
              <span class="k">{{ tl('管道伴热') }}</span
              ><span class="v">{{ s.pipeline?.tracing || '-' }}</span>
            </div>
          </div>
        </Panel>
      </div>

      <!-- ======== 油泵状态 + 阀门 / 保护 ======== -->
      <div class="grid cols-2">
        <Panel title="供油泵 / 回油泵">
          <template #extra>
            <span class="pill" :class="pumpFaultCount === 0 ? 'g' : 'a'"
              >{{ pumpRunCount }}/{{ s.pumps?.length || 0 }} {{ tl('运行') }}</span
            >
          </template>
          <div class="pump-grid">
            <div v-for="p in s.pumps ?? []" :key="p.id" class="pump-block">
              <div class="pump-head">
                <span class="d-status" :class="pumpDotCls(p.state)">●</span>
                <span class="d-name">{{ p.id }}</span>
                <span class="tag" :class="pumpTagCls(p.state)">{{ p.state }}</span>
                <span class="pump-mode muted">{{ p.mode }}</span>
              </div>
              <div class="sig-list" v-if="p.alarms?.length">
                <span class="sig" v-for="a in p.alarms" :key="a.name">
                  <span class="sig-k">{{ a.name }}</span>
                  <span class="sig-v" :class="sigCls(a.level)">{{ a.value }}</span>
                </span>
              </div>
              <div class="sig-list" v-if="p.protections?.length">
                <span class="sig" v-for="pr in p.protections" :key="pr.name">
                  <span class="sig-k">{{ pr.name }}</span>
                  <span class="sig-v" :class="sigCls(pr.level)">{{ pr.state }}</span>
                </span>
              </div>
            </div>
          </div>
        </Panel>

        <!-- 油罐参数表 -->
        <Panel class="scroll-x" title="油罐 / 油箱参数">
          <template #extra>
            <span class="pill g"
              >{{ mainTanks.length + dayTanks.length }} {{ tl('个监测点') }}</span
            >
          </template>
          <table class="mini-tbl">
            <thead>
              <tr>
                <th>{{ tl('编号') }}</th>
                <th>{{ tl('类型') }}</th>
                <th>{{ tl('容量') }}(L)</th>
                <th>{{ tl('液位') }}(%)</th>
                <th>{{ tl('存油') }}(L)</th>
                <th>{{ tl('油温') }}</th>
                <th>{{ tl('渗漏') }}</th>
                <th>{{ tl('阀门') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in tankRows" :key="row.id" class="tank-row" @click="selectRow(row.id)">
                <td class="d-name">{{ row.id }}</td>
                <td>
                  <span class="tag" :class="row.type === '主油罐' ? 'b' : 'g'">{{ row.type }}</span>
                </td>
                <td class="mono">{{ fmtInt(row.cap) }}</td>
                <td class="mono" :class="levelTextCls(row.level)">{{ fmt(row.level, 1) }}</td>
                <td class="mono">{{ fmtInt(row.volume) }}</td>
                <td class="mono">{{ row.temp == null ? '-' : fmt(row.temp, 1) + '°C' }}</td>
                <td>
                  <span class="tag" :class="row.leak === '正常' ? 'g' : 'r'">{{ row.leak }}</span>
                </td>
                <td>
                  <span class="tag" :class="row.valveOpen ? 'g' : 'b'">{{ row.valve }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </Panel>
      </div>

      <!-- ======== 3.4.5 补给记录表 ======== -->
      <Panel class="scroll-x" title="燃油补给记录">
        <template #extra>
          <div class="head-stats">
            <span class="hs"
              ><span class="k">{{ tl('近12次累计') }}</span
              ><span class="v mono">{{ fmtInt(refuelTotal) }} L</span></span
            >
            <span class="hs"
              ><span class="k">{{ tl('上次补给') }}</span
              ><span class="v mono">{{ refuelRecords[0]?.date || '-' }}</span></span
            >
            <span class="hs"
              ><span class="k">{{ tl('平均单次') }}</span
              ><span class="v mono">{{ fmtInt(refuelAvg) }} L</span></span
            >
          </div>
        </template>
        <table>
          <thead>
            <tr>
              <th>{{ tl('单号') }}</th>
              <th>{{ tl('日期') }}</th>
              <th>{{ tl('目标罐') }}</th>
              <th>{{ tl('补给量') }}(L)</th>
              <th>{{ tl('补给前') }}(%)</th>
              <th>{{ tl('补给后') }}(%)</th>
              <th>{{ tl('供应商') }}</th>
              <th>{{ tl('油品') }}</th>
              <th>{{ tl('化验') }}</th>
              <th>{{ tl('操作人') }}</th>
              <th>{{ tl('状态') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in refuelRecords" :key="r.no">
              <td class="mono">{{ r.no }}</td>
              <td class="mono">{{ r.date }}</td>
              <td class="d-name">{{ r.tank }}</td>
              <td class="mono g-text">+{{ fmtInt(r.amount) }}</td>
              <td class="mono">{{ r.before }}</td>
              <td class="mono">{{ r.after }}</td>
              <td class="muted">{{ r.vendor }}</td>
              <td class="muted">{{ r.grade }}</td>
              <td>
                <span class="tag" :class="r.qc === '合格' ? 'g' : 'a'">{{ r.qc }}</span>
              </td>
              <td class="muted">{{ r.operator }}</td>
              <td>
                <StatusBadge
                  :status="r.status === '已完成' ? 'normal' : 'warning'"
                  :text="r.status"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <!-- ======== 实时告警 ======== -->
      <Panel title="实时告警">
        <template #extra>
          <div class="badges">
            <AlarmBadge level="critical" :count="criticalCount" />
            <AlarmBadge level="warning" :count="warningCount" />
            <AlarmBadge level="info" :count="infoCount" />
          </div>
        </template>
        <div class="alarm-list">
          <div v-for="(a, ai) in alarms" :key="ai" class="alarm-row" :class="a.level">
            <span class="a-ts mono">{{ a.time }}</span>
            <span class="a-src">{{ a.source }}</span>
            <span class="a-msg">{{ a.message }}</span>
            <span class="a-val mono">{{ a.value }}</span>
            <span class="tag" :class="levelTagCls(a.level)">{{ levelText(a.level) }}</span>
          </div>
          <div v-if="!alarms.length" class="empty-tip muted">{{ tl('当前无燃油系统告警') }}</div>
        </div>
      </Panel>

      <!-- ======== 知识库 ======== -->
      <KnowledgePanels :knowledge="s.knowledge" />
    </template>
  </div>
</template>

<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, computed, reactive, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { fmt, fmtInt } from '@/utils/format'
import { SkeletonCard, TrendChart, ProgressGauge,  } from '@/components/monitor'
import { KpiCard, StatusBadge, AlarmBadge } from '@dc-ioc/ui'
import {
  getPowerFuelDetailed,
  type FuelSummary,
  type FuelMainTankView,
  type FuelDayTankView,
} from '@/api/power'
import Panel from '@/components/common/Panel.vue'
import KnowledgePanels from '@/components/KnowledgePanels.vue'

const { t: tl } = useI18n()

// ──────────────────────────────────────────
// 常量 / 布局
// ──────────────────────────────────────────
const LOW_LEVEL = 20 // 低位报警
const WARN_LEVEL = 30 // 低位预警
const HIGH_LEVEL = 90 // 高位溢流
const FULL_LOAD_RATE = 660 // 满载耗油 L/h (3×1000kW 机组约 660 L/h)

const SVG_W = 1000
const SVG_H = 380
const TANK_Y = 40
const TANK_H = 150
const TANK_W = 110
const PIPE_Y = 232
const PUMP_X = 500
const DAY_BUS_X = 640
const DAY_Y = 292
const DAY_H = 56
const DAY_W = 72

const RANGES = [
  { key: 'day', label: '日 (24h)' },
  { key: 'week', label: '周 (7d)' },
  { key: 'month', label: '月 (30d)' },
] as const
type RangeKey = (typeof RANGES)[number]['key']

// ──────────────────────────────────────────
// State
// ──────────────────────────────────────────
const loading = ref(true)
const error = ref('')
const s = ref<FuelSummary | null>(null)
const rangeKey = ref<RangeKey>('day')
let timer: number | undefined

interface DetailNode {
  code: string
  label: string
  cls: string
  kvs: { k: string; v: string; cls?: string }[]
}
const selectedNode = ref<DetailNode | null>(null)

const mainTanks = computed<FuelMainTankView[]>(() => s.value?.mainTanks ?? [])
const dayTanks = computed<FuelDayTankView[]>(() => s.value?.dayTanks ?? [])

// ──────────────────────────────────────────
// KPI 派生
// ──────────────────────────────────────────
const totalCapacity = computed(() =>
  [...mainTanks.value, ...dayTanks.value].reduce((sum, t) => sum + (t.cap || 0), 0),
)
const totalVolume = computed(() =>
  Number(
    [...mainTanks.value, ...dayTanks.value]
      .reduce((sum, t) => sum + ((t.cap || 0) * (t.level || 0)) / 100, 0)
      .toFixed(0),
  ),
)
const avgMainLevel = computed(() => avgOf(mainTanks.value.map((t) => t.level)))
const avgDayLevel = computed(() => avgOf(dayTanks.value.map((t) => t.level)))
const pumpRunCount = computed(() => (s.value?.pumps ?? []).filter((p) => p.state === '运行').length)
const pumpFaultCount = computed(
  () => (s.value?.pumps ?? []).filter((p) => p.state === '故障').length,
)

// ──────────────────────────────────────────
// 3.4.1 SVG 液位
// ──────────────────────────────────────────
function mainX(i: number): number {
  const n = mainTanks.value.length || 1
  const gap = 40
  const totalW = n * TANK_W + (n - 1) * gap
  const startX = Math.max(60, (SVG_W - totalW) / 2 - 120)
  return Math.round(startX + i * (TANK_W + gap))
}
function dayX(i: number): number {
  const n = dayTanks.value.length || 1
  const gap = 30
  const totalW = n * DAY_W + (n - 1) * gap
  const startX = DAY_BUS_X - totalW / 2
  return Math.round(startX + i * (DAY_W + gap))
}
function oilH(level: number, h: number): number {
  return Math.max(0, Math.min(h, (h * (level || 0)) / 100))
}
function oilTop(level: number, y: number, h: number): number {
  return y + h - oilH(level, h)
}
function oilFill(level: number): string {
  if (level < LOW_LEVEL || level > HIGH_LEVEL) return 'url(#oilR)'
  if (level < WARN_LEVEL) return 'url(#oilA)'
  return 'url(#oilG)'
}
/** 生成一段横跨罐宽的正弦波路径（配合 CSS translate 动画产生流动感） */
function wavePath(x: number, top: number, w: number): string {
  const amp = 3
  const seg = w / 2
  let d = `M ${x - w} ${top}`
  for (let i = 0; i < 4; i++) {
    d += ` q ${seg / 4} ${-amp} ${seg / 2} 0 q ${seg / 4} ${amp} ${seg / 2} 0`
  }
  d += ` L ${x + w * 2} ${top + 60} L ${x - w} ${top + 60} Z`
  return d
}

function selectTank(t: FuelMainTankView | FuelDayTankView, kind: 'main' | 'day') {
  const isMain = kind === 'main'
  const mt = t as FuelMainTankView
  const dt = t as FuelDayTankView
  const kvs: { k: string; v: string; cls?: string }[] = [
    { k: tl('类型'), v: isMain ? tl('室外储油罐') : tl('日用油箱') },
    { k: tl('液位'), v: fmt(t.level, 1) + '%', cls: levelTextCls(t.level) },
    { k: tl('容量'), v: fmtInt(t.cap) + ' L' },
    { k: tl('当前存油'), v: fmtInt((t.cap * t.level) / 100) + ' L' },
    { k: tl('渗漏检测'), v: t.leak, cls: t.leak === '正常' ? 'g-text' : 'r-text' },
  ]
  if (isMain) {
    kvs.push({ k: tl('油温'), v: fmt(mt.t, 1) + '°C' })
    kvs.push({ k: tl('水分'), v: mt.water })
    ;(mt.valves ?? []).forEach((v) => kvs.push({ k: v.name, v: v.state, cls: sigCls(v.level) }))
  } else if (dt.valve) {
    kvs.push({ k: dt.valve.name, v: dt.valve.state, cls: sigCls(dt.valve.level) })
  }
  ;(t.switches ?? []).forEach((sw) => kvs.push({ k: sw.th, v: sw.state, cls: sigCls(sw.level) }))
  ;(t.protections ?? []).forEach((p) => kvs.push({ k: p.name, v: p.state, cls: sigCls(p.level) }))
  selectedNode.value = {
    code: t.id,
    label: isMain ? tl('室外储油罐') : tl('日用油箱'),
    cls: levelNodeCls(t.level),
    kvs,
  }
}
function selectPump() {
  const list = s.value?.pumps ?? []
  const kvs: { k: string; v: string; cls?: string }[] = [
    { k: tl('油泵总数'), v: String(list.length) + ' ' + tl('台') },
    { k: tl('运行'), v: String(pumpRunCount.value) + ' ' + tl('台'), cls: 'g-text' },
    {
      k: tl('故障'),
      v: String(pumpFaultCount.value) + ' ' + tl('台'),
      cls: pumpFaultCount.value ? 'r-text' : 'g-text',
    },
    { k: tl('管道压力'), v: fmt(s.value?.pipeline?.pressure ?? 0, 2) + ' MPa' },
    { k: tl('管道状态'), v: s.value?.pipeline?.state || '-' },
    { k: tl('伴热'), v: s.value?.pipeline?.tracing || '-' },
  ]
  list.forEach((p) =>
    kvs.push({
      k: p.id,
      v: `${p.state} / ${p.mode}`,
      cls: p.state === '运行' ? 'g-text' : p.state === '故障' ? 'r-text' : '',
    }),
  )
  selectedNode.value = {
    code: 'PUMP',
    label: tl('供油泵组'),
    cls: pumpFaultCount.value ? 'r' : 'g',
    kvs,
  }
}
function selectRow(id: string) {
  const m = mainTanks.value.find((t) => t.id === id)
  if (m) return selectTank(m, 'main')
  const d = dayTanks.value.find((t) => t.id === id)
  if (d) selectTank(d, 'day')
}

// ──────────────────────────────────────────
// 3.4.2 消耗趋势
// ──────────────────────────────────────────
const consumeTrend = reactive<{
  labels: string[]
  series: {
    name: string
    type: 'line' | 'bar'
    data: number[]
    color: string
    areaStyle?: Record<string, unknown>
    smooth?: boolean
  }[]
}>({
  labels: [],
  series: [],
})

function switchRange(k: RangeKey) {
  rangeKey.value = k
  rebuildTrend()
}

function rebuildTrend() {
  const k = rangeKey.value
  const now = new Date()
  const labels: string[] = []
  const consume: number[] = []
  const stock: number[] = []
  let cur = totalVolume.value || 30000

  if (k === 'day') {
    for (let i = 23; i >= 0; i--) {
      const t = new Date(now.getTime() - i * 3600_000)
      labels.push(String(t.getHours()).padStart(2, '0') + ':00')
      const hourFactor = 0.35 + 0.5 * Math.max(0, Math.sin(((t.getHours() - 6) / 24) * Math.PI * 2))
      consume.push(Number((FULL_LOAD_RATE * 0.12 * hourFactor + rnd(6)).toFixed(0)))
    }
  } else if (k === 'week') {
    for (let i = 6; i >= 0; i--) {
      const t = new Date(now.getTime() - i * 86400_000)
      labels.push(`${t.getMonth() + 1}/${t.getDate()}`)
      consume.push(Number((FULL_LOAD_RATE * 0.12 * 24 * (0.8 + Math.random() * 0.5)).toFixed(0)))
    }
  } else {
    for (let i = 29; i >= 0; i--) {
      const t = new Date(now.getTime() - i * 86400_000)
      labels.push(`${t.getMonth() + 1}/${t.getDate()}`)
      consume.push(Number((FULL_LOAD_RATE * 0.12 * 24 * (0.7 + Math.random() * 0.7)).toFixed(0)))
    }
  }

  // 反推库存曲线（自后向前累加消耗）
  for (let i = consume.length - 1; i >= 0; i--) {
    stock[i] = Number(cur.toFixed(0))
    cur += consume[i]
    // 模拟补给：月视图中每 10 天有一次补给拉升
    if (k === 'month' && i % 10 === 0) cur -= 8000
    cur = Math.max(2000, cur)
  }

  consumeTrend.labels = labels
  consumeTrend.series = [
    { name: tl('燃油消耗'), type: 'bar' as const, data: consume, color: '#f59e0b' },
    { name: tl('库存油量'), type: 'line' as const, data: stock, color: '#22d3ee', smooth: true },
  ]
}

const rangeTotal = computed(() => (consumeTrend.series[0]?.data ?? []).reduce((a, b) => a + b, 0))
const rangeAvg = computed(() => {
  const d = consumeTrend.series[0]?.data ?? []
  return d.length ? Number((rangeTotal.value / d.length).toFixed(0)) : 0
})
const rangePeak = computed(() => Math.max(0, ...(consumeTrend.series[0]?.data ?? [0])))
const rangeUnitLabel = computed(() => (rangeKey.value === 'day' ? '时' : '日'))

// ──────────────────────────────────────────
// 3.4.3 低油量预警
// ──────────────────────────────────────────
interface LevelWarning {
  id: string
  level: 'critical' | 'warning'
  level_pct: number
  threshold: number
  message: string
}
const levelWarnings = computed<LevelWarning[]>(() => {
  const out: LevelWarning[] = []
  const push = (id: string, lv: number, isMain: boolean) => {
    if (lv < LOW_LEVEL) {
      out.push({
        id,
        level: 'critical',
        level_pct: lv,
        threshold: LOW_LEVEL,
        message: tl('液位低位报警，需立即补油'),
      })
    } else if (lv < WARN_LEVEL) {
      out.push({
        id,
        level: 'warning',
        level_pct: lv,
        threshold: WARN_LEVEL,
        message: tl('液位低位预警，建议安排补给'),
      })
    } else if (lv > HIGH_LEVEL) {
      out.push({
        id,
        level: 'critical',
        level_pct: lv,
        threshold: HIGH_LEVEL,
        message: tl('液位高位，存在溢流风险'),
      })
    }
    void isMain
  }
  mainTanks.value.forEach((t) => push(t.id, t.level, true))
  dayTanks.value.forEach((t) => push(t.id, t.level, false))
  return out
})

// ──────────────────────────────────────────
// 3.4.4 续航预测
// ──────────────────────────────────────────
const enduranceHours = computed(() => {
  const api = s.value?.endurance
  if (api && Number.isFinite(api) && api > 0) return Number(api)
  return Number((totalVolume.value / FULL_LOAD_RATE).toFixed(1))
})
const enduranceHalf = computed(() => Number((enduranceHours.value * 2).toFixed(1)))
const dayTankVolume = computed(() =>
  dayTanks.value.reduce((sum, t) => sum + ((t.cap || 0) * (t.level || 0)) / 100, 0),
)
const dayTankHours = computed(() => Number((dayTankVolume.value / FULL_LOAD_RATE).toFixed(1)))
const dayTankPct = computed(() =>
  Math.min(100, Number(((dayTankHours.value / 12) * 100).toFixed(1))),
)
const exhaustTime = computed(() => addHours(enduranceHours.value))
const refuelTime = computed(() => addHours(Math.max(0, enduranceHours.value - 6)))

function addHours(h: number): string {
  const d = new Date(Date.now() + h * 3600_000)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ──────────────────────────────────────────
// 油罐参数表
// ──────────────────────────────────────────
interface TankRow {
  id: string
  type: string
  cap: number
  level: number
  volume: number
  temp: number | null
  leak: string
  valve: string
  valveOpen: boolean
}
const tankRows = computed<TankRow[]>(() => {
  const rows: TankRow[] = []
  mainTanks.value.forEach((t) => {
    const v = (t.valves ?? [])[0]
    rows.push({
      id: t.id,
      type: '主油罐',
      cap: t.cap,
      level: t.level,
      volume: (t.cap * t.level) / 100,
      temp: t.t,
      leak: t.leak,
      valve: v?.state ?? '-',
      valveOpen: (v?.state ?? '').includes('开'),
    })
  })
  dayTanks.value.forEach((t) => {
    rows.push({
      id: t.id,
      type: '日用油箱',
      cap: t.cap,
      level: t.level,
      volume: (t.cap * t.level) / 100,
      temp: null,
      leak: t.leak,
      valve: t.valve?.state ?? '-',
      valveOpen: (t.valve?.state ?? '').includes('开'),
    })
  })
  return rows
})

// ──────────────────────────────────────────
// 3.4.5 补给记录 (确定性生成)
// ──────────────────────────────────────────
interface RefuelRecord {
  no: string
  date: string
  tank: string
  amount: number
  before: number
  after: number
  vendor: string
  grade: string
  qc: string
  operator: string
  status: string
}
const VENDORS = ['中石化 · 华南分公司', '中石油 · 区域配送', '应急保障供应商 A']
const OPERATORS = ['张启明', '李文涛', '王建国', '陈立平']
const refuelRecords = computed<RefuelRecord[]>(() => {
  const tanks = mainTanks.value.length ? mainTanks.value.map((t) => t.id) : ['T-01', 'T-02']
  const out: RefuelRecord[] = []
  const now = new Date()
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getTime() - (i * 13 + 3) * 86400_000)
    const before = 22 + ((i * 7) % 16)
    const after = Math.min(95, before + 55 + ((i * 5) % 12))
    const cap = mainTanks.value[i % Math.max(1, mainTanks.value.length)]?.cap ?? 30000
    out.push({
      no: `RF${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}-${String(i + 1).padStart(2, '0')}`,
      date: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
      tank: tanks[i % tanks.length],
      amount: Math.round((cap * (after - before)) / 100),
      before,
      after,
      vendor: VENDORS[i % VENDORS.length],
      grade: i % 4 === 0 ? '0# 柴油 (国VI)' : '-10# 柴油 (国VI)',
      qc: i === 5 ? '待复检' : '合格',
      operator: OPERATORS[i % OPERATORS.length],
      status: i === 0 ? '已完成' : '已完成',
    })
  }
  return out
})
const refuelTotal = computed(() => refuelRecords.value.reduce((a, r) => a + r.amount, 0))
const refuelAvg = computed(() =>
  refuelRecords.value.length
    ? Number((refuelTotal.value / refuelRecords.value.length).toFixed(0))
    : 0,
)

// ──────────────────────────────────────────
// 告警派生
// ──────────────────────────────────────────
interface AlarmItem {
  level: 'critical' | 'warning' | 'info'
  time: string
  source: string
  message: string
  value: string
}
const alarms = computed<AlarmItem[]>(() => {
  const out: AlarmItem[] = []
  const now = new Date()
  const ts = (m: number) => new Date(now.getTime() - m * 60000).toTimeString().slice(0, 8)
  let idx = 1

  levelWarnings.value.forEach((w) => {
    out.push({
      level: w.level,
      time: ts(idx++),
      source: w.id,
      message: w.message,
      value: fmt(w.level_pct, 1) + '%',
    })
  })
  ;[...mainTanks.value, ...dayTanks.value].forEach((t) => {
    if (t.leak && t.leak !== '正常') {
      out.push({
        level: 'critical',
        time: ts(idx++),
        source: t.id,
        message: tl('油罐渗漏检测异常'),
        value: t.leak,
      })
    }
    ;(t.protections ?? []).forEach((p) => {
      if (p.state !== '正常')
        out.push({
          level: sigLevel(p.level),
          time: ts(idx++),
          source: `${t.id}·${p.name}`,
          message: tl('保护装置动作'),
          value: p.state,
        })
    })
  })
  mainTanks.value.forEach((t) => {
    if (t.t != null && t.t > 40)
      out.push({
        level: 'warning',
        time: ts(idx++),
        source: t.id,
        message: tl('油温偏高'),
        value: fmt(t.t, 1) + '°C',
      })
    if (t.water && t.water !== '正常' && t.water !== '合格')
      out.push({
        level: 'warning',
        time: ts(idx++),
        source: t.id,
        message: tl('油品含水量异常'),
        value: t.water,
      })
  })
  ;(s.value?.pumps ?? []).forEach((p) => {
    if (p.state === '故障')
      out.push({
        level: 'critical',
        time: ts(idx++),
        source: p.id,
        message: tl('油泵故障停机'),
        value: p.state,
      })
    ;(p.alarms ?? []).forEach((a) => {
      if (a.level === 'a' || a.level === 'r')
        out.push({
          level: sigLevel(a.level),
          time: ts(idx++),
          source: `${p.id}·${a.name}`,
          message: tl('油泵运行告警'),
          value: a.value,
        })
    })
    ;(p.protections ?? []).forEach((pr) => {
      if (pr.level === 'a' || pr.level === 'r')
        out.push({
          level: sigLevel(pr.level),
          time: ts(idx++),
          source: `${p.id}·${pr.name}`,
          message: tl('油泵保护动作'),
          value: pr.state,
        })
    })
  })
  const press = s.value?.pipeline?.pressure ?? 0
  if (press > 0.5)
    out.push({
      level: 'warning',
      time: ts(idx++),
      source: tl('供油管道'),
      message: tl('管道压力偏高'),
      value: fmt(press, 2) + ' MPa',
    })
  if (enduranceHours.value < 12)
    out.push({
      level: enduranceHours.value < 8 ? 'critical' : 'warning',
      time: ts(idx++),
      source: tl('续航预测'),
      message: tl('满载续航低于设计要求 12h'),
      value: fmt(enduranceHours.value, 1) + ' h',
    })

  return out.slice(0, 16)
})
const criticalCount = computed(() => alarms.value.filter((a) => a.level === 'critical').length)
const warningCount = computed(() => alarms.value.filter((a) => a.level === 'warning').length)
const infoCount = computed(() => alarms.value.filter((a) => a.level === 'info').length)

// ──────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────
function avgOf(list: number[]): number {
  const vals = list.filter((v) => v != null && Number.isFinite(v))
  if (!vals.length) return 0
  return Number((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1))
}
function rnd(amp: number): number {
  return (Math.random() - 0.5) * amp
}

function levelTextCls(level: number): string {
  if (level < LOW_LEVEL || level > HIGH_LEVEL) return 'r-text'
  if (level < WARN_LEVEL) return 'a-text'
  return 'g-text'
}
function levelNodeCls(level: number): string {
  if (level < LOW_LEVEL || level > HIGH_LEVEL) return 'r'
  if (level < WARN_LEVEL) return 'a'
  return 'g'
}
function barColorOf(level: number): string {
  if (level < LOW_LEVEL || level > HIGH_LEVEL) return '#ef4444'
  if (level < WARN_LEVEL) return '#f59e0b'
  return '#22c55e'
}
function sigCls(level: string): string {
  if (level === 'g') return 'g-text'
  if (level === 'a') return 'a-text'
  if (level === 'r') return 'r-text'
  return ''
}
function sigLevel(level: string): 'critical' | 'warning' | 'info' {
  if (level === 'r') return 'critical'
  if (level === 'a') return 'warning'
  return 'info'
}
function pumpTagCls(st: string): string {
  if (st === '运行') return 'g'
  if (st === '故障') return 'r'
  if (st === '备用') return 'b'
  return 'a'
}
function pumpDotCls(st: string): string {
  if (st === '运行') return 'g'
  if (st === '故障') return 'r'
  if (st === '备用') return 'b'
  return 'a'
}
function levelTagCls(level: string): string {
  if (level === 'critical') return 'r'
  if (level === 'warning') return 'a'
  return 'b'
}
function levelText(level: string): string {
  if (level === 'critical') return tl('紧急')
  if (level === 'warning') return tl('预警')
  return tl('提示')
}

// ──────────────────────────────────────────
// Mock fallback
// ──────────────────────────────────────────
function mockSummary(): FuelSummary {
  const mkMain = (id: string, cap: number, level: number, t: number): FuelMainTankView => ({
    id,
    cap,
    level,
    t,
    water: '正常',
    leak: '正常',
    valves: [
      { name: '出油阀', state: '开启', level: 'g' },
      { name: '进油阀', state: '闭合', level: 'b' },
      { name: '排污阀', state: '闭合', level: 'b' },
    ],
    switches: [
      {
        name: 'LSHH',
        th: '高高位 90%',
        state: level > 90 ? '动作' : '正常',
        level: level > 90 ? 'r' : 'g',
      },
      {
        name: 'LSH',
        th: '高位 85%',
        state: level > 85 ? '动作' : '正常',
        level: level > 85 ? 'a' : 'g',
      },
      {
        name: 'LSL',
        th: '低位 30%',
        state: level < 30 ? '动作' : '正常',
        level: level < 30 ? 'a' : 'g',
      },
      {
        name: 'LSLL',
        th: '低低位 20%',
        state: level < 20 ? '动作' : '正常',
        level: level < 20 ? 'r' : 'g',
      },
    ],
    protections: [
      { name: '渗漏检测', state: '正常', level: 'g' },
      { name: '呼吸阀', state: '正常', level: 'g' },
      { name: '静电接地', state: '正常', level: 'g' },
    ],
  })
  const mkDay = (id: string, cap: number, level: number): FuelDayTankView => ({
    id,
    cap,
    level,
    leak: '正常',
    valve: { name: '进油阀', state: level < 60 ? '开启' : '闭合', level: level < 60 ? 'g' : 'b' },
    switches: [
      {
        name: 'LSH',
        th: '高位 90%',
        state: level > 90 ? '动作' : '正常',
        level: level > 90 ? 'a' : 'g',
      },
      {
        name: 'LSL',
        th: '低位 30%',
        state: level < 30 ? '动作' : '正常',
        level: level < 30 ? 'a' : 'g',
      },
    ],
    protections: [
      { name: '溢流保护', state: '正常', level: 'g' },
      { name: '渗漏检测', state: '正常', level: 'g' },
    ],
  })
  return {
    mainTanks: [mkMain('T-01', 30000, 76.4, 26.8), mkMain('T-02', 30000, 28.6, 27.4)],
    dayTanks: [mkDay('DT-01', 1000, 82), mkDay('DT-02', 1000, 68), mkDay('DT-03', 1000, 45)],
    pumps: [
      {
        id: 'P-01 供油泵',
        state: '运行',
        mode: '自动',
        alarms: [{ name: '过载', value: '正常', level: 'g' }],
        protections: [
          { name: '干转保护', state: '正常', level: 'g' },
          { name: '过流保护', state: '正常', level: 'g' },
        ],
      },
      {
        id: 'P-02 供油泵',
        state: '备用',
        mode: '自动',
        alarms: [{ name: '过载', value: '正常', level: 'g' }],
        protections: [{ name: '干转保护', state: '正常', level: 'g' }],
      },
      {
        id: 'P-03 回油泵',
        state: '停机',
        mode: '手动',
        alarms: [{ name: '密封泄漏', value: '轻微', level: 'a' }],
        protections: [{ name: '过流保护', state: '正常', level: 'g' }],
      },
    ],
    endurance: 0,
    contract: '2 小时应急送油 (三方框架协议)',
    pipeline: { pressure: 0.32, state: '正常供油', tracing: '电伴热运行 · 12°C' },
    knowledge: {
      thresholds: [
        { k: '储油罐低位报警', v: '< 20%', note: '触发应急补油流程' },
        { k: '储油罐低位预警', v: '< 30%', note: '安排 24h 内补给' },
        { k: '高位溢流', v: '> 90%', note: '联锁关闭进油阀' },
        { k: '满载续航要求', v: '≥ 12 h', note: 'T3 等级数据中心' },
        { k: '管道压力上限', v: '0.5 MPa', note: '超限停泵' },
        { k: '日用油箱容量', v: '1000 L / 台', note: '独立供单台机组' },
      ],
      arch: {
        components: [
          '室外储油罐 ×2',
          '日用油箱 ×3',
          '供油泵 ×2',
          '回油泵 ×1',
          '电动阀组',
          '液位四段开关',
          '渗漏检测绳',
          '燃油 PLC',
        ],
        design:
          '燃油监控 PLC 采集储油罐/日用油箱液位、阀门开合、油泵运行与保护信号，按液位阈值自动启停供油泵向日用油箱补油，异常时联锁停泵并上报动环告警。',
        redundancy: '供油泵 1 用 1 备自动切换，储油罐双罐互备，日用油箱一机一箱',
      },
      logic: [],
      faults: [
        {
          no: 1,
          fault: '储油罐低低位 (<20%)',
          lock: '锁定供油泵启动，柴发限时运行',
          action: '启动应急送油合同，人工确认后复位',
          manualReset: true,
        },
        {
          no: 2,
          fault: '日用油箱高位溢流',
          lock: '联锁关闭进油阀并停供油泵',
          action: '检查液位开关与电动阀，排空至 85% 以下',
          manualReset: true,
        },
        {
          no: 3,
          fault: '油泵干转',
          lock: '立即停泵，切至备用泵',
          action: '检查吸油管路与滤网',
          manualReset: true,
        },
        {
          no: 4,
          fault: '管道压力超限 (>0.5MPa)',
          lock: '停泵保护',
          action: '检查阀门是否误闭合',
          manualReset: false,
        },
        {
          no: 5,
          fault: '渗漏检测报警',
          lock: '关闭对应罐出油阀',
          action: '现场确认渗漏点，切换至备用罐',
          manualReset: true,
        },
      ],
    },
    total: 8,
    online: 8,
    avgLoadPercent: null,
    avgVoltage: null,
    avgCurrent: null,
    devices: [],
  }
}

// ──────────────────────────────────────────
// Load
// ──────────────────────────────────────────
async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const data = await getPowerFuelDetailed()
    if (data && (data.mainTanks?.length || data.dayTanks?.length || data.pumps?.length)) {
      s.value = data
    } else {
      s.value = mockSummary()
    }
    rebuildTrend()
  } catch (e: unknown) {
    error.value = (e as ErrorLike)?.message || String(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
  timer = window.setInterval(loadData, 30000)
})
onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
/* ── view-head ── */
.view-head {
  margin-bottom: 16px;
}
.view-head h1 {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary, #e5e7eb);
  margin: 0;
}
.view-head .sub {
  font-size: 0.75rem;
  color: var(--text-muted, #6b7280);
  margin-top: 2px;
  display: block;
}

/* ── grid ── */
.grid {
  display: grid;
  gap: 14px;
  margin-bottom: 14px;
}
.grid.cols-6 {
  grid-template-columns: repeat(6, 1fr);
}
.grid.cols-3 {
  grid-template-columns: repeat(3, 1fr);
}
.grid.cols-2 {
  grid-template-columns: repeat(2, 1fr);
}
.sub-grid {
  margin-bottom: 10px;
}

.badges {
  display: flex;
  gap: 6px;
}
.head-stats {
  display: flex;
  gap: 18px;
}
.hs {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  font-size: 11px;
}
.hs .k {
  color: var(--text-muted, #94a3b8);
}
.hs .v {
  color: var(--text-primary, #e5e7eb);
  font-weight: 600;
}

/* ── SVG 油罐 ── */
.schematic-wrap {
  background: rgba(15, 23, 42, 0.5);
  border-radius: 8px;
  padding: 8px;
}
.fuel-svg {
  width: 100%;
  height: auto;
  display: block;
}
.tank-node {
  cursor: pointer;
}
.tank-shell {
  fill: rgba(30, 41, 59, 0.65);
  stroke: #475569;
  stroke-width: 2;
  transition: filter 0.2s;
}
.tank-node:hover .tank-shell {
  filter: drop-shadow(0 0 8px rgba(34, 211, 238, 0.6));
  stroke: #22d3ee;
}
.oil-body {
  transition:
    y 0.8s ease,
    height 0.8s ease;
}
.oil-wave {
  animation: waveMove 4s linear infinite;
}
.oil-wave.slow {
  animation-duration: 7s;
}
@keyframes waveMove {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(110px);
  }
}
.tick-line {
  stroke: rgba(148, 163, 184, 0.25);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}
.tick-text {
  fill: #64748b;
  font-size: 9px;
}
.tank-pct {
  font-size: 20px;
  font-weight: 800;
  text-anchor: middle;
  paint-order: stroke;
  stroke: rgba(15, 23, 42, 0.85);
  stroke-width: 3px;
}
.tank-vol {
  fill: #cbd5e1;
  font-size: 11px;
  text-anchor: middle;
  paint-order: stroke;
  stroke: rgba(15, 23, 42, 0.7);
  stroke-width: 3px;
}
.tank-id {
  fill: #e5e7eb;
  font-size: 13px;
  font-weight: 700;
  text-anchor: middle;
}
.day-pct {
  font-size: 14px;
  font-weight: 700;
  text-anchor: middle;
  paint-order: stroke;
  stroke: rgba(15, 23, 42, 0.85);
  stroke-width: 3px;
}
.day-id {
  fill: #cbd5e1;
  font-size: 11px;
  text-anchor: middle;
}
.day-load {
  fill: #64748b;
  font-size: 10px;
  text-anchor: middle;
}
.pipe {
  stroke: #475569;
  stroke-width: 3;
  stroke-linecap: round;
}
.pipe.active {
  stroke: #22d3ee;
  stroke-dasharray: 8 6;
  animation: flow 1.2s linear infinite;
}
@keyframes flow {
  to {
    stroke-dashoffset: -28;
  }
}
.pipe-label {
  fill: #22d3ee;
  font-size: 11px;
  text-anchor: middle;
}
.pump-box {
  fill: rgba(34, 211, 238, 0.14);
  stroke: #22d3ee;
  stroke-width: 1.5;
  cursor: pointer;
}
.pump-box:hover {
  filter: drop-shadow(0 0 8px rgba(34, 211, 238, 0.7));
}
.pump-text {
  fill: #e5e7eb;
  font-size: 11px;
  font-weight: 600;
  text-anchor: middle;
  pointer-events: none;
}

/* SVG 文本颜色 (fill 覆盖) */
.g-text {
  color: #22c55e;
  fill: #22c55e;
}
.a-text {
  color: #f59e0b;
  fill: #f59e0b;
}
.r-text {
  color: #ef4444;
  fill: #ef4444;
}

/* legend */
.legend {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  flex-wrap: wrap;
}
.lg {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--text-muted, #94a3b8);
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.dot.g {
  background: #22c55e;
}
.dot.a {
  background: #f59e0b;
}
.dot.r {
  background: #ef4444;
}
.dot.b {
  background: #3b82f6;
}

/* 节点详情 */
.node-detail {
  margin-top: 12px;
  border: 1px solid var(--border, #334155);
  border-radius: 8px;
  padding: 12px 14px;
  background: rgba(30, 41, 59, 0.5);
}
.nd-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.nd-code {
  font-family: monospace;
  font-weight: 700;
  font-size: 13px;
  padding: 1px 8px;
  border-radius: 5px;
}
.nd-code.g {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.12);
}
.nd-code.r {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.12);
}
.nd-code.a {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.12);
}
.nd-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #e5e7eb);
}
.nd-close {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--text-muted, #94a3b8);
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
}
.nd-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 6px 18px;
}
.nd-kv {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px dotted rgba(51, 65, 85, 0.5);
}
.nd-k {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}
.nd-v {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  font-weight: 500;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ── 趋势区间切换 ── */
.range-tabs {
  display: inline-flex;
  gap: 4px;
  background: rgba(15, 23, 42, 0.6);
  padding: 3px;
  border-radius: 8px;
}
.rt-btn {
  border: none;
  background: transparent;
  color: var(--text-muted, #94a3b8);
  font-size: 11px;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
}
.rt-btn.on {
  background: rgba(34, 211, 238, 0.16);
  color: #22d3ee;
  font-weight: 600;
}
.stat-box {
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid var(--border, #334155);
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sb-k {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}
.sb-v {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary, #e5e7eb);
}
.sb-v small {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted, #94a3b8);
  margin-left: 2px;
}

/* ── 低油量预警 ── */
.warn-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.warn-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  background: rgba(30, 41, 59, 0.5);
  border-left: 3px solid transparent;
}
.warn-row.critical {
  border-left-color: #ef4444;
}
.warn-row.warning {
  border-left-color: #f59e0b;
}
.w-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: 0 0 auto;
}
.w-dot.critical {
  background: #ef4444;
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.8);
  animation: pulse 1.4s infinite;
}
.w-dot.warning {
  background: #f59e0b;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
.w-id {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #e5e7eb);
  min-width: 64px;
}
.w-bar {
  flex: 0 0 110px;
  height: 6px;
  border-radius: 3px;
  background: rgba(51, 65, 85, 0.7);
  overflow: hidden;
}
.w-bar i {
  display: block;
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s;
}
.w-pct {
  font-size: 12px;
  font-weight: 700;
  min-width: 50px;
  text-align: right;
}
.w-msg {
  flex: 1;
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
}
.w-th {
  font-size: 11px;
}
.thr-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border, #334155);
}
.thr {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}

/* ── 续航预测 ── */
.gauge-row {
  display: flex;
  justify-content: space-around;
  gap: 12px;
  flex-wrap: wrap;
}
.gauge-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.gauge-num {
  font-size: 14px;
  font-weight: 700;
}
.gauge-cap {
  font-size: 10px;
}
.pred-list {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid var(--border, #334155);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.pred-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  padding: 4px 0;
  border-bottom: 1px dashed rgba(51, 65, 85, 0.5);
}
.pred-row .k {
  color: var(--text-muted, #94a3b8);
}
.pred-row .v {
  color: var(--text-secondary, #94a3b8);
  font-weight: 500;
}

/* ── 油泵 ── */
.pump-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}
.pump-block {
  border: 1px solid rgba(51, 65, 85, 0.7);
  border-radius: 8px;
  padding: 10px 12px;
  background: rgba(15, 23, 42, 0.4);
}
.pump-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.pump-head .tag {
  margin-left: auto;
}
.pump-mode {
  font-size: 11px;
}
.d-status {
  font-size: 9px;
}
.d-status.g {
  color: #22c55e;
}
.d-status.r {
  color: #ef4444;
}
.d-status.a {
  color: #f59e0b;
}
.d-status.b {
  color: #3b82f6;
}
.sig-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 4px;
}
.sig {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  padding: 2px 7px;
  border-radius: 4px;
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(51, 65, 85, 0.7);
}
.sig-k {
  color: var(--text-muted, #94a3b8);
}
.sig-v {
  font-weight: 600;
}

/* ── table ── */
.scroll-x {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}
th {
  text-align: left;
  color: var(--text-muted, #6b7280);
  font-weight: 600;
  font-size: 10px;
  letter-spacing: 0.4px;
  padding: 7px 8px;
  border-bottom: 1px solid var(--border, #334155);
  white-space: nowrap;
}
td {
  padding: 6px 8px;
  border-bottom: 1px solid rgba(51, 65, 85, 0.5);
  color: var(--text-secondary, #94a3b8);
  white-space: nowrap;
}
tbody tr:hover {
  background: rgba(255, 255, 255, 0.03);
}
.tank-row {
  cursor: pointer;
}
.d-name {
  font-weight: 500;
  color: var(--text-primary, #e5e7eb);
}
.mono {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

.mini-tbl th,
.mini-tbl td {
  font-size: 11px;
  padding: 5px 6px;
}

/* ── 告警 ── */
.alarm-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.alarm-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  background: rgba(30, 41, 59, 0.5);
  border-left: 3px solid transparent;
}
.alarm-row.critical {
  border-left-color: #ef4444;
}
.alarm-row.warning {
  border-left-color: #f59e0b;
}
.alarm-row.info {
  border-left-color: #3b82f6;
}
.a-ts {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}
.a-src {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #e5e7eb);
  min-width: 110px;
}
.a-msg {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  flex: 1;
}
.a-val {
  font-size: 11px;
  color: #f59e0b;
}

/* ── error/empty ── */
.err-card {
  text-align: center;
  padding: 32px 16px;
}
.err-title {
  font-size: 1rem;
  font-weight: 700;
  color: #ef4444;
  margin-bottom: 8px;
}
.err-detail {
  font-size: 0.75rem;
  color: var(--text-muted, #6b7280);
  margin-bottom: 14px;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: 6px;
  border: 1px solid var(--border, #334155);
  background: transparent;
  color: var(--text-primary, #e5e7eb);
  font-size: 0.75rem;
  cursor: pointer;
}
.btn:hover {
  background: rgba(255, 255, 255, 0.05);
}
.empty-tip {
  text-align: center;
  padding: 20px;
  font-size: 12px;
}

/* ── responsive ── */
@media (max-width: 1280px) {
  .grid.cols-6 {
    grid-template-columns: repeat(3, 1fr);
  }
  .grid.cols-3 {
    grid-template-columns: 1fr;
  }
  .grid.cols-2 {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 860px) {
  .grid.cols-6 {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
