import importlib.util
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[2] / "infra" / "oci" / "scripts" / "ci_try_provision.py"
    spec = importlib.util.spec_from_file_location("ci_try_provision", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_flex_detection_and_compose_profile(monkeypatch) -> None:
    mod = _load_module()
    assert mod._is_flex_shape("VM.Standard.A1.Flex")
    assert not mod._is_flex_shape("VM.Standard.E2.1.Micro")
    assert mod._compose_profile_for_shape("VM.Standard.E2.1.Micro") == "micro"
    assert mod._compose_profile_for_shape("VM.Standard.A1.Flex") == "full"
    monkeypatch.setenv("OCI_INSTANCE_SHAPE", "VM.Standard.E2.1.Micro")
    monkeypatch.setenv("OCI_TRY_A1_FALLBACK", "true")
    assert mod._shape_attempts() == ["VM.Standard.E2.1.Micro", "VM.Standard.A1.Flex"]
    monkeypatch.setenv("OCI_TRY_A1_FALLBACK", "false")
    assert mod._shape_attempts() == ["VM.Standard.E2.1.Micro"]
    monkeypatch.setenv("OCI_AVAILABILITY_DOMAINS", "AD-1, AD-2")
    assert mod._availability_domains("default") == ["AD-1", "AD-2"]
    assert mod._boot_volume_gbs("VM.Standard.E2.1.Micro") == 47
