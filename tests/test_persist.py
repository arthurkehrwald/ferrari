import json

from ferrari.persist import Store


def test_roundtrip_and_delay(tmp_path):
    path = tmp_path / "sub" / "state.json"
    s = Store(path, save_delay_s=2.0)
    assert s.get("volume", "music") == 0.5
    s.set("volume", "music", 0.7)
    s.tick(now=0)  # Verzögerung noch nicht abgelaufen (dirty_since ist monotonic)
    assert not path.exists()
    s.flush()
    assert json.loads(path.read_text())["volume"]["music"] == 0.7
    assert Store(path).get("volume", "music") == 0.7
    assert list(path.parent.iterdir()) == [path]  # keine Temp-Dateien übrig


def test_corrupt_file_uses_defaults(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{kaputt")
    assert Store(path).get("stall_count") == 0


def test_ignores_unknown_and_wrong_types(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"stall_count": "viele", "foo": 1, "turkey_highscore": 12,
                                "volume": {"music": 1}}))
    s = Store(path)
    assert s.get("stall_count") == 0
    assert s.get("turkey_highscore") == 12
    assert s.get("volume", "music") == 1
    assert "foo" not in s.data


def test_unchanged_value_does_not_dirty(tmp_path):
    s = Store(tmp_path / "state.json")
    s.set("stall_count", 0)
    s.flush()
    assert not (tmp_path / "state.json").exists()
