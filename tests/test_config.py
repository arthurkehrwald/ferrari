import copy

import pytest
import yaml

from ferrari import config


@pytest.fixture
def raw():
    return yaml.safe_load(config.DEFAULT_PATH.read_text())


def parse(raw):
    return config._parse(raw)


def test_default_config_is_valid():
    cfg = config.load()
    assert cfg.pico.buttons["play"] == 0
    assert cfg.pico.encoders["music_volume"] == (11, 12)
    assert cfg.relay.keep_mask == 1 << cfg.relay.tv


def test_firmware_config_order(raw):
    cfg = parse(raw)
    fw = cfg.pico.firmware_config()
    names = cfg.pico.digital_inputs
    assert len(fw["inputs"]) == len(names)
    assert fw["inputs"][names.index("ignition")] == 10
    assert fw["brightness"] == round(cfg.pico.max_brightness * 255)


def errors(raw):
    with pytest.raises(config.ConfigError) as e:
        parse(raw)
    return e.value.errors


def test_duplicate_pin(raw):
    raw["pico"]["buttons"]["nitro"] = "GP0"
    assert any("schon belegt" in e for e in errors(raw))


def test_adc_pin(raw):
    raw["pico"]["analog"]["pong_left"] = "GP5"
    errs = errors(raw)
    assert any("pico.analog.pong_left" in e and "ADC" in e for e in errs)


def test_invalid_pin(raw):
    raw["pico"]["buttons"]["play"] = "GP25"
    assert any("kein nutzbarer Pin" in e for e in errors(raw))


def test_duplicate_relay(raw):
    raw["relay"]["tv"] = 0
    assert any("Kanal 0 ist schon belegt" in e for e in errors(raw))


def test_missing_and_wrong_type(raw):
    r = copy.deepcopy(raw)
    del r["wheel"]["device"]
    r["audio"]["volume_step"] = "viel"
    errs = errors(r)
    assert "wheel.device: fehlt" in errs
    assert any(e.startswith("audio.volume_step") for e in errs)


def test_unknown_keep_device(raw):
    raw["relay"]["keep_on_timeout"] = ["toaster"]
    assert any("toaster" in e for e in errors(raw))


def test_heartbeat_too_slow(raw):
    raw["relay"]["heartbeat_s"] = 0.8
    assert any(e.startswith("relay.heartbeat_s") for e in errors(raw))
