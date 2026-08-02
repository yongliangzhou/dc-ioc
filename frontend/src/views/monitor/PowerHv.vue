<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('设施监控') }} {{ tl('·') }} {{ tl('nav.powerMonitor') }} {{ tl('·') }} {{ tl('nav.hv') }}</h1>
      <span class="sub">{{ tl('10KV 中压配电') }} {{ tl('·') }} {{ tl('分布式采集控制系统') }} {{ tl('·') }} {{ tl('实时电参量 / 开关状态 / 变压器温湿度与遥信') }}</span>
    </div>

    <!-- ======== 顶部 KPI: 系统总体 ======== -->
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="hv-total" :label="tl('设备总数')" :value="s.total" unit="台" quality="good" :online="true" />
      <MetricCard metric-name="hv-online" :label="tl('在线率')" :value="onlinePercent" unit="%" quality="good" :online="true" />
      <MetricCard metric-name="hv-load" :label="tl('平均负载率')" :value="s.avgLoadPercent ?? 0" unit="%" :quality="(s.avgLoadPercent ?? 0) > 85 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="hv-voltage" :label="tl('平均电压')" :value="avgVoltageKv" unit="kV" quality="good" :online="true" />
    </div>
    <div class="grid cols-4" v-if="s">
      <MetricCard metric-name="hv-power" :label="tl('进线总有功')" :value="incomerPower" unit="MW" quality="good" :online="true" />
      <MetricCard metric-name="hv-bustie-i" :label="tl('母联电流')" :value="s.busTie?.i ?? 0" unit="A" :quality="busTieClosed ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="hv-thd" :label="tl('电压谐波 THD-U')" :value="s.quality?.thdU ?? 0" unit="%" :quality="(s.quality?.thdU ?? 0) > 3 ? 'uncertain' : 'good'" :online="true" />
      <MetricCard metric-name="hv-unbal" :label="tl('三相不平衡度')" :value="s.quality?.unbalance ?? 0" unit="%" :quality="(s.quality?.unbalance ?? 0) > 2 ? 'uncertain' : 'good'" :online="true" />
    </div>

    <!-- 加载 / 错误态 -->
    <template v-if="!s">
      <div class="card" v-if="!error">
        <div class="flex center" style="padding:40px"><span class="muted">{{ tl('加载中...') }}</span></div>
      </div>
      <div class="card" v-if="error">
        <div class="flex center" style="padding:40px"><span class="muted" style="color:var(--red)">{{ tl('加载失败') }}: {{ error }}</span></div>
      </div>
    </template>

    <template v-else>
      <!-- ======== 分布式采集控制系统架构 ======== -->
      <div class="card">
        <div class="card-head">
          <span class="ct">{{ tl('分布式采集控制系统') }}</span>
          <span class="pill g">{{ s.scheme || tl('两路市电 + 母联备自投') }}</span>
        </div>
        <p class="arch-desc muted">{{ tl('采用分布式采集控制系统，对 10KV 进线/出线的三相电压、三相电流、有功/无功功率、功率因数、电度等电参量进行实时采集；同步采集断路器/母联开关的合分状态；并将 10KV/0.4KV 配电变压器的绕组/油温/环境温湿度及轻瓦斯、重瓦斯、超温、压力释放等遥测遥信量，经统一协议接入运维监控平台，在保障向系统提供持续稳定电力供应的条件下，保障设备的安全高效运行。') }}</p>
        <div class="chips">
          <span class="chip" v-for="c in collectTargets" :key="c">{{ c }}</span>
        </div>
      </div>

      <!-- ======== 10KV 进线监测 (三相电参量 + 开关状态) ======== -->
      <div class="card scroll-x">
        <div class="card-head">
          <span class="ct">{{ tl('10KV 进线监测') }} ({{ tl('三相电参量') }})</span>
          <span class="pill" :class="incomerAllClosed ? 'g' : 'a'">{{ s.incomers.length }} {{ tl('路') }} · {{ tl('开关合闸') }} {{ incomerClosedCount }}/{{ s.incomers.length }}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>{{ tl('进线') }}</th><th>{{ tl('电源') }}</th><th>{{ tl('开关状态') }}</th>
              <th>Ua (kV)</th><th>Ub (kV)</th><th>Uc (kV)</th>
              <th>Ia (A)</th><th>Ib (A)</th><th>Ic (A)</th>
              <th>P (MW)</th><th>Q (MVar)</th><th>{{ tl('功率因数') }}</th><th>{{ tl('频率') }} (Hz)</th><th>{{ tl('电度') }} (kWh)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in s.incomers" :key="d.id">
              <td class="d-name">{{ d.id }}</td>
              <td class="muted">{{ d.src }}</td>
              <td><span class="tag" :class="breakerCls(d.breaker)">{{ d.breaker }}</span></td>
              <td class="mono">{{ fmt(d.ua) }}</td><td class="mono">{{ fmt(d.ub) }}</td><td class="mono">{{ fmt(d.uc) }}</td>
              <td class="mono">{{ fmt(d.ia, 0) }}</td><td class="mono">{{ fmt(d.ib, 0) }}</td><td class="mono">{{ fmt(d.ic, 0) }}</td>
              <td class="mono">{{ fmt(d.p) }}</td><td class="mono">{{ fmt(d.q) }}</td>
              <td class="mono" :class="pfCls(d.pf)">{{ fmt(d.pf) }}</td>
              <td class="mono">{{ fmt(d.freq) }}</td>
              <td class="mono">{{ fmtEnergy(d.energy) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ======== 10KV 出线/馈线监测 ======== -->
      <div class="card scroll-x">
        <div class="card-head">
          <span class="ct">{{ tl('10KV 出线/馈线监测') }} ({{ tl('三相电参量 + 开关状态') }})</span>
          <span class="pill" :class="feederAllClosed ? 'g' : 'a'">{{ s.feeders.length }} {{ tl('路') }} · {{ tl('合闸') }} {{ feederClosedCount }}/{{ s.feeders.length }}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>{{ tl('馈线') }}</th><th>{{ tl('供电负荷') }}</th><th>{{ tl('开关状态') }}</th>
              <th>Ua (kV)</th><th>Ub (kV)</th><th>Uc (kV)</th>
              <th>Ia (A)</th><th>Ib (A)</th><th>Ic (A)</th>
              <th>P (MW)</th><th>{{ tl('功率因数') }}</th><th>{{ tl('电度') }} (kWh)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in s.feeders" :key="d.id">
              <td class="d-name">{{ d.id }}</td>
              <td class="muted">{{ d.load }}</td>
              <td><span class="tag" :class="breakerCls(d.breaker)">{{ d.breaker }}</span></td>
              <td class="mono">{{ fmt(d.ua) }}</td><td class="mono">{{ fmt(d.ub) }}</td><td class="mono">{{ fmt(d.uc) }}</td>
              <td class="mono">{{ fmt(d.ia, 0) }}</td><td class="mono">{{ fmt(d.ib, 0) }}</td><td class="mono">{{ fmt(d.ic, 0) }}</td>
              <td class="mono">{{ fmt(d.p) }}</td>
              <td class="mono" :class="pfCls(d.pf)">{{ fmt(d.pf) }}</td>
              <td class="mono">{{ fmtEnergy(d.energy) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ======== 母联 / 备自投 / 母线段 ======== -->
      <div class="grid cols-3" v-if="s.busTie">
        <!-- 母联 -->
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('母联开关') }}</span>
            <span class="tag" :class="breakerCls(s.busTie.state)">{{ s.busTie.state }}</span>
          </div>
          <div class="kv-grid">
            <div class="kv"><span class="k">{{ tl('备自投') }}</span><span class="v">{{ s.busTie.autoSwitch }}</span></div>
            <div class="kv"><span class="k">{{ tl('模式') }}</span><span class="v">{{ s.busTie.mode }}</span></div>
            <div class="kv"><span class="k">{{ tl('额定电流') }}</span><span class="v mono">{{ s.busTie.iRated }} A</span></div>
            <div class="kv"><span class="k">{{ tl('当前电流') }}</span><span class="v mono">{{ s.busTie.i }} A</span></div>
          </div>
        </div>
        <!-- ATS 备自投 -->
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('备自投 ATS') }}</span>
            <span class="pill g">{{ tl('逻辑已投入') }}</span>
          </div>
          <p class="arch-desc muted">{{ s.ats?.logic }}</p>
          <div class="kv-grid">
            <div class="kv"><span class="k">{{ tl('切换时间') }}</span><span class="v mono">{{ s.ats?.switchTime }}</span></div>
            <div class="kv"><span class="k">{{ tl('上次试验') }}</span><span class="v">{{ s.ats?.lastTest }}</span></div>
          </div>
        </div>
        <!-- 母线段 -->
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('母线段电压') }}</span>
            <span class="pill g">{{ s.busSections?.length || 0 }} {{ tl('段带电') }}</span>
          </div>
          <div class="bus-grid">
            <div class="bus-item" v-for="b in s.busSections" :key="b.id">
              <span class="bus-label">{{ b.id }}</span>
              <span class="bus-val" :class="busStateCls(b.state)">{{ fmt(b.u) }} <small>kV</small></span>
              <span class="bus-sub mono">{{ fmt(b.freq) }} Hz · {{ b.state }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ======== 配电变压器 (温湿度 / 遥测 / 遥信) ======== -->
      <div class="card" v-if="s.transformers?.length">
        <div class="card-head">
          <span class="ct">{{ tl('10KV/0.4KV 配电变压器') }} ({{ tl('温湿度·遥测·遥信') }})</span>
          <span class="pill" :class="txAllRunning ? 'g' : 'a'">{{ s.transformers.length }} {{ tl('台') }} · {{ txRunningCount }} {{ tl('运行') }}</span>
        </div>
        <div class="tx-grid">
          <div class="tx-block" v-for="t in s.transformers" :key="t.id">
            <div class="tx-head">
              <span class="d-status" :class="txStateCls(t.state)">●</span>
              <span class="d-name">{{ t.id }}</span>
              <span class="d-code muted">{{ t.feeder }}</span>
              <span class="tag" :class="txStateTagCls(t.state)">{{ t.state }}</span>
            </div>
            <!-- 温湿度 (遥测) -->
            <div class="tx-mini-grid">
              <div class="tx-mini"><span class="k">{{ tl('负载率') }}</span><span class="v mono" :class="loadCls(t.load)">{{ t.load }}%</span></div>
              <div class="tx-mini"><span class="k">{{ tl('绕组温度') }}</span><span class="v mono" :class="tempCls(t.windingT, 85, 95)">{{ t.windingT }}°C</span></div>
              <div class="tx-mini"><span class="k">{{ tl('油温') }}</span><span class="v mono" :class="tempCls(t.oilT, 75, 85)">{{ t.oilT }}°C</span></div>
              <div class="tx-mini"><span class="k">{{ tl('环境温度') }}</span><span class="v mono">{{ t.ambT }}°C</span></div>
              <div class="tx-mini"><span class="k">{{ tl('湿度') }}</span><span class="v mono" :class="humCls(t.humidity)">{{ t.humidity }}%RH</span></div>
              <div class="tx-mini"><span class="k">{{ tl('调压档位') }}</span><span class="v mono">{{ t.tap }} {{ tl('档') }}</span></div>
              <div class="tx-mini"><span class="k">{{ tl('高压侧') }}</span><span class="v mono">{{ fmt(t.uHigh) }} kV / {{ fmt(t.iHigh, 0) }} A</span></div>
              <div class="tx-mini"><span class="k">{{ tl('低压侧') }}</span><span class="v mono">{{ fmt(t.uLow, 3) }} kV / {{ fmt(t.iLow, 0) }} A</span></div>
              <div class="tx-mini"><span class="k">{{ tl('冷却风机') }}</span><span class="v">{{ t.fan }}</span></div>
            </div>
            <!-- 遥信量 -->
            <div class="sig-list">
              <span class="sig" v-for="sg in t.signals" :key="sg.name">
                <span class="sig-k">{{ sg.name }}</span>
                <span class="sig-v" :class="sigLevelCls(sg.level)">{{ sg.value }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- ======== 直流屏 (操作电源) ======== -->
      <div class="grid cols-3" v-if="s.dcPanel">
        <div class="card col-span-2">
          <div class="card-head">
            <span class="ct">{{ tl('直流屏') }} / {{ tl('操作电源') }} ({{ s.dcPanel.id }})</span>
            <span class="pill" :class="s.dcPanel.state === '浮充' ? 'g' : 'a'">{{ s.dcPanel.state }}</span>
          </div>
          <div class="tx-mini-grid">
            <div class="tx-mini"><span class="k">{{ tl('DC 母线') }}</span><span class="v mono" :class="dcBusCls(s.dcPanel.dcBus, s.dcPanel.dcBusTarget)">{{ s.dcPanel.dcBus }} V</span></div>
            <div class="tx-mini"><span class="k">{{ tl('目标电压') }}</span><span class="v mono">{{ s.dcPanel.dcBusTarget }} V</span></div>
            <div class="tx-mini"><span class="k">{{ tl('蓄电池组') }}</span><span class="v mono">{{ s.dcPanel.batteryBank }} V</span></div>
            <div class="tx-mini"><span class="k">{{ tl('充电电流') }}</span><span class="v mono">{{ s.dcPanel.chargeI }} A</span></div>
            <div class="tx-mini"><span class="k">{{ tl('放电电流') }}</span><span class="v mono">{{ s.dcPanel.dischargeI }} A</span></div>
            <div class="tx-mini"><span class="k">{{ tl('绝缘电阻') }}</span><span class="v mono" :class="s.dcPanel.insulationR < 10 ? 'r' : 'g'">{{ s.dcPanel.insulationR }} MΩ</span></div>
            <div class="tx-mini"><span class="k">{{ tl('纹波电压') }}</span><span class="v mono">{{ s.dcPanel.ripple }} V</span></div>
          </div>
          <div class="sig-list" style="margin-top:10px">
            <span class="sig" v-for="a in s.dcPanel.alarms" :key="a.name">
              <span class="sig-k">{{ a.name }}</span>
              <span class="sig-v" :class="sigLevelCls(a.level)">{{ a.value }}</span>
            </span>
          </div>
        </div>
        <!-- 开关柜环境监测 -->
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('开关柜环境监测') }}</span>
            <span class="pill g">{{ tl('局放 TEV/超声') }}</span>
          </div>
          <table class="mini-tbl">
            <thead><tr><th>{{ tl('柜列') }}</th><th>°C</th><th>%RH</th><th>TEV</th><th>超声</th><th>{{ tl('状态') }}</th></tr></thead>
            <tbody>
              <tr v-for="r in s.switchgearEnv?.rows" :key="r.id">
                <td class="muted">{{ r.id }}</td>
                <td class="mono">{{ fmt(r.t, 1) }}</td>
                <td class="mono">{{ r.h }}</td>
                <td class="mono" :class="tevCls(r.tev)">{{ fmt(r.tev, 1) }}</td>
                <td class="mono">{{ fmt(r.us, 1) }}</td>
                <td><span class="tag" :class="r.state === '正常' ? 'g' : 'a'">{{ r.state }}</span></td>
              </tr>
            </tbody>
          </table>
          <p class="arch-desc muted" style="margin-top:8px">{{ s.switchgearEnv?.note }}</p>
        </div>
      </div>

      <!-- ======== 微机保护装置 ======== -->
      <div class="card scroll-x" v-if="s.protectionRelays?.length">
        <div class="card-head">
          <span class="ct">{{ tl('微机保护装置') }} (REF615/611)</span>
          <span class="pill" :class="relayAllComm ? 'g' : 'a'">{{ s.protectionRelays.length }} {{ tl('套') }} · {{ tl('通讯正常') }} {{ relayCommCount }}/{{ s.protectionRelays.length }}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>{{ tl('保护装置') }}</th><th>{{ tl('被保护设备') }}</th><th>{{ tl('状态') }}</th>
              <th>{{ tl('过流') }}</th><th>{{ tl('接地') }}</th><th>{{ tl('差动') }}</th>
              <th>{{ tl('欠压') }}</th><th>{{ tl('过压') }}</th><th>{{ tl('频率') }}</th>
              <th>{{ tl('通讯') }}</th><th>{{ tl('最近动作') }}</th><th>{{ tl('动作次数') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in s.protectionRelays" :key="r.id">
              <td class="d-name">{{ r.id }}</td>
              <td class="muted">{{ r.device }}</td>
              <td><span class="tag" :class="r.state === '运行' ? 'g' : 'b'">{{ r.state }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.overcurrent)">{{ r.overcurrent }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.earthFault)">{{ r.earthFault }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.diff)">{{ r.diff }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.underVoltage)">{{ r.underVoltage }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.overVoltage)">{{ r.overVoltage }}</span></td>
              <td><span class="tag" :class="relayFuncCls(r.freq)">{{ r.freq }}</span></td>
              <td><span class="tag" :class="r.comm === '正常' ? 'g' : 'r'">{{ r.comm }}</span></td>
              <td class="muted mono" :class="r.tripCount > 0 ? 'a' : ''" style="font-size:11px">{{ r.lastTrip }}</td>
              <td class="mono" :class="r.tripCount > 0 ? 'a' : ''">{{ r.tripCount }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ======== 消弧线圈 / 接地变 + 关口计量 + 电能质量 ======== -->
      <div class="grid cols-3" v-if="s.arcSuppression">
        <!-- 消弧线圈 -->
        <div class="card">
          <div class="card-head">
            <span class="ct">{{ tl('消弧线圈 / 接地变') }}</span>
            <span class="pill g">{{ tl('中性点接地') }}</span>
          </div>
          <p class="arch-desc muted">{{ s.arcSuppression.mode }}</p>
          <div class="kv-grid">
            <div class="kv"><span class="k">{{ tl('补偿电流') }}</span><span class="v mono">{{ s.arcSuppression.coilCurrent }} A</span></div>
            <div class="kv"><span class="k">{{ tl('档位') }}</span><span class="v mono">{{ s.arcSuppression.coilPosition }}</span></div>
            <div class="kv"><span class="k">{{ tl('中性点电压') }}</span><span class="v mono">{{ s.arcSuppression.neutralV }} V</span></div>
            <div class="kv"><span class="k">{{ tl('电容电流') }}</span><span class="v mono">{{ s.arcSuppression.earthCapacitance }} A</span></div>
            <div class="kv"><span class="k">{{ tl('残余电流') }}</span><span class="v mono">{{ s.arcSuppression.residualCurrent }} A</span></div>
            <div class="kv"><span class="k">{{ tl('状态') }}</span><span class="v">{{ s.arcSuppression.state }}</span></div>
          </div>
          <div class="kv" style="border-top:1px solid var(--border); margin-top:6px; padding-top:8px">
            <span class="k">{{ tl('接地变') }} {{ s.arcSuppression.groundingTx?.id }}</span>
            <span class="v mono">{{ s.arcSuppression.groundingTx?.state }} · {{ s.arcSuppression.groundingTx?.t }}°C / {{ s.arcSuppression.groundingTx?.i }} A</span>
          </div>
        </div>

        <!-- 关口计量 -->
        <div class="card" v-if="s.metering">
          <div class="card-head">
            <span class="ct">{{ tl('关口计量') }} (kWh)</span>
            <span class="pill g">{{ tl('峰/平/谷') }}</span>
          </div>
          <table class="mini-tbl">
            <thead><tr><th>{{ tl('进线') }}</th><th>{{ tl('总电度') }}</th><th>{{ tl('峰') }}</th><th>{{ tl('平') }}</th><th>{{ tl('谷') }}</th><th>{{ tl('需量') }}</th></tr></thead>
            <tbody>
              <tr>
                <td class="d-name">1#</td>
                <td class="mono">{{ fmtEnergy(s.metering.incomer1.energyTotal) }}</td>
                <td class="mono">{{ fmtEnergy(s.metering.incomer1.energyPeak) }}</td>
                <td class="mono">{{ fmtEnergy(s.metering.incomer1.energyFlat) }}</td>
                <td class="mono">{{ fmtEnergy(s.metering.incomer1.energyValley) }}</td>
                <td class="mono">{{ fmt(s.metering.incomer1.demand) }} MW</td>
              </tr>
              <tr>
                <td class="d-name">2#</td>
                <td class="mono">{{ fmtEnergy(s.metering.incomer2.energyTotal) }}</td>
                <td class="mono">{{ fmtEnergy(s.metering.incomer2.energyPeak) }}</td>
                <td class="mono">{{ fmtEnergy(s.metering.incomer2.energyFlat) }}</td>
                <td class="mono">{{ fmtEnergy(s.metering.incomer2.energyValley) }}</td>
                <td class="mono">{{ fmt(s.metering.incomer2.demand) }} MW</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 电能质量 -->
        <div class="card" v-if="s.quality">
          <div class="card-head">
            <span class="ct">{{ tl('电能质量') }}</span>
            <span class="pill g">THD / {{ tl('不平衡度') }}</span>
          </div>
          <div class="tx-mini-grid">
            <div class="tx-mini"><span class="k">THD-U</span><span class="v mono" :class="(s.quality.thdU) > 3 ? 'a' : 'g'">{{ fmt(s.quality.thdU) }}%</span></div>
            <div class="tx-mini"><span class="k">THD-I</span><span class="v mono" :class="(s.quality.thdI) > 5 ? 'a' : 'g'">{{ fmt(s.quality.thdI) }}%</span></div>
            <div class="tx-mini"><span class="k">{{ tl('三相不平衡') }}</span><span class="v mono" :class="(s.quality.unbalance) > 2 ? 'a' : 'g'">{{ fmt(s.quality.unbalance) }}%</span></div>
          </div>
          <table class="mini-tbl" style="margin-top:8px" v-if="s.quality.incomer1 || s.quality.incomer2">
            <thead><tr><th>{{ tl('进线') }}</th><th>THD-U</th><th>THD-I</th><th>{{ tl('不平衡') }}</th><th>{{ tl('闪变') }}</th></tr></thead>
            <tbody>
              <tr v-if="s.quality.incomer1"><td class="d-name">1#</td><td class="mono">{{ fmt(s.quality.incomer1.thdU) }}%</td><td class="mono">{{ fmt(s.quality.incomer1.thdI) }}%</td><td class="mono">{{ fmt(s.quality.incomer1.unbalance) }}%</td><td class="mono">{{ fmt(s.quality.incomer1.flicker) }}</td></tr>
              <tr v-if="s.quality.incomer2"><td class="d-name">2#</td><td class="mono">{{ fmt(s.quality.incomer2.thdU) }}%</td><td class="mono">{{ fmt(s.quality.incomer2.thdI) }}%</td><td class="mono">{{ fmt(s.quality.incomer2.unbalance) }}%</td><td class="mono">{{ fmt(s.quality.incomer2.flicker) }}</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ======== 知识库: 阈值 ======== -->
      <div class="card" v-if="s.knowledge?.thresholds?.length">
        <div class="section-title"><span class="bar"></span>{{ tl('设计 / 告警阈值') }}</div>
        <div class="kv-grid">
          <div class="kv" v-for="t in s.knowledge.thresholds" :key="t.k">
            <span class="k">{{ t.k }}</span>
            <span class="v">{{ t.v }}</span>
            <span v-if="t.note" class="note muted">{{ t.note }}</span>
          </div>
        </div>
      </div>

      <!-- ======== 知识库: 架构 ======== -->
      <div class="card" v-if="s.knowledge?.arch">
        <div class="section-title"><span class="bar"></span>{{ tl('系统架构与组成') }}</div>
        <p class="arch-desc muted">{{ s.knowledge.arch.design }}</p>
        <div class="chips">
          <span class="chip" v-for="c in s.knowledge.arch.components" :key="c">{{ c }}</span>
        </div>
        <p class="redundancy muted" v-if="s.knowledge.arch.redundancy">{{ tl('冗余配置') }}：{{ s.knowledge.arch.redundancy }}</p>
      </div>

      <!-- ======== 知识库: 切换逻辑 ======== -->
      <div class="card" v-for="g in (s.knowledge?.logic || [])" :key="g.title">
        <div class="section-title"><span class="bar"></span>{{ g.title }}</div>
        <div class="logic-list">
          <div class="logic-step" v-for="st in g.steps" :key="st.step">
            <span class="step-no">{{ st.step }}</span>
            <span class="step-text">{{ st.text }}</span>
            <span v-if="st.ok !== undefined" class="ok" :class="st.ok ? 'ok-y' : 'ok-n'">{{ st.ok ? tl('满足') : tl('未满足') }}</span>
          </div>
        </div>
      </div>

      <!-- ======== 知识库: 故障锁定 ======== -->
      <div class="card scroll-x" v-if="s.knowledge?.faults?.length">
        <div class="section-title"><span class="bar"></span>{{ tl('故障锁定知识库') }}</div>
        <table>
          <thead><tr><th style="width:50px">{{ tl('序号') }}</th><th>{{ tl('故障') }}</th><th>{{ tl('锁定 / 影响') }}</th><th>{{ tl('处置动作') }}</th><th style="width:80px">{{ tl('复位') }}</th></tr></thead>
          <tbody>
            <tr v-for="f in s.knowledge.faults" :key="f.no">
              <td class="mono">{{ f.no }}</td>
              <td class="d-name">{{ f.fault }}</td>
              <td class="muted">{{ f.lock }}</td>
              <td class="muted">{{ f.action }}</td>
              <td><span class="tag" :class="f.manualReset ? 'a' : 'g'">{{ f.manualReset ? tl('人工复位') : tl('自动') }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="knote muted" v-if="s.knowledge?.note">{{ s.knowledge.note }}</p>

      <!-- 底部统计 -->
      <div class="footer-note muted">
        {{ tl('10KV 中压配电') }} · {{ tl('分布式采集控制系统') }} | {{ tl('设备总数') }} {{ s.total }} {{ tl('台') }} · {{ s.online }} {{ tl('台在线') }} · {{ tl('进线') }} {{ incomerPower }} MW · {{ tl('母联') }} {{ s.busTie?.state }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import { getPowerHvDetailed, type HvSummary } from '@/api/power'
const { t: tl } = useI18n()

const s = ref<HvSummary | null>(null)
const error = ref('')

const onlinePercent = computed(() => {
  if (!s.value || !s.value.total) return 0
  return Number(((s.value.online / s.value.total) * 100).toFixed(1))
})

// 平均电压: 后端 avgVoltage 已由 kV→V 换算, 这里还原为 kV 展示
const avgVoltageKv = computed(() => {
  const v = s.value?.avgVoltage
  return v != null ? Number((v / 1000).toFixed(2)) : 0
})

// 进线总有功 (MW)
const incomerPower = computed(() => {
  const list = s.value?.incomers ?? []
  if (!list.length) return 0
  return Number(list.reduce((sum, d) => sum + (d.p || 0), 0).toFixed(2))
})

// 开关合闸统计
const incomerClosedCount = computed(() => (s.value?.incomers ?? []).filter((d) => isClosed(d.breaker)).length)
const incomerAllClosed = computed(() => {
  const list = s.value?.incomers ?? []
  return list.length > 0 && incomerClosedCount.value === list.length
})
const feederClosedCount = computed(() => (s.value?.feeders ?? []).filter((d) => isClosed(d.breaker)).length)
const feederAllClosed = computed(() => {
  const list = s.value?.feeders ?? []
  return list.length > 0 && feederClosedCount.value === list.length
})

// 母联
const busTieClosed = computed(() => isClosed(s.value?.busTie?.state))

// 变压器运行统计
const txRunningCount = computed(() => (s.value?.transformers ?? []).filter((t) => t.state === '运行').length)
const txAllRunning = computed(() => {
  const list = s.value?.transformers ?? []
  return list.length > 0 && txRunningCount.value === list.length
})

// 保护装置通讯
const relayCommCount = computed(() => (s.value?.protectionRelays ?? []).filter((r) => r.comm === '正常').length)
const relayAllComm = computed(() => {
  const list = s.value?.protectionRelays ?? []
  return list.length > 0 && relayCommCount.value === list.length
})

// 分布式采集对象
const collectTargets = computed(() => [
  '10KV 进线电参量', '10KV 出线/馈线电参量', '断路器合分状态', '母联备自投',
  '变压器温湿度', '变压器遥测/遥信', '直流屏操作电源', '微机保护装置',
  '开关柜局放 TEV/超声', '消弧线圈/接地变', '关口计量', '电能质量 THD',
])

// ---- 工具函数 ----
function isClosed(v?: string): boolean {
  const t = String(v ?? '').trim()
  return t.includes('合闸') || t.includes('合') && !t.includes('分')
}

function fmt(v: number | undefined | null, dp = 2): string {
  if (v == null || !Number.isFinite(v)) return '-'
  return Number(v).toFixed(dp)
}

function fmtEnergy(v: number | undefined | null): string {
  if (v == null || !Number.isFinite(v)) return '-'
  return Math.round(v).toLocaleString()
}

function breakerCls(v: string): string {
  if (isClosed(v)) return 'g'
  if (v.includes('分闸') || v.includes('分')) return 'b'
  return 'a'
}

function pfCls(pf: number): string {
  if (pf >= 0.95) return 'g-text'
  if (pf >= 0.9) return 'a-text'
  return 'r-text'
}

function txStateCls(st: string): string {
  if (st === '运行') return 'g'
  if (st.includes('故障') || st.includes('停机')) return 'r'
  if (st.includes('预警') || st.includes('异常')) return 'a'
  return 'm'
}
function txStateTagCls(st: string): string {
  if (st === '运行') return 'g'
  if (st.includes('故障') || st.includes('停机')) return 'r'
  if (st.includes('预警') || st.includes('异常')) return 'a'
  return 'b'
}

function tempCls(t: number, warn: number, alarm: number): string {
  if (t >= alarm) return 'r-text'
  if (t >= warn) return 'a-text'
  return 'g-text'
}

function loadCls(load: number): string {
  if (load >= 90) return 'r-text'
  if (load >= 80) return 'a-text'
  return 'g-text'
}

function humCls(h: number): string {
  if (h > 70 || h < 20) return 'a-text'
  return 'g-text'
}

function dcBusCls(bus: number, target: number): string {
  if (target && Math.abs(bus - target) > 5) return 'a-text'
  return 'g-text'
}

function busStateCls(state: string): string {
  if (state === '带电' || state === '运行') return 'g-text'
  if (state.includes('失电')) return 'r-text'
  return 'a-text'
}

function tevCls(tev: number): string {
  if (tev >= 20) return 'r-text'
  if (tev >= 10) return 'a-text'
  return 'g-text'
}

function relayFuncCls(v: string): string {
  return v === '投入' ? 'g' : 'b'
}

function sigLevelCls(level: string): string {
  if (level === 'g') return 'sig-g'
  if (level === 'a') return 'sig-a'
  if (level === 'r') return 'sig-r'
  return 'sig-b'
}

async function load() {
  error.value = ''
  try {
    s.value = await getPowerHvDetailed()
  } catch (e: any) {
    error.value = e?.message || String(e)
  }
}
onMounted(load)
</script>

<style scoped>
/* ----------  card / head / pill ---------- */
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 8px; }
.ct { font-weight: 600; font-size: 14px; }
.pill { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--bg2); color: var(--txt2); }
.pill.g { background: rgba(82,196,26,0.12); color: var(--green); }
.pill.a { background: rgba(250,173,20,0.12); color: var(--amber); }

.arch-desc { font-size: 12px; line-height: 1.7; margin: 0 0 10px; }

/* ----------  chips ---------- */
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 11px; padding: 2px 9px; border-radius: 12px; background: rgba(34,227,255,0.08); color: var(--cyan); border: 1px solid rgba(34,227,255,0.25); }

/* ----------  table ---------- */
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; color: var(--txt3); font-weight: 600; font-size: 10.5px; letter-spacing: .5px; padding: 7px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
td { padding: 6px 8px; border-bottom: 1px solid var(--td-line); color: var(--txt); white-space: nowrap; }
tbody tr:hover { background: var(--row-hover); }
.mini-tbl th, .mini-tbl td { font-size: 11px; padding: 5px 6px; }

.d-name { font-weight: 500; color: var(--txt); }
.mono { font-variant-numeric: tabular-nums; font-family: "SF Mono", Consolas, monospace; }

/* 文本色 (用于 td 数值着色, 不影响布局) */
.g-text { color: var(--green); }
.a-text { color: var(--amber); }
.r-text { color: var(--red); }

/* ----------  tag (复用全局, 补 b) ---------- */
.tag { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 20px; border: 1px solid var(--line); white-space: nowrap; }
.tag.g { color: var(--green); border-color: rgba(43,212,122,.4); background: rgba(43,212,122,.08); }
.tag.a { color: var(--amber); border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }
.tag.r { color: var(--red); border-color: rgba(255,77,94,.4); background: rgba(255,77,94,.09); }
.tag.b { color: var(--blue); border-color: rgba(59,130,246,.4); background: rgba(59,130,246,.08); }

/* ----------  kv-grid (键值网格) ---------- */
.kv-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px 18px; }
.kv { display: flex; flex-direction: column; gap: 2px; padding: 6px 0; border-bottom: 1px dashed var(--td-line); }
.k { font-size: 11px; color: var(--txt3); }
.v { font-size: 13px; color: var(--txt); font-weight: 600; }
.note { font-size: 10px; }

/* ----------  母线段 ---------- */
.bus-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.bus-item { text-align: center; padding: 10px 6px; border-radius: 6px; background: var(--bg2); }
.bus-label { display: block; font-size: 11px; color: var(--muted); margin-bottom: 4px; }
.bus-val { display: block; font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }
.bus-val small { font-size: 11px; color: var(--txt3); font-weight: 500; }
.bus-sub { display: block; font-size: 10px; color: var(--muted); margin-top: 3px; }

/* ----------  变压器 ---------- */
.tx-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.tx-block { border: 1px solid var(--td-line); border-radius: 8px; padding: 10px 12px; background: var(--bg2); }
.tx-head { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.d-status { font-size: 8px; }
.d-status.g { color: var(--green); }
.d-status.r { color: var(--red); }
.d-status.a { color: var(--amber); }
.d-status.m { color: var(--muted); }
.d-code { font-size: 11px; }
.tx-head .tag { margin-left: auto; }
.tx-mini-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px 12px; }
.tx-mini { display: flex; flex-direction: column; gap: 1px; padding: 4px 0; }
.tx-mini .k { font-size: 10px; color: var(--txt3); }
.tx-mini .v { font-size: 12px; font-weight: 600; }

/* 遥信量 */
.sig-list { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--td-line); }
.sig { display: inline-flex; align-items: center; gap: 4px; font-size: 10.5px; padding: 2px 7px; border-radius: 4px; background: var(--panel); border: 1px solid var(--td-line); }
.sig-k { color: var(--txt3); }
.sig-v { font-weight: 600; }
.sig-g { color: var(--green); }
.sig-a { color: var(--amber); }
.sig-r { color: var(--red); }
.sig-b { color: var(--blue); }

/* ----------  知识库 ---------- */
.section-title { font-size: 13px; font-weight: 700; color: var(--cyan); margin: 0 0 10px; display: flex; align-items: center; gap: 8px; }
.section-title::before { content: ""; width: 4px; height: 14px; border-radius: 2px; background: var(--cyan); }
.section-title .bar { display: none; }
.logic-list { display: flex; flex-direction: column; gap: 8px; }
.logic-step { display: flex; align-items: flex-start; gap: 10px; font-size: 12px; color: var(--txt); line-height: 1.5; }
.step-no { flex: 0 0 auto; width: 20px; height: 20px; border-radius: 50%; background: var(--cyan); color: #061021; font-size: 11px; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.step-text { flex: 1; }
.ok { flex: 0 0 auto; font-size: 10px; padding: 1px 8px; border-radius: 999px; }
.ok-y { background: rgba(43,212,122,.15); color: var(--green); }
.ok-n { background: rgba(255,77,94,.15); color: var(--red); }
.redundancy { font-size: 12px; margin: 10px 0 0; }
.knote { font-size: 12px; font-style: italic; text-align: center; margin-top: 12px; }

/* ----------  layout ---------- */
.grid { display: grid; gap: 12px; }
.cols-3 { grid-template-columns: repeat(3, 1fr); }
.col-span-2 { grid-column: span 2; }
@media (max-width: 1180px) {
  .cols-3 { grid-template-columns: 1fr; }
  .col-span-2 { grid-column: span 1; }
  .tx-grid { grid-template-columns: 1fr; }
}

/* ----------  misc ---------- */
.flex { display: flex; }
.center { align-items: center; }
.muted { color: var(--txt2); }
.scroll-x { overflow-x: auto; }
.empty-tip { text-align: center; padding: 20px; color: var(--muted); font-size: 12px; }
.footer-note { text-align: center; margin-top: 16px; font-size: 11px; }
</style>
