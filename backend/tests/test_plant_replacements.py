"""绿植更换记录接口测试。"""


def replacement_payload(space_id, **overrides):
    payload = {
        "green_space_id": space_id,
        "plant_name": "红叶石楠",
        "plant_category": "shrub",
        "spec": "冠幅 80-100cm",
        "quantity": 24,
        "unit": "plant",
        "reason": "dead",
        "old_plant_status": "dead",
        "replace_date": "2026-03-16",
        "plant_source": "purchased",
        "supplier": "萧山苗木合作社",
        "unit_price": 88.5,
        "operator": "王海涛",
    }
    payload.update(overrides)
    return payload


def test_create_replacement_computes_amount(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/plant-replacements", replacement_payload(space.id)), 201)
    assert data["replacement_no"].startswith("PR-")
    assert data["quantity"] == 24.0
    assert data["amount"] == 2124.0
    assert data["plant_category_label"] == "灌木"
    assert data["reason_label"] == "枯死更换"
    assert data["unit_label"] == "株"
    assert data["plant_source"] == "purchased"
    assert data["plant_source_label"] == "外购苗"
    assert data["source_incomplete"] is False


def test_missing_source_registration_is_flagged(api, make_space):
    space = make_space()
    # 未登记苗木来源
    data = api.data(api.post(
        "/api/v1/plant-replacements",
        replacement_payload(space.id, plant_source=None, supplier=None, unit_price=None),
    ), 201)
    assert data["plant_source"] is None
    assert data["plant_source_label"] is None
    assert data["source_incomplete"] is True

    # 已选自产苗但漏填单价，同样标记待补录
    incomplete = api.data(api.post(
        "/api/v1/plant-replacements",
        replacement_payload(space.id, plant_source="self_grown",
                            supplier="中心自有苗圃", unit_price=None),
    ), 201)
    assert incomplete["source_incomplete"] is True

    # 补录单价后标记解除
    fixed = api.data(api.put(f"/api/v1/plant-replacements/{incomplete['id']}", {
        "green_space_id": space.id,
        "plant_name": "红叶石楠",
        "plant_category": "shrub",
        "quantity": incomplete["quantity"],
        "unit": "plant",
        "reason": "dead",
        "replace_date": "2026-03-16",
        "plant_source": "self_grown",
        "supplier": "中心自有苗圃",
        "unit_price": 12,
    }))
    assert fixed["source_incomplete"] is False
    assert fixed["amount"] == round(12 * incomplete["quantity"], 2)


def test_amount_is_empty_without_unit_price(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/plant-replacements",
                             replacement_payload(space.id, unit_price=None)), 201)
    assert data["unit_price"] is None
    assert data["amount"] is None


def test_quantity_and_category_are_validated(api, make_space):
    space = make_space()
    response = api.post("/api/v1/plant-replacements",
                        replacement_payload(space.id, quantity=0, plant_category="bonsai"))
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "quantity" in details and "plant_category" in details


def test_record_must_belong_to_same_green_space(api, make_record, make_space):
    record = make_record()
    other_space = make_space(name="无关绿地")
    response = api.post("/api/v1/plant-replacements",
                        replacement_payload(other_space.id, maintenance_record_id=record.id))
    assert response.status_code == 422
    assert "不属于所选绿地" in response.get_json()["data"]["maintenance_record_id"]


def test_update_recomputes_amount(api, make_replacement):
    replacement = make_replacement()
    data = api.data(api.put(f"/api/v1/plant-replacements/{replacement.id}", {
        "green_space_id": replacement.green_space_id,
        "plant_name": replacement.plant_name,
        "plant_category": replacement.plant_category,
        "quantity": 50,
        "unit": "plant",
        "reason": replacement.reason,
        "replace_date": "2026-03-20",
        "unit_price": 10,
    }))
    assert data["quantity"] == 50.0
    assert data["amount"] == 500.0
    assert data["replace_date"] == "2026-03-20"


def test_summary_groups_by_category_and_reason(api, make_replacement):
    make_replacement(quantity=10, unit_price=100, plant_category="tree", reason="dead")
    make_replacement(quantity=20, unit_price=50, plant_category="tree", reason="aging")
    make_replacement(quantity=5, unit_price=20, plant_category="shrub", reason="dead")

    data = api.data(api.get("/api/v1/plant-replacements/summary"))
    assert data["total_count"] == 3
    assert data["total_quantity"] == 35.0
    assert data["total_amount"] == 2100.0

    by_category = {item["value"]: item for item in data["by_category"]}
    assert by_category["tree"]["count"] == 2
    assert by_category["tree"]["quantity"] == 30.0
    assert by_category["shrub"]["amount"] == 100.0

    by_reason = {item["value"]: item for item in data["by_reason"]}
    assert by_reason["dead"]["count"] == 2
    assert by_reason["aging"]["quantity"] == 20.0


def test_list_filters_by_green_space_and_reason(api, make_replacement, make_space):
    space = make_space(name="目标绿地")
    make_replacement(space=space, reason="dead")
    make_replacement(space=space, reason="upgrade")
    make_replacement()

    data = api.data(api.get("/api/v1/plant-replacements", green_space_id=space.id,
                            reason="upgrade"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["reason"] == "upgrade"


def test_list_filters_by_plant_source_and_incomplete(api, make_space):
    space = make_space()
    base = dict(
        green_space_id=space.id,
        plant_name="红叶石楠",
        plant_category="shrub",
        quantity=10,
        unit="plant",
        reason="dead",
        replace_date="2026-03-16",
    )

    def _create(**overrides):
        return api.data(api.post("/api/v1/plant-replacements", {**base, **overrides}), 201)

    _create(plant_source="self_grown", supplier="中心自有苗圃", unit_price=12)
    _create(plant_source="purchased", supplier="萧山苗木合作社", unit_price=80)
    _create(plant_source="purchased", supplier="杭州城西园艺公司", unit_price=None)
    _create(plant_source=None, supplier=None, unit_price=None)

    self_grown = api.data(api.get("/api/v1/plant-replacements", plant_source="self_grown"))
    assert self_grown["meta"]["total"] == 1
    assert self_grown["items"][0]["plant_source"] == "self_grown"

    purchased = api.data(api.get("/api/v1/plant-replacements", plant_source="purchased"))
    assert purchased["meta"]["total"] == 2

    incomplete = api.data(api.get("/api/v1/plant-replacements", source_incomplete="true"))
    assert incomplete["meta"]["total"] == 2
    assert all(item["source_incomplete"] for item in incomplete["items"])


def test_summary_compares_sources_by_avg_price_and_quantity(api, make_space):
    space = make_space()
    base = dict(
        green_space_id=space.id,
        plant_name="香樟",
        plant_category="tree",
        unit="plant",
        reason="dead",
        replace_date="2026-03-16",
    )

    def _create(**overrides):
        return api.data(api.post("/api/v1/plant-replacements", {**base, **overrides}), 201)

    # 自产苗：数量 10×20 元 + 30×40 元，平均单价按金额加权 = 1400/40 = 35 元
    _create(quantity=10, plant_source="self_grown", supplier="中心自有苗圃", unit_price=20)
    _create(quantity=30, plant_source="self_grown", supplier="中心自有苗圃", unit_price=40)
    # 外购苗：数量 5×100 元
    _create(quantity=5, plant_source="purchased", supplier="萧山苗木合作社", unit_price=100)
    # 来源未登记一条
    _create(quantity=8, plant_source=None, supplier=None, unit_price=None)

    data = api.data(api.get("/api/v1/plant-replacements/summary"))
    assert data["total_count"] == 4
    assert data["total_quantity"] == 53.0
    assert data["source_incomplete_count"] == 1
    assert data["source_missing_count"] == 1

    by_source = {item["value"]: item for item in data["by_source"]}
    self_grown = by_source["self_grown"]
    assert self_grown["label"] == "自产苗"
    assert self_grown["count"] == 2
    assert self_grown["quantity"] == 40.0
    assert self_grown["amount"] == 1400.0
    assert self_grown["avg_unit_price"] == 35.0
    assert self_grown["incomplete_count"] == 0

    purchased = by_source["purchased"]
    assert purchased["quantity"] == 5.0
    assert purchased["avg_unit_price"] == 100.0

    missing = by_source[None]
    assert missing["label"] == "来源未登记"
    assert missing["count"] == 1
    assert missing["quantity"] == 8.0
    assert missing["avg_unit_price"] is None
    assert missing["incomplete_count"] == 1


def test_delete_replacement(api, make_replacement):
    replacement = make_replacement()
    api.delete(f"/api/v1/plant-replacements/{replacement.id}")
    assert api.get(f"/api/v1/plant-replacements/{replacement.id}").status_code == 404
