import json

from tests.conftest import token

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


# ------------------------------------------------------------ auth / RBAC / tenancy
def test_login_wrong_password(client, seeded):
    r = client.post("/api/v1/auth/login", json={"email": "ogretmen@demo.bcn", "password": "yanlis"})
    assert r.status_code == 401


def test_unauthenticated(client):
    assert client.get("/api/v1/exams").status_code == 401


def test_parent_cannot_access_exam_api(client, seeded):
    h = token(client, "veli@demo.bcn")
    assert client.get("/api/v1/exams", headers=h).status_code == 403


def test_teacher_sees_own_exam(client, seeded, teacher):
    r = client.get("/api/v1/exams", headers=teacher)
    assert r.status_code == 200
    assert [e["id"] for e in r.json()] == [str(seeded["main"]["exam_id"])]


def test_other_teacher_cannot_see_exam(client, seeded):
    h = token(client, "ogretmen2@demo.bcn")
    assert client.get("/api/v1/exams", headers=h).json() == []
    assert client.get(f"/api/v1/exams/{seeded['main']['exam_id']}", headers=h).status_code == 404


def test_cross_tenant_isolation(client, seeded):
    h = token(client, "koordinator-x@demo.bcn")  # coordinator of the OTHER org (org-wide role)
    assert client.get(f"/api/v1/exams/{seeded['main']['exam_id']}", headers=h).status_code == 404
    sub = seeded["main"]["submission_ids"][0]
    assert client.get(f"/api/v1/submissions/{sub}", headers=h).status_code == 404
    ids = [e["id"] for e in client.get("/api/v1/exams", headers=h).json()]
    assert str(seeded["main"]["exam_id"]) not in ids


# ------------------------------------------------------------ exam workflow
def _q(**kw):
    base = {"position": 1, "stem_text": "x + 2 = 5", "answer_type": "equation", "points": 10,
            "correct_answer": "x=3", "reference_steps": ["x+2=5", "x=3"], "outcome_ids": []}
    base.update(kw)
    return base


def test_exam_create_validate_publish(client, seeded, teacher):
    m = seeded["main"]
    outcome = str(m["outcomes"]["M.7.2.2.2"])
    body = {"title": "Kısa Sınav", "subject_id": str(m["subject_id"]), "grade_level": 7,
            "class_ids": [str(m["class_7a"])], "exam_date": "2026-11-20", "questions": []}
    r = client.post("/api/v1/exams", json=body, headers=teacher)
    assert r.status_code == 201, r.text
    exam_id = r.json()["id"]

    # reference steps that are not equivalent are rejected
    bad = [_q(reference_steps=["x+2=5", "x=4"], correct_answer="x=4", outcome_ids=[outcome])]
    assert client.put(f"/api/v1/exams/{exam_id}/questions", json=bad, headers=teacher).status_code == 422
    # MC key must be among options
    bad_mc = [_q(answer_type="multiple_choice", correct_answer="E", options={"A": "1", "B": "2"}, reference_steps=[])]
    assert client.put(f"/api/v1/exams/{exam_id}/questions", json=bad_mc, headers=teacher).status_code == 422

    r = client.put(f"/api/v1/exams/{exam_id}/questions", json=[_q(outcome_ids=[outcome])], headers=teacher)
    assert r.status_code == 200
    assert any("doğrulanmadı" in b for b in r.json()["publish_blockers"])
    assert client.post(f"/api/v1/exams/{exam_id}/publish", headers=teacher).status_code == 409

    client.post(f"/api/v1/exams/{exam_id}/validate-keys", headers=teacher)
    r = client.post(f"/api/v1/exams/{exam_id}/publish", headers=teacher)
    assert r.status_code == 200 and r.json()["status"] == "published"
    # published exams are locked
    assert client.put(f"/api/v1/exams/{exam_id}/questions", json=[_q()], headers=teacher).status_code == 409


def test_teacher_cannot_create_for_unassigned_class(client, seeded, teacher):
    m = seeded["main"]
    body = {"title": "Yetkisiz", "subject_id": str(m["subject_id"]), "grade_level": 7,
            "class_ids": [str(m["class_7b"])], "exam_date": "2026-11-20"}
    r = client.post("/api/v1/exams", json=body, headers=teacher)
    assert r.status_code == 403, r.text


def test_csv_import(client, seeded, teacher):
    m = seeded["main"]
    body = {"title": "CSV", "subject_id": str(m["subject_id"]), "grade_level": 7,
            "class_ids": [str(m["class_7a"])], "exam_date": "2026-11-21"}
    exam_id = client.post("/api/v1/exams", json=body, headers=teacher).json()["id"]
    csv_text = ("position;answer_type;stem_text;correct_answer;points;outcome_codes;reference_steps;options\n"
                "1;equation;2x=8 çöz;x=4;10;M.7.2.2.2;2x=8|x=4;\n"
                "2;multiple_choice;Hangisi?;B;5;M.7.1.3.1;;A=1|B=2|C=3\n")
    r = client.post(f"/api/v1/exams/{exam_id}/questions/import-csv", headers=teacher,
                    files={"file": ("q.csv", csv_text.encode(), "text/csv")})
    assert r.status_code == 200, r.text
    assert [q["position"] for q in r.json()["questions"]] == [1, 2]
    bad = csv_text.replace("M.7.1.3.1", "YOK.1")
    r = client.post(f"/api/v1/exams/{exam_id}/questions/import-csv", headers=teacher,
                    files={"file": ("q.csv", bad.encode(), "text/csv")})
    assert r.status_code == 422 and "YOK.1" in r.json()["detail"]


# ------------------------------------------------------------ uploads & jobs
def test_upload_rejects_disguised_file(client, seeded, teacher):
    m = seeded["main"]
    r = client.post(f"/api/v1/exams/{m['exam_id']}/submissions", headers=teacher,
                    data={"student_id": str(m["student_ids"][20 - 1])},
                    files=[("files", ("sayfa.png", b"MZ\x90\x00 not an image", "image/png"))])
    assert r.status_code == 422 and "desteklenmeyen" in r.json()["detail"]


def test_upload_student_not_in_exam_class(client, seeded, teacher):
    m = seeded["main"]
    r = client.post(f"/api/v1/exams/{m['exam_id']}/submissions", headers=teacher,
                    data={"student_id": str(m["student_ids"][22])},  # 7-B student
                    files=[("files", ("a.png", PNG, "image/png"))])
    assert r.status_code == 422


def test_upload_image_with_mock_provider_requires_review(client, seeded, teacher):
    m = seeded["main"]
    r = client.post(f"/api/v1/exams/{m['exam_id']}/submissions", headers=teacher,
                    data={"student_id": str(m["student_ids"][0])},
                    files=[("files", ("1001_s1.png", PNG, "image/png")), ("files", ("1001_s2.png", PNG, "image/png"))])
    assert r.status_code == 201, r.text
    sub_id = r.json()["id"]
    sub = client.get(f"/api/v1/submissions/{sub_id}", headers=teacher).json()
    assert sub["job"]["status"] == "requires_review"
    assert sub["job"]["provider_is_mock"] is True
    assert sub["needs_review_count"] == 5
    resps = client.get(f"/api/v1/submissions/{sub_id}/responses", headers=teacher).json()
    assert all("güvenilir biçimde analiz edilemedi" in x["review_reason"] for x in resps)
    # file served only to authorised users
    fid = sub["files"][0]["id"]
    assert client.get(f"/api/v1/files/{fid}", headers=teacher).status_code == 200
    assert client.get(f"/api/v1/files/{fid}", headers=token(client, "ogretmen2@demo.bcn")).status_code == 404
    # retry is allowed from requires_review
    assert client.post(f"/api/v1/submissions/{sub_id}/retry", headers=teacher).status_code == 200


def test_bulk_upload_groups_by_student_number(client, seeded, teacher):
    m = seeded["main"]
    files = [("files", ("1002_a.png", PNG, "image/png")), ("files", ("1002_b.png", PNG, "image/png")),
             ("files", ("1003.png", PNG, "image/png")), ("files", ("9999.png", PNG, "image/png"))]
    r = client.post(f"/api/v1/exams/{m['exam_id']}/submissions/bulk", headers=teacher, files=files)
    assert r.status_code == 201, r.text
    body = r.json()
    assert sorted(s["student"]["student_number"] for s in body["created"]) == ["1002", "1003"]
    assert len(body["created"][0]["files"]) in (1, 2) and len(body["errors"]) == 1


def test_dev_fixture_pipeline_and_teacher_correction(client, seeded, teacher):
    m = seeded["main"]
    fixture = {"responses": [{"position": 1, "final_answer": "x=25/3", "answer_confidence": 0.95, "steps": [
        {"raw_text": s, "ocr_confidence": 0.95} for s in ["3x+5=20", "3x=20+5", "3x=25", "x=25/3"]]}]}
    r = client.post(f"/api/v1/exams/{m['exam_id']}/submissions", headers=teacher,
                    data={"student_id": str(m["student_ids"][5])},
                    files=[("files", ("x.transcript.json", json.dumps(fixture).encode(), "application/json"))])
    assert r.status_code == 201, r.text
    resps = client.get(f"/api/v1/submissions/{r.json()['id']}/responses", headers=teacher).json()
    q1 = next(x for x in resps if x["question"]["position"] == 1)
    prim = next(h for h in q1["hypotheses"] if h["is_primary"])
    assert prim["detector"] == "sign_transposition" and prim["evidence"][0]["step_index"] == 1
    assert prim["llm_explanation_is_mock"] is True

    # teacher corrects OCR: actually the student wrote 3x = 20 - 5 ... x = 5 -> correct
    r = client.put(f"/api/v1/responses/{q1['id']}/transcription", headers=teacher, json={
        "final_answer": "x=5", "steps": [{"raw_text": s} for s in ["3x+5=20", "3x=20-5", "3x=15", "x=5"]]})
    assert r.status_code == 200
    out = r.json()
    assert out["is_correct"] is True and out["hypotheses"] == [] and out["transcription_source"] == "teacher"
    assert out["score"] == 20


def test_review_flow_feeds_calibration(client, seeded, teacher):
    m = seeded["main"]
    queue = client.get(f"/api/v1/reviews/queue?exam_id={m['exam_id']}", headers=teacher).json()
    assert queue, "seeded data should produce review items"
    item = next(q for q in queue if q["primary_category"])
    resp = client.get(f"/api/v1/responses/{item['response_id']}", headers=teacher).json()
    h = next(x for x in resp["hypotheses"] if x["is_primary"])
    # MODIFIED requires a corrected category
    assert client.post(f"/api/v1/hypotheses/{h['id']}/review", headers=teacher,
                       json={"action": "modified"}).status_code == 422
    r = client.post(f"/api/v1/hypotheses/{h['id']}/review", headers=teacher,
                    json={"action": "modified", "corrected_category": "arithmetic_error", "note": "test"})
    assert r.status_code == 200
    updated = next(x for x in r.json()["hypotheses"] if x["id"] == h["id"])
    assert updated["review_status"] == "modified" and updated["category"] == "arithmetic_error"
    # coordinator in same org can review too; parent cannot
    assert client.post(f"/api/v1/hypotheses/{h['id']}/review", headers=token(client, "veli@demo.bcn"),
                       json={"action": "approved"}).status_code == 403


def test_score_override_bounds(client, seeded, teacher):
    m = seeded["main"]
    resps = client.get(f"/api/v1/submissions/{m['submission_ids'][0]}/responses", headers=teacher).json()
    rid = resps[0]["id"]
    assert client.post(f"/api/v1/responses/{rid}/score", headers=teacher, json={"score": 999}).status_code == 422
    r = client.post(f"/api/v1/responses/{rid}/score", headers=teacher, json={"score": 10, "note": "kısmi puan"})
    assert r.status_code == 200 and r.json()["score"] == 10


def test_item_analysis_and_outcome_report(client, seeded, teacher):
    m = seeded["main"]
    r = client.get(f"/api/v1/exams/{m['exam_id']}/item-analysis", headers=teacher)
    assert r.status_code == 200
    d = r.json()
    assert d["n_items"] == 5 and d["n_students"] >= 20
    assert all(0 <= i["difficulty_p"] <= 1 for i in d["items"])
    mc = next(i for i in d["items"] if i["position"] == 4)
    assert mc["distractors"] and "C" in mc["distractors"]
    r = client.get(f"/api/v1/exams/{m['exam_id']}/outcome-report", headers=teacher)
    assert r.status_code == 200
    assert {row["code"] for row in r.json()["rows"]} == {"M.7.1.3.1", "M.7.2.1.2", "M.7.2.2.2"}
