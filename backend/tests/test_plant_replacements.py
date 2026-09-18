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


def test_create_replacement_with_seedling_source(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/plant-replacements",
                             replacement_payload(space.id, seedling_source="self_grown",
                                                 supplier="本单位苗圃")), 201)
    assert data["seedling_source"] == "self_grown"
    assert data["seedling_source_label"] == "自产苗"


def test_seedling_source_must_be_valid(api, make_space):
    space = make_space()
    response = api.post("/api/v1/plant-replacements",
                        replacement_payload(space.id, seedling_source="imported"))
    assert response.status_code == 422
    assert "seedling_source" in response.get_json()["data"]


def test_seedling_source_can_be_left_empty(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/plant-replacements",
                             replacement_payload(space.id, seedling_source=None, supplier=None)),
                    201)
    assert data["seedling_source"] is None
    assert data["seedling_source_label"] is None


def test_list_filters_by_seedling_source(api, make_replacement):
    make_replacement(seedling_source="self_grown")
    make_replacement(seedling_source="purchased")
    make_replacement()

    data = api.data(api.get("/api/v1/plant-replacements", seedling_source="purchased"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["seedling_source"] == "purchased"
    assert data["summary"]["missing_source_count"] == 0

    data = api.data(api.get("/api/v1/plant-replacements", source_missing="true"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["seedling_source"] is None
    assert data["summary"]["missing_source_count"] == 1


def test_summary_compares_seedling_sources(api, make_replacement):
    make_replacement(quantity=10, unit_price=100, seedling_source="self_grown")
    make_replacement(quantity=20, unit_price=50, seedling_source="self_grown")
    make_replacement(quantity=5, unit_price=200, seedling_source="purchased")
    make_replacement(quantity=8, unit_price=None, seedling_source=None)

    data = api.data(api.get("/api/v1/plant-replacements/summary"))
    assert data["missing_source_count"] == 1

    by_source = {item["value"]: item for item in data["by_source"]}

    self_grown = by_source["self_grown"]
    assert self_grown["label"] == "自产苗"
    assert self_grown["count"] == 2
    assert self_grown["quantity"] == 30.0
    assert self_grown["amount"] == 2000.0
    assert self_grown["priced_count"] == 2
    assert self_grown["avg_unit_price"] == 75.0

    purchased = by_source["purchased"]
    assert purchased["label"] == "外购苗"
    assert purchased["quantity"] == 5.0
    assert purchased["avg_unit_price"] == 200.0

    missing = by_source[None]
    assert missing["label"] == "未登记"
    assert missing["count"] == 1
    assert missing["quantity"] == 8.0
    assert missing["priced_count"] == 0
    assert missing["avg_unit_price"] is None


def test_list_filters_by_green_space_and_reason(api, make_replacement, make_space):
    space = make_space(name="目标绿地")
    make_replacement(space=space, reason="dead")
    make_replacement(space=space, reason="upgrade")
    make_replacement()

    data = api.data(api.get("/api/v1/plant-replacements", green_space_id=space.id,
                            reason="upgrade"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["reason"] == "upgrade"


def test_delete_replacement(api, make_replacement):
    replacement = make_replacement()
    api.delete(f"/api/v1/plant-replacements/{replacement.id}")
    assert api.get(f"/api/v1/plant-replacements/{replacement.id}").status_code == 404
