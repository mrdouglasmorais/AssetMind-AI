#!/usr/bin/env python3
"""Try Always Free compute: E2.1.Micro first, then Ampere A1.

Soft-skip only when every shape/AD attempt returns Out of host capacity.

Exit codes:
  0 — provisioned or intentionally skipped (no capacity)
  1 — unexpected error

GitHub Actions outputs (when GITHUB_OUTPUT is set):
  provisioned=true|false
  public_ip=...
  instance_id=...
  skip_reason=...
  shape=...
  compose_profile=micro|full
"""

from __future__ import annotations

import base64
import os
import sys
import time
from pathlib import Path

SHAPE_MICRO = "VM.Standard.E2.1.Micro"
SHAPE_A1 = "VM.Standard.A1.Flex"


def _emit(key: str, value: str) -> None:
    print(f"{key}={value}")
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def _is_capacity_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "out of host capacity" in text or "out of capacity" in text


def _is_flex_shape(shape: str) -> bool:
    return ".Flex" in shape


def _compose_profile_for_shape(shape: str) -> str:
    return "micro" if shape == SHAPE_MICRO or "E2.1.Micro" in shape else "full"


def _shape_attempts() -> list[str]:
    primary = os.environ.get("OCI_INSTANCE_SHAPE", SHAPE_MICRO).strip() or SHAPE_MICRO
    shapes = [primary]
    if primary != SHAPE_A1 and os.environ.get("OCI_TRY_A1_FALLBACK", "true").strip().lower() != "false":
        shapes.append(SHAPE_A1)
    # Deduplicate while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for shape in shapes:
        if shape not in seen:
            seen.add(shape)
            ordered.append(shape)
    return ordered


def _availability_domains(default_ad: str) -> list[str]:
    raw = os.environ.get("OCI_AVAILABILITY_DOMAINS", "").strip()
    if raw:
        ads = [part.strip() for part in raw.split(",") if part.strip()]
        return ads or [default_ad]
    return [default_ad]


def _public_ip(vnet: object, compartment_id: str, instance_id: str) -> str | None:
    vnics = vnet.list_vnic_attachments(compartment_id=compartment_id, instance_id=instance_id).data  # type: ignore[attr-defined]
    for attachment in vnics:
        if not attachment.vnic_id:
            continue
        vnic = vnet.get_vnic(attachment.vnic_id).data  # type: ignore[attr-defined]
        if vnic.public_ip:
            return str(vnic.public_ip)
    return None


def _wait_ip(
    compute: object,
    vnet: object,
    compartment_id: str,
    instance_id: str,
    timeout_s: int = 600,
) -> str | None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        instance = compute.get_instance(instance_id).data  # type: ignore[attr-defined]
        state = instance.lifecycle_state
        print(f"instance state={state}")
        if state == "RUNNING":
            ip = _public_ip(vnet, compartment_id, instance_id)
            if ip:
                return ip
        if state in {"TERMINATING", "TERMINATED"}:
            return None
        time.sleep(15)
    return _public_ip(vnet, compartment_id, instance_id)


def _resolve_image_id(compute: object, *, compartment_id: str, shape: str, fallback: str) -> str:
    """Prefer a live Ubuntu image for the shape; fall back to OCI_IMAGE_OCID when needed."""

    ubuntu_version = os.environ.get("OCI_UBUNTU_VERSION", "22.04").strip() or "22.04"
    try:
        images = compute.list_images(  # type: ignore[attr-defined]
            compartment_id=compartment_id,
            operating_system="Canonical Ubuntu",
            operating_system_version=ubuntu_version,
            shape=shape,
            sort_by="TIMECREATED",
            sort_order="DESC",
        ).data
    except Exception as exc:  # noqa: BLE001
        print(f"image lookup failed for {shape}: {exc}; using fallback", file=sys.stderr)
        if not fallback:
            raise SystemExit(f"no image for shape {shape}") from exc
        return fallback
    if images:
        image_id = str(images[0].id)
        print(f"resolved image for {shape}: {image_id}")
        return image_id
    if fallback and shape == SHAPE_A1:
        print(f"no listed image for {shape}; using OCI_IMAGE_OCID fallback")
        return fallback
    raise SystemExit(f"no Ubuntu {ubuntu_version} image found for shape {shape}")


def _boot_volume_gbs(shape: str) -> int:
    # OCI requires boot volumes >= 50 GB.
    if shape == SHAPE_MICRO:
        return int(os.environ.get("OCI_BOOT_VOLUME_GBS_MICRO", "50"))
    return int(os.environ.get("OCI_BOOT_VOLUME_GBS", "50"))


def main() -> int:
    try:
        from oci.core import ComputeClient, VirtualNetworkClient
        from oci.core.models import (
            CreateVnicDetails,
            InstanceSourceViaImageDetails,
            LaunchInstanceDetails,
            LaunchInstanceShapeConfigDetails,
        )
        from oci.exceptions import ServiceError
    except ImportError:
        print("pip install oci first", file=sys.stderr)
        return 1

    tenancy = _required("OCI_TENANCY_OCID")
    user = _required("OCI_USER_OCID")
    fingerprint = _required("OCI_FINGERPRINT")
    key_content = _required("OCI_PRIVATE_KEY")
    region = os.environ.get("OCI_REGION", "sa-saopaulo-1").strip()
    compartment = os.environ.get("OCI_COMPARTMENT_OCID", tenancy).strip()
    subnet_id = _required("OCI_SUBNET_OCID")
    default_ad = _required("OCI_AVAILABILITY_DOMAIN")
    fallback_image = os.environ.get("OCI_IMAGE_OCID", "").strip()
    ssh_public_key = _required("OCI_SSH_PUBLIC_KEY")
    display_name = os.environ.get("OCI_INSTANCE_DISPLAY_NAME", "assetmind-api").strip()
    ocpus = float(os.environ.get("OCI_INSTANCE_OCPUS", "1"))
    memory_gb = float(os.environ.get("OCI_INSTANCE_MEMORY_GBS", "6"))

    repo_root = Path(__file__).resolve().parents[3]
    cloud_init_path = repo_root / "infra" / "oci" / "cloud-init.yaml"
    user_data = base64.b64encode(cloud_init_path.read_bytes()).decode("ascii")

    key_path = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "oci_api_key.pem"
    key_path.write_text(key_content if key_content.endswith("\n") else key_content + "\n", encoding="utf-8")
    key_path.chmod(0o600)

    config = {
        "user": user,
        "key_file": str(key_path),
        "fingerprint": fingerprint,
        "tenancy": tenancy,
        "region": region,
    }
    compute = ComputeClient(config)
    vnet = VirtualNetworkClient(config)

    existing = compute.list_instances(compartment_id=compartment, display_name=display_name).data
    live = [item for item in existing if item.lifecycle_state in {"PROVISIONING", "RUNNING", "STARTING"}]
    if live:
        instance = live[0]
        shape = str(getattr(instance, "shape", "") or SHAPE_A1)
        public_ip = _public_ip(vnet, compartment, instance.id) or ""
        if instance.lifecycle_state != "RUNNING":
            public_ip = _wait_ip(compute, vnet, compartment, instance.id) or public_ip
        _emit("provisioned", "true")
        _emit("instance_id", instance.id)
        _emit("public_ip", public_ip)
        _emit("skip_reason", "already_exists")
        _emit("shape", shape)
        _emit("compose_profile", _compose_profile_for_shape(shape))
        return 0

    shapes = _shape_attempts()
    ads = _availability_domains(default_ad)
    last_error: BaseException | None = None
    capacity_only = True

    for shape in shapes:
        image_id = _resolve_image_id(compute, compartment_id=compartment, shape=shape, fallback=fallback_image)
        boot_gb = _boot_volume_gbs(shape)
        for availability_domain in ads:
            print(f"trying shape={shape} ad={availability_domain}")
            kwargs: dict[str, object] = {
                "availability_domain": availability_domain,
                "compartment_id": compartment,
                "display_name": display_name,
                "shape": shape,
                "source_details": InstanceSourceViaImageDetails(
                    source_type="image",
                    image_id=image_id,
                    boot_volume_size_in_gbs=boot_gb,
                ),
                "create_vnic_details": CreateVnicDetails(
                    subnet_id=subnet_id,
                    assign_public_ip=True,
                    display_name=f"{display_name}-vnic",
                    hostname_label="api",
                ),
                "metadata": {
                    "ssh_authorized_keys": ssh_public_key,
                    "user_data": user_data,
                },
                "freeform_tags": {
                    "Project": "assetmind",
                    "ManagedBy": "github-actions",
                    "Environment": "always-free",
                    "ShapeProfile": _compose_profile_for_shape(shape),
                },
            }
            if _is_flex_shape(shape):
                kwargs["shape_config"] = LaunchInstanceShapeConfigDetails(ocpus=ocpus, memory_in_gbs=memory_gb)

            details = LaunchInstanceDetails(**kwargs)
            try:
                response = compute.launch_instance(details)
            except ServiceError as exc:
                last_error = exc
                if _is_capacity_error(exc):
                    print(f"Out of host capacity for {shape} in {availability_domain}")
                    continue
                # Shape/image quirks: try the next AD/shape instead of failing the job.
                capacity_only = False
                print(f"OCI ServiceError for {shape} in {availability_domain}: {exc}", file=sys.stderr)
                continue
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if _is_capacity_error(exc):
                    print(f"Out of host capacity for {shape} in {availability_domain}")
                    continue
                capacity_only = False
                print(f"launch failed for {shape} in {availability_domain}: {exc}", file=sys.stderr)
                continue

            instance = response.data
            print(f"Launching {instance.id} shape={shape} …")
            public_ip = _wait_ip(compute, vnet, compartment, instance.id) or ""
            _emit("provisioned", "true")
            _emit("instance_id", instance.id)
            _emit("public_ip", public_ip)
            _emit("skip_reason", "" if public_ip else "ip_pending")
            _emit("shape", shape)
            _emit("compose_profile", _compose_profile_for_shape(shape))
            return 0

    if capacity_only or (last_error is not None and _is_capacity_error(last_error)):
        print("Out of host capacity for all shapes — skipping provision (soft).")
        _emit("provisioned", "false")
        _emit("instance_id", "")
        _emit("public_ip", "")
        _emit("skip_reason", "out_of_host_capacity")
        _emit("shape", "")
        _emit("compose_profile", "")
        return 0

    print(f"launch failed after retries: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
