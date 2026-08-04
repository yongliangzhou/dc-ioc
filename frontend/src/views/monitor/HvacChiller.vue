<template>
  <div class="chiller-page">
    <!-- ========== 顶栏：页面标题 + 控制栏 ========== -->
    <div class="page-topbar">
      <h2 class="page-title">
        <span class="title-icon">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--cyan)"
            stroke-width="2"
          >
            <path d="M12 2L4 6v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V6l-8-4z" />
          </svg>
        </span>
        冷源系统
        <span class="page-subtitle">Chiller Plant Monitoring</span>
      </h2>
      <div class="topbar-actions">
        <TimeRangePicker v-model="activeRange" />
        <button class="btn-refresh" @click="loadData" :disabled="loading">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            :class="{ spinning: loading }"
          >
            <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
            <path d="M21 3v5h-5" />
          </svg>
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
      </div>
    </div>

    <!-- ========== KPI 指标卡片行 ========== -->
    <div class="kpi-row">
      <KpiCard
        title="运行模式"
        :value="chiller?.mode || '-'"
        unit=""
        :trend="0"
        :subtitle="modeDesc"
        :valueClass="modeClass"
      />
      <KpiCard
        title="冷冻供水温度"
        :value="chiller?.supplyTemp ?? 0"
        unit="℃"
        :decimals="1"
        :target="chiller?.targetSupplyTemp"
        targetLabel="设定"
        :trend="0"
      />
      <KpiCard
        title="冷冻回水温度"
        :value="chiller?.returnTemp ?? 0"
        unit="℃"
        :decimals="1"
        :trend="0"
      />
      <KpiCard
        title="室外温度"
        :value="chiller?.outdoorTemp ?? 0"
        unit="℃"
        :decimals="1"
        :subtitle="`湿球 ${chiller?.wetBulb ?? '-'}℃ | RH ${chiller?.outdoorRH ?? '-'}%`"
        :trend="0"
      />
      <KpiCard
        title="部分负载率 PLR"
        :value="chiller?.plr ?? 0"
        unit="%"
        :decimals="1"
        :progress="chiller?.plr ?? 0"
        :progressColor="plrColor"
        :trend="0"
      />
      <KpiCard
        title="制冷总量"
        :value="chiller?.coolingCap ?? 0"
        unit="MW"
        :decimals="2"
        :trend="0"
      />
      <KpiCard title="系统流量" :value="chiller?.flow ?? 0" unit="m³/h" :decimals="0" :trend="0" />
      <KpiCard
        title="在线 / 总数"
        :value="`${chiller?.online ?? 0} / ${chiller?.total ?? 0}`"
        unit=""
        :subtitle="
          chiller?.total ? `${((chiller.online / chiller.total) * 100).toFixed(0)}% 在线率` : ''
        "
        :trend="0"
      />
    </div>

    <!-- ========== 系统工艺流程图 (SVG 组态) ========== -->
    <div class="section">
      <h3 class="section-title"><span class="dot c0"></span> 系统工艺流程</h3>
      <div class="flow-svg-wrap">
        <svg viewBox="0 0 1000 340" class="flow-svg" @click="onFlowClick">
          <!-- 冷冻回水总管 -->
          <rect
            x="20"
            y="130"
            width="60"
            height="100"
            rx="4"
            fill="rgba(6,182,212,0.08)"
            stroke="var(--cyan)"
            stroke-width="1"
          />
          <text x="50" y="175" text-anchor="middle" fill="var(--cyan)" font-size="11">
            冷冻回水
          </text>
          <text x="50" y="192" text-anchor="middle" fill="var(--txt3)" font-size="9">总管</text>
          <text
            x="50"
            y="218"
            text-anchor="middle"
            fill="var(--txt)"
            font-size="11"
            font-weight="700"
          >
            {{ chiller?.returnTemp ?? '-' }}℃
          </text>

          <!-- 冷水机组 1 -->
          <rect
            x="120"
            y="80"
            width="120"
            height="200"
            rx="8"
            class="flow-chiller"
            :class="chillerState(0)"
            data-idx="0"
          />
          <text
            x="180"
            y="140"
            text-anchor="middle"
            fill="var(--txt)"
            font-size="13"
            font-weight="700"
          >
            {{ groupName(0) }}
          </text>
          <StatusBadge :status="groupStatus(0)" size="tiny" class="flow-badge" />
          <text
            x="180"
            y="200"
            text-anchor="middle"
            :fill="groupStatus(0) === 'online' ? '#22c55e' : 'var(--txt3)'"
            font-size="18"
            font-weight="800"
          >
            {{ groupLoad(0) }}%
          </text>
          <text x="180" y="218" text-anchor="middle" fill="var(--cyan)" font-size="10">
            COP {{ groupCop(0) }}
          </text>
          <text x="180" y="235" text-anchor="middle" fill="var(--txt)" font-size="10">
            {{ groupEvapT(0) }} / {{ groupCondT(0) }}℃
          </text>
          <text
            x="180"
            y="260"
            text-anchor="middle"
            fill="var(--txt3)"
            font-size="9"
            class="click-hint"
          >
            点击查看详情
          </text>

          <!-- 冷水机组 2 -->
          <rect
            x="280"
            y="80"
            width="120"
            height="200"
            rx="8"
            class="flow-chiller"
            :class="chillerState(1)"
            data-idx="1"
          />
          <text
            x="340"
            y="140"
            text-anchor="middle"
            fill="var(--txt)"
            font-size="13"
            font-weight="700"
          >
            {{ groupName(1) }}
          </text>
          <StatusBadge :status="groupStatus(1)" size="tiny" class="flow-badge" />
          <text
            x="340"
            y="200"
            text-anchor="middle"
            :fill="groupStatus(1) === 'online' ? '#22c55e' : 'var(--txt3)'"
            font-size="18"
            font-weight="800"
          >
            {{ groupLoad(1) }}%
          </text>
          <text x="340" y="218" text-anchor="middle" fill="var(--cyan)" font-size="10">
            COP {{ groupCop(1) }}
          </text>
          <text x="340" y="235" text-anchor="middle" fill="var(--txt)" font-size="10">
            {{ groupEvapT(1) }} / {{ groupCondT(1) }}℃
          </text>
          <text
            x="340"
            y="260"
            text-anchor="middle"
            fill="var(--txt3)"
            font-size="9"
            class="click-hint"
          >
            点击查看详情
          </text>

          <!-- 冷水机组 3 -->
          <rect
            x="440"
            y="80"
            width="120"
            height="200"
            rx="8"
            class="flow-chiller"
            :class="chillerState(2)"
            data-idx="2"
          />
          <text
            x="500"
            y="140"
            text-anchor="middle"
            fill="var(--txt)"
            font-size="13"
            font-weight="700"
          >
            {{ groupName(2) }}
          </text>
          <StatusBadge :status="groupStatus(2)" size="tiny" class="flow-badge" />
          <text
            x="500"
            y="200"
            text-anchor="middle"
            :fill="groupStatus(2) === 'online' ? '#22c55e' : 'var(--txt3)'"
            font-size="18"
            font-weight="800"
          >
            {{ groupLoad(2) }}%
          </text>
          <text x="500" y="218" text-anchor="middle" fill="var(--cyan)" font-size="10">
            COP {{ groupCop(2) }}
          </text>
          <text x="500" y="235" text-anchor="middle" fill="var(--txt)" font-size="10">
            {{ groupEvapT(2) }} / {{ groupCondT(2) }}℃
          </text>
          <text
            x="500"
            y="260"
            text-anchor="middle"
            fill="var(--txt3)"
            font-size="9"
            class="click-hint"
          >
            点击查看详情
          </text>

          <!-- 冷冻供水总管 -->
          <rect
            x="600"
            y="130"
            width="60"
            height="100"
            rx="4"
            fill="rgba(34,197,94,0.08)"
            stroke="var(--green)"
            stroke-width="1"
          />
          <text x="630" y="175" text-anchor="middle" fill="var(--green)" font-size="11">
            冷冻供水
          </text>
          <text x="630" y="192" text-anchor="middle" fill="var(--txt3)" font-size="9">总管</text>
          <text
            x="630"
            y="218"
            text-anchor="middle"
            fill="var(--txt)"
            font-size="11"
            font-weight="700"
          >
            {{ chiller?.supplyTemp ?? '-' }}℃
          </text>

          <!-- 冷却塔 -->
          <rect
            x="700"
            y="60"
            width="90"
            height="100"
            rx="6"
            fill="rgba(249,115,22,0.06)"
            stroke="var(--amber)"
            stroke-width="1"
            stroke-dasharray="4"
          />
          <text x="745" y="100" text-anchor="middle" fill="var(--amber)" font-size="11">
            冷却塔
          </text>
          <text x="745" y="118" text-anchor="middle" fill="var(--txt3)" font-size="9">
            ×{{ chiller?.towers?.length || 0 }}台
          </text>
          <text x="745" y="140" text-anchor="middle" fill="var(--txt)" font-size="10">
            {{ towerSummary }}
          </text>
          <text
            x="745"
            y="158"
            text-anchor="middle"
            fill="var(--txt3)"
            font-size="9"
            class="click-hint"
          >
            点击展开
          </text>

          <!-- 冷冻泵 CHWP -->
          <rect
            x="120"
            y="295"
            width="120"
            height="40"
            rx="4"
            fill="rgba(6,182,212,0.06)"
            stroke="var(--line)"
            stroke-width="1"
          />
          <text x="180" y="318" text-anchor="middle" fill="var(--cyan)" font-size="11">
            ❰ 冷冻一次泵 CHWP
          </text>

          <!-- 冷却泵 CWP -->
          <rect
            x="280"
            y="295"
            width="120"
            height="40"
            rx="4"
            fill="rgba(249,115,22,0.06)"
            stroke="var(--line)"
            stroke-width="1"
          />
          <text x="340" y="318" text-anchor="middle" fill="var(--amber)" font-size="11">
            ❰ 冷却水泵 CWP
          </text>

          <!-- 板换 -->
          <rect
            x="440"
            y="295"
            width="120"
            height="40"
            rx="4"
            fill="rgba(139,92,246,0.06)"
            stroke="var(--line)"
            stroke-width="1"
          />
          <text x="500" y="318" text-anchor="middle" fill="var(--purple2, #8b5cf6)" font-size="11">
            ❰ 板式换热器
          </text>

          <!-- 连接线（简化：水平线 + 箭头） -->
          <line
            x1="80"
            y1="180"
            x2="115"
            y2="180"
            stroke="var(--cyan)"
            stroke-width="2"
            marker-end="url(#arrowCyan)"
          />
          <line x1="240" y1="180" x2="275" y2="180" stroke="var(--cyan)" stroke-width="2" />
          <line x1="400" y1="180" x2="435" y2="180" stroke="var(--cyan)" stroke-width="2" />
          <line
            x1="560"
            y1="180"
            x2="595"
            y2="180"
            stroke="var(--green)"
            stroke-width="2"
            marker-end="url(#arrowGreen)"
          />
          <line
            x1="660"
            y1="180"
            x2="695"
            y2="120"
            stroke="var(--amber)"
            stroke-width="1.5"
            stroke-dasharray="5 3"
          />
          <line
            x1="745"
            y1="160"
            x2="745"
            y2="295"
            stroke="var(--amber)"
            stroke-width="1.5"
            stroke-dasharray="5 3"
            marker-end="url(#arrowAmber)"
          />

          <!-- 箭头定义 -->
          <defs>
            <marker
              id="arrowCyan"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto"
            >
              <path d="M0,0 L10,5 L0,10 z" fill="var(--cyan)" />
            </marker>
            <marker
              id="arrowGreen"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto"
            >
              <path d="M0,0 L10,5 L0,10 z" fill="var(--green)" />
            </marker>
            <marker
              id="arrowAmber"
              viewBox="0 0 10 10"
              refX="5"
              refY="10"
              markerWidth="6"
              markerHeight="6"
              orient="auto"
            >
              <path d="M0,0 L10,0 L5,10 z" fill="var(--amber)" />
            </marker>
          </defs>
        </svg>
      </div>
    </div>

    <!-- ========== 制冷机组分组详情 ========== -->
    <div class="section">
      <h3 class="section-title">
        <span class="dot c0"></span> 制冷机组分组 (CH ↔ 冷冻泵 ↔ 冷却泵 ↔ 蓄冷罐)
      </h3>
      <div class="chiller-groups">
        <GroupCard
          v-for="(g, i) in chillerGroups"
          :key="'g' + i"
          :title="g.chiller?.id || `机组 ${i + 1}`"
          :status="
            g.chiller?.state === '运行'
              ? 'online'
              : g.chiller?.state === '检修'
                ? 'fault'
                : 'standby'
          "
          :defaultOpen="i === 0"
        >
          <!-- 冷机核心指标 -->
          <div class="group-grid">
            <KpiCard
              title="负载率"
              :value="g.chiller?.load ?? 0"
              unit="%"
              :progress="g.chiller?.load ?? 0"
              :progressColor="
                (g.chiller?.load ?? 0) > 80
                  ? 'var(--red)'
                  : (g.chiller?.load ?? 0) > 60
                    ? 'var(--amber)'
                    : 'var(--cyan)'
              "
              size="sm"
            />
            <KpiCard
              title="COP 能效比"
              :value="g.chiller?.cop ?? 0"
              unit=""
              :decimals="2"
              :valueClass="(g.chiller?.cop ?? 0) >= 6 ? 'val-good' : ''"
              size="sm"
            />
            <KpiCard title="蒸发温度" :value="g.chiller?.evapT ?? '-'" unit="℃" size="sm" />
            <KpiCard title="冷凝温度" :value="g.chiller?.condT ?? '-'" unit="℃" size="sm" />
            <KpiCard
              title="运行电流"
              :value="g.chiller?.current ?? 0"
              unit="A"
              :decimals="1"
              size="sm"
            />
            <KpiCard
              title="累计运行"
              :value="g.chiller?.runHrs ?? 0"
              unit="h"
              :decimals="0"
              size="sm"
            />
          </div>

          <!-- 冷冻泵 -->
          <div v-if="g.chwPump" class="pump-line">
            <span class="pump-label chw">CHW 冷冻泵</span>
            <StatusBadge :status="g.chwPump.state === '运行' ? 'online' : 'standby'" size="tiny" />
            <span class="pump-id">{{ g.chwPump.id }}</span>
            <span class="pump-val">{{ g.chwPump.hz }}Hz</span>
            <span class="pump-val">{{ g.chwPump.flow }}m³/h</span>
            <span class="pump-val">{{ g.chwPump.kw }}kW</span>
          </div>

          <!-- 冷却泵 -->
          <div v-if="g.cwPump" class="pump-line">
            <span class="pump-label cw">CWP 冷却泵</span>
            <StatusBadge :status="g.cwPump.state === '运行' ? 'online' : 'standby'" size="tiny" />
            <span class="pump-id">{{ g.cwPump.id }}</span>
            <span class="pump-val">{{ g.cwPump.hz }}Hz</span>
            <span class="pump-val">{{ g.cwPump.flow }}m³/h</span>
            <span class="pump-val">{{ g.cwPump.kw }}kW</span>
          </div>

          <!-- 蓄冷罐连接 + 控制 -->
          <div class="group-footer">
            <div class="tank-status" :class="{ on: g.tankConnected }">
              {{ g.tankConnected ? `蓄冷罐直连 · 流量 ${g.tankFlow} m³/h` : '未连接蓄冷罐' }}
            </div>
            <QuickControl
              label=""
              :showStartStop="true"
              :running="g.chiller?.state === '运行'"
              :modes="['制冷模式', '预冷模式', '自然冷却']"
              :activeMode="chiller?.mode ?? '制冷模式'"
              @toggleStartStop="onToggleChiller(i)"
              @modeChange="onModeChange(i, $event)"
              :showTemp="true"
              tempLabel="冷冻供水设定"
              :tempValue="chiller?.targetSupplyTemp ?? 7"
              :tempMin="5"
              :tempMax="15"
              :tempStep="0.5"
              @tempChange="onTempSet(i, $event)"
            />
          </div>
        </GroupCard>
      </div>
    </div>

    <!-- ========== 趋势图 1: 冷冻水出水温度 vs 湿球 vs 负载率 ========== -->
    <div class="section">
      <h3 class="section-title">
        <span class="dot c1"></span> 冷冻水出水温度 · 室外湿球温度 · 负载率 叠加趋势
      </h3>
      <TrendChart
        :height="280"
        :xAxisData="freezeTimestamps"
        :series="freezeSeries"
        :loading="trendsLoading"
        :empty="!freezeSeries.length"
        emptyText="暂无趋势数据"
      />
    </div>

    <!-- ========== 趋势图 2: COP vs %RLA 散点 ========== -->
    <div class="section">
      <h3 class="section-title">
        <span class="dot c2"></span> 机组能效比 COP 与负载率 %RLA 散点趋势
      </h3>
      <div ref="copChartEl" class="chart-box"></div>
    </div>

    <!-- ========== 趋势图 3: 冷凝 vs 冷却水温差 ========== -->
    <div class="section">
      <h3 class="section-title"><span class="dot c3"></span> 冷凝水与冷却水出水温差趋势</h3>
      <TrendChart
        :height="280"
        :xAxisData="condTimestamps"
        :series="condSeries"
        :loading="trendsLoading"
        :empty="!condSeries.length"
        emptyText="暂无趋势数据"
      />
    </div>

    <!-- ========== 趋势图 4: 水泵频率 vs 流量 ========== -->
    <div class="section">
      <h3 class="section-title"><span class="dot c4"></span> 水泵频率 Hz 与流量 m³/h 关联趋势</h3>
      <div ref="pumpChartEl" class="chart-box"></div>
    </div>

    <!-- ========== 趋势图 5: 蓄冷罐温度梯度热力图 ========== -->
    <div class="section">
      <h3 class="section-title"><span class="dot c5"></span> 蓄冷罐垂直温度梯度色阶图</h3>
      <HeatmapView
        :xAxisData="tankTimestamps"
        :yAxisData="tankLevels"
        :heatData="tankHeatData"
        :valueRange="[5, 14]"
        :loading="trendsLoading"
        emptyText="暂无罐温数据"
      />
    </div>

    <!-- ========== 趋势图 6: 制冷负载 + 自然冷源利用率 ========== -->
    <div class="section">
      <h3 class="section-title">
        <span class="dot c6"></span> 总制冷负载 RT 与自然冷源利用率 月度柱状叠加
      </h3>
      <TrendChart
        :height="320"
        :xAxisData="monthlyDays"
        :series="monthlySeries"
        :loading="trendsLoading"
        :empty="!monthlySeries.length"
        emptyText="暂无月度数据"
      />
    </div>

    <!-- ========== 趋势图 7: ΔT vs 旁通阀开度 ========== -->
    <div class="section">
      <h3 class="section-title">
        <span class="dot c7"></span> 冷冻水供回水温差 ΔT 与旁通阀开度 — 过去1小时
      </h3>
      <TrendChart
        :height="280"
        :xAxisData="deltaTimestamps"
        :series="deltaSeries"
        :loading="trendsLoading"
        :empty="!deltaSeries.length"
        emptyText="暂无数据"
      />
    </div>

    <!-- ========== 子系统一览：冷却塔 + 板换 + 蓄冷罐 + 水泵 + 阀门 + 管路 ========== -->
    <div class="section" v-if="chiller">
      <h3 class="section-title"><span class="dot c8"></span> 子系统纵览</h3>

      <!-- 冷却塔 -->
      <div class="sub-row" v-if="chiller.towers?.length">
        <h4 class="sub-head">
          冷却塔 <span class="sub-count">{{ chiller.towers.length }}台</span>
        </h4>
        <DeviceTable :columns="towerColumns" :rows="towerRows" :count="chiller.towers.length" />
      </div>

      <!-- 板式换热器 -->
      <div class="sub-row" v-if="chiller.hexs?.length">
        <h4 class="sub-head">
          板式换热器 <span class="sub-count">{{ chiller.hexs.length }}台</span>
        </h4>
        <DeviceTable :columns="hexColumns" :rows="hexRows" :count="chiller.hexs.length" />
      </div>

      <!-- 蓄冷罐 -->
      <div class="sub-row" v-if="chiller.storageTank">
        <h4 class="sub-head">蓄冷罐</h4>
        <div class="tank-info-cards">
          <KpiCard
            title="液位"
            :value="chiller.storageTank.level"
            unit="%"
            :progress="chiller.storageTank.level"
            :progressColor="'var(--green)'"
            size="sm"
          />
          <KpiCard title="运行模式" :value="chiller.storageTank.mode || '-'" unit="" size="sm" />
          <KpiCard
            title="放冷最低液位"
            :value="chiller.storageTank.dischargeMin"
            unit="%"
            size="sm"
          />
          <KpiCard
            title="罐体容量"
            :value="chiller.storageTank.capacity"
            unit="m³"
            :decimals="0"
            size="sm"
          />
          <KpiCard
            title="顶部温度"
            :value="chiller.storageTank.topTemp"
            unit="℃"
            :decimals="1"
            size="sm"
          />
          <KpiCard
            title="底部温度"
            :value="chiller.storageTank.botTemp"
            unit="℃"
            :decimals="1"
            size="sm"
          />
          <KpiCard
            title="当前流量"
            :value="chiller.storageTank.flow"
            unit="m³/h"
            :decimals="0"
            size="sm"
          />
          <KpiCard
            title="功率"
            :value="chiller.storageTank.power"
            unit="kW"
            :decimals="1"
            size="sm"
          />
        </div>
      </div>

      <!-- 水泵总览 -->
      <div class="sub-row">
        <h4 class="sub-head">水泵状态总览</h4>
        <DeviceTable :columns="pumpColumns" :rows="allPumpRows" :count="allPumpRows.length" />
      </div>

      <!-- 管路压力 -->
      <div class="sub-row" v-if="chiller.pipePressure">
        <h4 class="sub-head">管路压力</h4>
        <div class="tank-info-cards">
          <KpiCard
            title="冷冻供水母管"
            :value="chiller.pipePressure.supplyHeader"
            unit="bar"
            :decimals="2"
            size="sm"
          />
          <KpiCard
            title="冷冻回水母管"
            :value="chiller.pipePressure.returnHeader"
            unit="bar"
            :decimals="2"
            size="sm"
          />
          <KpiCard
            title="二次供水母管"
            :value="chiller.pipePressure.secSupplyHeader"
            unit="bar"
            :decimals="2"
            size="sm"
          />
          <KpiCard
            title="二次回水母管"
            :value="chiller.pipePressure.secReturnHeader"
            unit="bar"
            :decimals="2"
            size="sm"
          />
          <KpiCard
            title="冷却供水母管"
            :value="chiller.pipePressure.condenserSupply"
            unit="bar"
            :decimals="2"
            size="sm"
          />
          <KpiCard
            title="冷却回水母管"
            :value="chiller.pipePressure.condenserReturn"
            unit="bar"
            :decimals="2"
            size="sm"
          />
        </div>
      </div>

      <!-- 定压补水 + 旁滤 -->
      <div class="sub-row">
        <h4 class="sub-head">辅助设备</h4>
        <div class="aux-grid">
          <div class="aux-card" v-if="chiller.makeupDevice?.id">
            <div class="aux-title">
              定压补水装置
              <StatusBadge
                :status="chiller.makeupDevice.state === '运行' ? 'online' : 'standby'"
                size="tiny"
              />
            </div>
            <div class="aux-metrics">
              <span
                >供水压力 {{ chiller.makeupDevice.supplyPressure }} /
                {{ chiller.makeupDevice.setpointPressure }} bar</span
              >
              <span>水箱液位 {{ chiller.makeupDevice.tankLevel }}%</span>
              <span>水泵 {{ chiller.makeupDevice.pumpHz }}Hz</span>
              <span>补水流量 {{ chiller.makeupDevice.makeupFlow }}m³/h</span>
            </div>
          </div>
          <div class="aux-card" v-if="chiller.bypassFilter?.id">
            <div class="aux-title">
              旁滤装置
              <StatusBadge
                :status="chiller.bypassFilter.state === '运行' ? 'online' : 'standby'"
                size="tiny"
              />
            </div>
            <div class="aux-metrics">
              <span>流量 {{ chiller.bypassFilter.flow }}m³/h</span>
              <span>压差 {{ chiller.bypassFilter.diffPressure }}bar</span>
              <span>浊度 {{ chiller.bypassFilter.turbidity }}NTU</span>
              <span>滤芯健康 {{ chiller.bypassFilter.filterHealth }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 活跃告警 ========== -->
    <div class="section" v-if="activeAlarms.length">
      <h3 class="section-title">
        <span class="dot danger"></span> 活跃告警
        <span class="alarm-count">{{ activeAlarms.length }}</span>
      </h3>
      <div class="alarm-list">
        <div v-for="(a, ai) in activeAlarms" :key="ai" class="alarm-row" :class="a.level">
          <AlarmBadge :level="a.level" />
          <span class="alarm-ts">{{ a.ts }}</span>
          <span class="alarm-msg">{{ a.msg }}</span>
          <StatusBadge :status="a.status" size="tiny" />
        </div>
      </div>
    </div>

    <!-- ========== 加载骨架屏 / 空状态 ========== -->
    <SkeletonCard v-if="loading && !chiller" size="lg" />
    <EmptyState v-if="!loading && !chiller" text="冷源系统数据加载失败，请刷新重试" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  getChillerPlant,
  getChillerTrends,
  type ChillerSummary,
  type ChillerGroupView,
  type ChillerTrends,
  type PumpView,
} from '@/api/hvac'

interface AlarmLite {
  level?: string
  domain?: string
  system?: string
  source?: string
  status?: string
  timestamp?: string
  message?: string
  title?: string
  summary?: string
  [k: string]: unknown
}

interface PumpRow extends PumpView {
  type: string
  status: string
  inP: number
  outP: number
}
import { getActiveAlarms } from '@/api/index'
import {
  KpiCard,
  StatusBadge,
  AlarmBadge,
  GroupCard,
  TrendChart,
  DeviceTable,
  HeatmapView,
  TimeRangePicker,
  QuickControl,
  EmptyState,
  SkeletonCard,
} from '@/components/monitor'
import { CHART_COLORS } from '@/assets/echarts-theme'

// ---- State ----
const chiller = ref<ChillerSummary | null>(null)
const chillerGroups = ref<ChillerGroupView[]>([])
const trends = ref<ChillerTrends | null>(null)
const activeAlarms = ref<{ level: string; ts: string; msg: string; status: string }[]>([])
const activeRange = ref('24h')
const loading = ref(false)
const trendsLoading = ref(false)

// Chart refs (for scatter charts not covered by TrendChart)
const copChartEl = ref<HTMLDivElement | null>(null)
const pumpChartEl = ref<HTMLDivElement | null>(null)
let copChart: echarts.ECharts | null = null
let pumpChart: echarts.ECharts | null = null
let copRo: ResizeObserver | null = null
let pumpRo: ResizeObserver | null = null

// ---- Colors ----
const C = CHART_COLORS

// ---- Computed: KPI ----
const modeClass = computed(() => {
  const m = chiller.value?.mode
  if (m === '预冷模式') return 'val-cyan'
  if (m === '自然冷却模式') return 'val-green'
  if (m === '制冷模式') return 'val-amber'
  return ''
})
const modeDesc = computed(() => {
  const m = chiller.value?.mode
  if (m === '预冷模式') return '通过板换利用室外低温'
  if (m === '自然冷却模式') return '完全自由冷却，不开压缩机组'
  if (m === '制冷模式') return '压缩机组运行供冷'
  return ''
})
const plrColor = computed(() => {
  const p = chiller.value?.plr ?? 0
  if (p < 50) return 'var(--green)'
  if (p < 80) return 'var(--amber)'
  return 'var(--red)'
})

// ---- Computed: Flow SVG helpers ----
function groupName(i: number) {
  const g = chillerGroups.value[i]
  return g?.chiller?.id ?? `CH-${i + 1}`
}
function groupStatus(i: number) {
  const g = chillerGroups.value[i]
  const s = g?.chiller?.state
  if (s === '运行') return 'online'
  if (s === '检修') return 'fault'
  return 'standby'
}
function groupLoad(i: number) {
  return chillerGroups.value[i]?.chiller?.load ?? 0
}
function groupCop(i: number) {
  return chillerGroups.value[i]?.chiller?.cop ?? '-'
}
function groupEvapT(i: number) {
  return chillerGroups.value[i]?.chiller?.evapT ?? '-'
}
function groupCondT(i: number) {
  return chillerGroups.value[i]?.chiller?.condT ?? '-'
}
function chillerState(i: number) {
  return groupStatus(i)
}
const towerSummary = computed(() => {
  const towers = chiller.value?.towers ?? []
  if (!towers.length) return '-'
  const online = towers.filter((t) => t.state === '投入' || t.state === '运行').length
  return `在线 ${online}/${towers.length}`
})

function onFlowClick(e: MouseEvent) {
  const target = (e.target as Element).closest('.flow-chiller')
  if (!target) return
  const idx = parseInt((target as HTMLElement).dataset.idx ?? '-1')
  if (idx >= 0) {
    // scroll to group card
    const cards = document.querySelectorAll('.group-card')
    if (cards[idx]) cards[idx].scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

// ---- Data Load ----
async function loadData() {
  loading.value = true
  try {
    const [plantRes, trendsRes] = await Promise.all([getChillerPlant(), getChillerTrends()])
    chiller.value = plantRes
    chillerGroups.value = plantRes?.chillerGroups ?? []
    trends.value = trendsRes
    renderEChartsAfterLoad()
  } catch {
    /* silent */
  }
  loading.value = false
}

async function loadAlarms() {
  try {
    const res = await getActiveAlarms()
    const items = res.items ?? []
    const lite = items as AlarmLite[]
    activeAlarms.value = lite
      .filter(
        (a) =>
          (a.system === 'hvac' || a.domain === 'hvac' || a.source === '冷源系统') &&
          a.level &&
          a.level !== 'info' &&
          a.status !== 'acknowledged',
      )
      .slice(0, 10)
      .map((a) => ({
        level: a.level ?? 'warning',
        ts: a.timestamp ? new Date(a.timestamp).toLocaleTimeString('zh-CN') : '',
        msg: a.message ?? a.title ?? a.summary ?? '-',
        status: a.status ?? 'active',
      }))
  } catch {
    /* silent */
  }
}

// ---- TrendChart data formatting ----

// Chart 1: freeze trend
const freezeTimestamps = computed(() => {
  const r = activeRange.value
  const tss = trends.value?.freezeTrend?.[r]?.timestamps ?? []
  return tss.map((t) => fmtTime(t, r))
})
const freezeSeries = computed(() => {
  const r = activeRange.value
  const d = trends.value?.freezeTrend?.[r]
  if (!d) return []
  return [
    {
      name: '冷冻水出水温度',
      type: 'line' as const,
      data: d.supplyTemp,
      color: C.cyan,
      smooth: true,
    },
    {
      name: '室外湿球温度',
      type: 'line' as const,
      data: d.wetBulb,
      color: C.green,
      smooth: true,
      lineStyle: { type: 'dashed' },
    },
    {
      name: '负载率',
      type: 'line' as const,
      data: d.loadPct,
      color: C.orange,
      smooth: true,
      yAxisIndex: 1,
      areaStyle: true,
    },
  ]
})

// Chart 3: cond-cool diff
const condTimestamps = computed(() => {
  const r = activeRange.value
  return (trends.value?.condCoolDiff?.[r]?.timestamps ?? []).map((t) => fmtTime(t, r))
})
const condSeries = computed(() => {
  const r = activeRange.value
  const d = trends.value?.condCoolDiff?.[r]
  if (!d) return []
  return [
    { name: '冷凝出水温', type: 'line' as const, data: d.condTemp, color: C.red, smooth: true },
    { name: '冷却出水温', type: 'line' as const, data: d.coolTemp, color: C.blue, smooth: true },
    {
      name: '温差',
      type: 'line' as const,
      data: d.diff,
      color: C.purple,
      smooth: true,
      lineStyle: { type: 'dashed' },
    },
  ]
})

// Chart 6: monthly
const monthlyDays = computed(() => trends.value?.coolingFreecoolingMonthly?.days ?? [])
const monthlySeries = computed(() => {
  const d = trends.value?.coolingFreecoolingMonthly
  if (!d) return []
  return [
    { name: '制冷负载(RT)', type: 'bar' as const, data: d.coolingLoad, color: C.orange },
    {
      name: '自然冷源利用率(%)',
      type: 'line' as const,
      data: d.freeCoolingPct,
      color: C.green,
      smooth: true,
      yAxisIndex: 1,
      areaStyle: true,
    },
  ]
})

// Chart 7: deltaT bypass
const deltaTimestamps = computed(() => {
  return (trends.value?.deltaTBypass1h?.timestamps ?? []).map((t) => {
    const d = new Date(t)
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })
})
const deltaSeries = computed(() => {
  const d = trends.value?.deltaTBypass1h
  if (!d) return []
  return [
    {
      name: 'ΔT供回水温差',
      type: 'line' as const,
      data: d.deltaT,
      color: C.cyan,
      smooth: true,
      areaStyle: true,
    },
    {
      name: '旁通阀开度',
      type: 'line' as const,
      data: d.bypassValve,
      color: C.orange,
      smooth: true,
      yAxisIndex: 1,
    },
  ]
})

// Chart 5: tank heatmap
const tankTimestamps = computed(() => {
  const r = activeRange.value
  return (trends.value?.tankGradient?.[r]?.timestamps ?? []).map((t) => fmtTime(t, r))
})
const tankLevels = computed(() => trends.value?.tankGradient?.[activeRange.value]?.levels ?? [])
const tankHeatData = computed(() => {
  const r = activeRange.value
  const d = trends.value?.tankGradient?.[r]
  if (!d) return []
  const result: [number, number, number][] = []
  const tss = d.timestamps.length
  for (let lv = 0; lv < d.levels.length; lv++) {
    for (let ti = 0; ti < tss; ti++) {
      result.push([ti, lv, d.data[lv][ti]])
    }
  }
  return result
})

// ---- ECharts scatter charts (2: COP/RLA, 4: Pump freq/flow) ----

function fmtTime(ts: string, range: string): string {
  if (!ts) return ''
  const d = new Date(ts)
  if (range === '24h') return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  if (range === '7d')
    return (
      d.getMonth() +
      1 +
      '/' +
      d.getDate() +
      ' ' +
      d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    )
  return d.getMonth() + 1 + '/' + d.getDate()
}

function initCopChart(el: HTMLDivElement) {
  copChart = echarts.init(el)
  copRo = new ResizeObserver(() => copChart?.resize())
  copRo.observe(el)
}
function renderCopRla() {
  if (!copChart || !trends.value) return
  const r = activeRange.value
  const pts = trends.value.copRlaScatter?.[r]
  if (!pts?.length) return
  const chIds = [...new Set(pts.map((p) => p.chiller))]
  const pal = [C.cyan, C.orange, C.purple, C.green, C.blue, C.red, C.yellow]
  copChart.setOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: (p: echarts.DefaultLabelFormatterCallbackParams) => {
          const v = (Array.isArray(p.value) ? p.value : []) as unknown[]
          return `${v[2]}<br/>RLA: ${v[0]}% | COP: ${v[1]}`
        },
      },
      legend: { data: chIds, bottom: 0, textStyle: { color: '#94a3b8', fontSize: 11 } },
      grid: { left: 55, right: 20, top: 20, bottom: 35 },
      xAxis: {
        type: 'value',
        name: 'RLA (%)',
        nameTextStyle: { color: '#94a3b8' },
        axisLabel: { color: '#64748b' },
        splitLine: { lineStyle: { color: 'var(--line)' } },
      },
      yAxis: {
        type: 'value',
        name: 'COP',
        nameTextStyle: { color: '#94a3b8' },
        axisLabel: { color: '#64748b' },
        splitLine: { lineStyle: { color: 'var(--line)' } },
      },
      series: chIds.map((ch, i) => ({
        name: ch,
        type: 'scatter',
        symbolSize: 8,
        data: pts
          .filter((p) => p.chiller === ch)
          .map((p) => [p.rla, p.cop, `${ch} @ ${fmtTime(p.ts, '24h')}`]),
        itemStyle: { color: pal[i % pal.length], opacity: 0.8 },
      })),
    },
    true,
  )
}

function initPumpChart(el: HTMLDivElement) {
  pumpChart = echarts.init(el)
  pumpRo = new ResizeObserver(() => pumpChart?.resize())
  pumpRo.observe(el)
}
function renderPumpFreqFlow() {
  if (!pumpChart || !trends.value) return
  const r = activeRange.value
  const data = trends.value.pumpFreqFlow?.[r]
  if (!data) return
  function tl(pts: { hz: number; flow: number }[]) {
    if (!pts.length)
      return [
        [0, 0],
        [1, 1],
      ]
    const n = pts.length
    const sx = pts.reduce((s, p) => s + p.hz, 0)
    const sy = pts.reduce((s, p) => s + p.flow, 0)
    const sxy = pts.reduce((s, p) => s + p.hz * p.flow, 0)
    const sxx = pts.reduce((s, p) => s + p.hz * p.hz, 0)
    const slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    const inter = (sy - slope * sx) / n
    const mn = Math.min(...pts.map((p) => p.hz))
    const mx = Math.max(...pts.map((p) => p.hz))
    return [
      [mn, slope * mn + inter],
      [mx, slope * mx + inter],
    ]
  }
  const chwTL = tl(data.chwPump)
  const cwTL = tl(data.cwPump)
  pumpChart.setOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: (p: echarts.DefaultLabelFormatterCallbackParams) => {
          const v = (Array.isArray(p.value) ? p.value : []) as unknown[]
          return `${p.seriesName}<br/>频率: ${v[0]}Hz<br/>流量: ${v[1]}m³/h`
        },
      },
      legend: {
        data: ['冷冻泵', '冷却泵'],
        bottom: 0,
        textStyle: { color: '#94a3b8', fontSize: 11 },
      },
      grid: { left: 55, right: 20, top: 20, bottom: 35 },
      xAxis: {
        type: 'value',
        name: '频率 (Hz)',
        nameTextStyle: { color: '#94a3b8' },
        axisLabel: { color: '#64748b' },
        splitLine: { lineStyle: { color: 'var(--line)' } },
      },
      yAxis: {
        type: 'value',
        name: '流量 (m³/h)',
        nameTextStyle: { color: '#94a3b8' },
        axisLabel: { color: '#64748b' },
        splitLine: { lineStyle: { color: 'var(--line)' } },
      },
      series: [
        {
          name: '冷冻泵',
          type: 'scatter',
          symbolSize: 7,
          data: data.chwPump.map((p) => [p.hz, p.flow]),
          itemStyle: { color: C.cyan, opacity: 0.7 },
        },
        {
          name: '冷冻泵趋势线',
          type: 'line',
          data: chwTL,
          lineStyle: { color: C.cyan, width: 2, type: 'dashed' },
          symbol: 'none',
          silent: true,
        },
        {
          name: '冷却泵',
          type: 'scatter',
          symbolSize: 7,
          data: data.cwPump.map((p) => [p.hz, p.flow]),
          itemStyle: { color: C.orange, opacity: 0.7 },
        },
        {
          name: '冷却泵趋势线',
          type: 'line',
          data: cwTL,
          lineStyle: { color: C.orange, width: 2, type: 'dashed' },
          symbol: 'none',
          silent: true,
        },
      ],
    },
    true,
  )
}

function renderEChartsAfterLoad() {
  nextTick(() => {
    renderCopRla()
    renderPumpFreqFlow()
  })
}

// ---- DeviceTable rows ----
const towerColumns = [
  { key: 'code', label: '编号', width: '80px' },
  { key: 'status', label: '状态', width: '70px', render: 'status' as const },
  { key: 'fanHz', label: '风机Hz', width: '80px', align: 'right' as const },
  { key: 'outTemp', label: '出水温度℃', width: '100px', align: 'right' as const },
]
const towerRows = computed(() =>
  (chiller.value?.towers ?? []).map((t) => ({
    ...t,
    status: t.state === '投入' || t.state === '运行' ? 'online' : 'standby',
  })),
)

const hexColumns = [
  { key: 'code', label: '编号', width: '80px' },
  { key: 'status', label: '状态', width: '70px', render: 'status' as const },
  { key: 'eff', label: '效率%', width: '70px', align: 'right' as const },
  { key: 'priIn', label: '一次进水℃', width: '100px', align: 'right' as const },
  { key: 'priOut', label: '一次出水℃', width: '100px', align: 'right' as const },
  { key: 'secIn', label: '二次进水℃', width: '100px', align: 'right' as const },
  { key: 'secOut', label: '二次出水℃', width: '100px', align: 'right' as const },
]
const hexRows = computed(() =>
  (chiller.value?.hexs ?? []).map((h) => ({
    ...h,
    status: h.state === '投入' || h.state === '运行' ? 'online' : 'standby',
  })),
)

const pumpColumns = [
  { key: 'code', label: '编号', width: '100px' },
  { key: 'type', label: '类型', width: '80px' },
  { key: 'status', label: '状态', width: '70px', render: 'status' as const },
  { key: 'hz', label: '频率Hz', width: '80px', align: 'right' as const },
  { key: 'kw', label: '功率kW', width: '80px', align: 'right' as const },
  { key: 'flow', label: '流量m³/h', width: '90px', align: 'right' as const },
  { key: 'inP', label: '入口bar', width: '80px', align: 'right' as const },
  { key: 'outP', label: '出口bar', width: '80px', align: 'right' as const },
]
const allPumpRows = computed(() => {
  const rows: PumpRow[] = []
  ;(chiller.value?.pumpsChw ?? []).forEach((p) =>
    rows.push({
      ...p,
      type: '一次冷冻泵',
      status: p.state === '运行' ? 'online' : 'standby',
      inP: p.inPressure,
      outP: p.outPressure,
    }),
  )
  ;(chiller.value?.pumpsSec ?? []).forEach((p) =>
    rows.push({
      ...p,
      type: '二次冷冻泵',
      status: p.state === '运行' ? 'online' : 'standby',
      inP: p.inPressure,
      outP: p.outPressure,
    }),
  )
  ;(chiller.value?.pumpsCw ?? []).forEach((p) =>
    rows.push({
      ...p,
      type: '冷却泵',
      status: p.state === '运行' ? 'online' : 'standby',
      inP: p.inPressure,
      outP: p.outPressure,
    }),
  )
  return rows
})

// ---- Controls ----
function onToggleChiller(i: number) {
  const g = chillerGroups.value[i]
  if (!g) return
  console.log('Toggle chiller:', g.chiller?.id)
}
function onModeChange(i: number, mode: string) {
  console.log('Mode change for chiller', i, 'to', mode)
}
function onTempSet(i: number, val: number) {
  console.log('Temp set for chiller', i, 'to', val)
}

// ---- Lifecycle ----
onMounted(() => {
  nextTick(() => {
    if (copChartEl.value) initCopChart(copChartEl.value)
    if (pumpChartEl.value) initPumpChart(pumpChartEl.value)
  })
  loadData()
  loadAlarms()
})

onUnmounted(() => {
  if (copRo) copRo.disconnect()
  if (pumpRo) pumpRo.disconnect()
  copChart?.dispose()
  pumpChart?.dispose()
})

watch(activeRange, () => {
  renderEChartsAfterLoad()
})

// Auto refresh 30s
const refreshTimer = setInterval(() => {
  loadData()
  loadAlarms()
}, 30000)
onUnmounted(() => clearInterval(refreshTimer))
</script>

<style scoped>
.chiller-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px 0;
}

/* Page Topbar */
.page-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}
.page-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--txt);
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
}
.title-icon {
  display: flex;
}
.page-subtitle {
  font-size: 11px;
  font-weight: 400;
  color: var(--txt3);
  margin-left: 4px;
}
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.btn-refresh {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--bg);
  color: var(--txt2);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-refresh:hover {
  border-color: var(--cyan);
  color: var(--cyan);
}
.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.spinning {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* KPI Row */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}

/* Section */
.section {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px 16px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}
.dot.c0 {
  background: #06b6d4;
}
.dot.c1 {
  background: #06b6d4;
}
.dot.c2 {
  background: #f97316;
}
.dot.c3 {
  background: #ef4444;
}
.dot.c4 {
  background: #22c55e;
}
.dot.c5 {
  background: #8b5cf6;
}
.dot.c6 {
  background: #eab308;
}
.dot.c7 {
  background: #3b82f6;
}
.dot.c8 {
  background: #06b6d4;
}
.dot.danger {
  background: #ef4444;
}

.alarm-count {
  font-size: 11px;
  color: var(--txt);
  background: rgba(239, 68, 68, 0.15);
  padding: 1px 8px;
  border-radius: 10px;
  margin-left: auto;
}

/* Flow SVG */
.flow-svg-wrap {
  overflow-x: auto;
  background: var(--bg);
  border-radius: 8px;
  padding: 4px;
}
.flow-svg {
  width: 100%;
  min-width: 840px;
  display: block;
}
.flow-chiller {
  cursor: pointer;
  transition: opacity 0.2s;
}
.flow-chiller:hover {
  opacity: 0.85;
}
.flow-chiller.fault {
  opacity: 0.5;
}
.flow-chiller.standby {
  opacity: 0.6;
}
.flow-badge {
  display: flex;
  justify-content: center;
  margin-top: -2px;
}
.click-hint {
  opacity: 0;
  transition: opacity 0.15s;
}
.flow-chiller:hover .click-hint {
  opacity: 1;
}

/* Group Grid */
.chiller-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.group-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

/* Pump lines */
.pump-line {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  margin-bottom: 4px;
  background: var(--bg);
  border-radius: 6px;
  font-size: 12px;
}
.pump-label {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  min-width: 72px;
  text-align: center;
}
.pump-label.chw {
  background: rgba(6, 182, 212, 0.15);
  color: #06b6d4;
}
.pump-label.cw {
  background: rgba(249, 115, 22, 0.15);
  color: #f97316;
}
.pump-id {
  font-weight: 600;
  color: var(--txt);
  min-width: 60px;
}
.pump-val {
  color: var(--txt2);
  font-variant-numeric: tabular-nums;
}

/* Group Footer */
.group-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  margin-top: 8px;
  border-top: 1px solid var(--line);
  flex-wrap: wrap;
  gap: 8px;
}
.tank-status {
  font-size: 12px;
  color: var(--txt3);
}
.tank-status.on {
  color: #22c55e;
}

/* Subsystem */
.sub-row {
  margin-bottom: 16px;
}
.sub-row:last-child {
  margin-bottom: 0;
}
.sub-head {
  font-size: 13px;
  font-weight: 600;
  color: var(--txt2);
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.sub-count {
  font-size: 11px;
  color: var(--txt3);
  font-weight: 400;
}

.tank-info-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px;
}

.aux-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.aux-card {
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 14px;
}
.aux-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--txt);
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.aux-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  font-size: 11px;
  color: var(--txt2);
}

/* Chart */
.chart-box {
  width: 100%;
  height: 280px;
}

/* Alarms */
.alarm-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 240px;
  overflow-y: auto;
}
.alarm-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: 6px;
  background: var(--bg);
  font-size: 12px;
}
.alarm-row.emergency {
  border-left: 3px solid var(--red);
  background: rgba(239, 68, 68, 0.05);
}
.alarm-row.critical {
  border-left: 3px solid var(--amber, #f97316);
  background: rgba(249, 115, 22, 0.04);
}
.alarm-row.warning {
  border-left: 3px solid #eab308;
}
.alarm-ts {
  color: var(--txt3);
  font-size: 11px;
  white-space: nowrap;
}
.alarm-msg {
  color: var(--txt);
  flex: 1;
}

.val-cyan {
  color: var(--cyan) !important;
}
.val-green {
  color: var(--green) !important;
}
.val-amber {
  color: var(--amber) !important;
}
.val-good {
  color: var(--green) !important;
}
</style>
