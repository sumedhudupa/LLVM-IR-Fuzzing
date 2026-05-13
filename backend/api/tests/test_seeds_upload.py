from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_upload_ll_saves_file_and_returns_metadata(client, monkeypatch, tmp_path: Path):
    import app.services.seed_service as seed_service

    monkeypatch.setattr(seed_service, "SEED_DIR", tmp_path)

    ir = b"define i32 @main() { ret i32 0 }\n"
    res = client.post(
        "/api/v1/seeds/upload",
        files={"file": ("seed1.ll", ir, "text/plain")},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "seed1.ll"
    assert data["path"].endswith("seed1.ll")
    assert (tmp_path / "seed1.ll").read_bytes() == ir


def test_upload_ll_auto_renames_on_collision(client, monkeypatch, tmp_path: Path):
    import app.services.seed_service as seed_service

    monkeypatch.setattr(seed_service, "SEED_DIR", tmp_path)

    ir = b"define i32 @main() { ret i32 0 }\n"

    res1 = client.post(
        "/api/v1/seeds/upload",
        files={"file": ("seed1.ll", ir, "text/plain")},
    )
    assert res1.status_code == 200
    assert res1.json()["name"] == "seed1.ll"

    res2 = client.post(
        "/api/v1/seeds/upload",
        files={"file": ("seed1.ll", ir, "text/plain")},
    )
    assert res2.status_code == 200
    assert res2.json()["name"] == "seed1_1.ll"
    assert (tmp_path / "seed1_1.ll").exists()


def test_upload_c_compiles_to_ll_and_saves(client, monkeypatch, tmp_path: Path):
    import app.services.seed_service as seed_service
    import app.routes.seeds as seeds_route

    monkeypatch.setattr(seed_service, "SEED_DIR", tmp_path)

    compiled = b"; ModuleID = 'input.c'\nsource_filename = \"input.c\"\n\ndefine i32 @main() {\nentry:\n  ret i32 0\n}\n"

    monkeypatch.setattr(seeds_route, "compile_c_to_ll", lambda b: compiled)

    c_src = b"int main(){return 0;}\n"
    res = client.post(
        "/api/v1/seeds/upload",
        files={"file": ("prog.c", c_src, "text/x-c")},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "prog.ll"
    assert (tmp_path / "prog.ll").read_bytes() == compiled


def test_upload_rejects_other_extensions(client):
    res = client.post(
        "/api/v1/seeds/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 400
    assert "Only .c and .ll" in res.json()["detail"]
