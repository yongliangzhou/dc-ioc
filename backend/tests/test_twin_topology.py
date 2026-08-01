"""build-graph-apis: 数字孪生 / 链路拓扑 数据底座 (twin/topology) 单元测试 (无需数据库)。

覆盖:
  - /twin/topology 数据底座 (合并孪生层级图 + 链路拓扑图 + 汇总)
  - 推演接口: simulate / scenario_library / ark_closed_loop
无真实数据时自动回退生成器, 故无需 DB 即可验证 JSON 契约与基本不变量。
"""

from app.services import twin_topology as tp


def test_topology_data_foundation():
    d = tp.build_topology_data()
    # 顶层契约
    for k in ("generatedAt", "source", "twinGraph", "topology", "summary"):
        assert k in d, f"missing top-level key: {k}"
    # 图数据非空
    assert len(d["twinGraph"]["idcs"]) >= 1, "twinGraph should have >=1 IDC"
    assert len(d["topology"]["nodes"]) >= 1, "topology should have nodes"
    assert len(d["topology"]["edges"]) >= 1, "topology should have edges"
    # 汇总指标类型正确
    s = d["summary"]
    assert isinstance(s["equipmentCount"], int) and s["equipmentCount"] > 0
    assert isinstance(s["roomCount"], int) and s["roomCount"] > 0
    assert isinstance(s["topoNodes"], int) and s["topoNodes"] > 0
    assert isinstance(s["topoEdges"], int) and s["topoEdges"] >= 0
    # topoRedundancy 为 {N+1, 2N, single} 计数字典
    rr = s["topoRedundancy"]
    assert isinstance(rr, dict)
    for _k in ("N+1", "2N", "single"):
        assert _k in rr and isinstance(rr[_k], int) and rr[_k] >= 0
    print(f"[PASS] test_topology_data_foundation "
          f"(rooms={s['roomCount']}, equip={s['equipmentCount']}, "
          f"topo={s['topoNodes']}n/{s['topoEdges']}e)")


def test_simulate_contract():
    res = tp.simulate({"scenario": "市电失电"})
    for k in ("scenario", "baseline", "after", "impact", "affectedEquipmentIds", "affectedRoomIds"):
        assert k in res, f"simulate missing key: {k}"
    assert res["impact"]["equipmentLost"] >= 0
    assert isinstance(res["affectedEquipmentIds"], list)
    assert isinstance(res["affectedRoomIds"], list)
    print(f"[PASS] test_simulate_contract "
          f"(scenario={res['scenario']}, lost={res['impact']['equipmentLost']})")


def test_scenario_library_contract():
    lib = tp.scenario_library()
    assert "scenarios" in lib
    assert len(lib["scenarios"]) >= 1, "should have >=1 scenario"
    for s in lib["scenarios"]:
        for k in ("id", "scenario", "name", "desc", "targetCount",
                  "impactCount", "riskLevel", "runnable"):
            assert k in s, f"scenario missing key: {k}"
        assert s["riskLevel"] in ("low", "medium", "high")
    print(f"[PASS] test_scenario_library_contract "
          f"(scenarios={len(lib['scenarios'])}, total={lib['equipmentTotal']})")


def test_ark_closed_loop_contract():
    ark = tp.ark_closed_loop()
    assert "summary" in ark and "loops" in ark
    sm = ark["summary"]
    for k in ("source", "facilityKw", "itKw", "coolingKw",
              "achievedKw", "achievedKwhYear", "carbonTonYear", "loopCount"):
        assert k in sm, f"ark summary missing key: {k}"
    assert sm["loopCount"] >= 1
    for l in ark["loops"]:
        for k in ("id", "name", "kind", "savedKw", "savingPct",
                  "savedKwhYear", "metrics"):
            assert k in l, f"loop missing key: {k}"
        assert l["kind"] in ("achieved", "potential")
    print(f"[PASS] test_ark_closed_loop_contract "
          f"(source={sm['source']}, achievedKw={sm['achievedKw']}, "
          f"loops={sm['loopCount']})")


if __name__ == "__main__":
    test_topology_data_foundation()
    test_simulate_contract()
    test_scenario_library_contract()
    test_ark_closed_loop_contract()
    print("[ALL_OK] twin/topology data-foundation API contract")
