#!/usr/bin/env python3
"""Try to create the Always Free Ampere VM. Soft-skip on Out of host capacity.

Exit codes:
  0 — provisioned or intentionally skipped (no capacity)
  1 — unexpected error

GitHub Actions outputs (when GITHUB_OUTPUT is set):
  provisioned=true|false
  public_ip=...
  instance_id=...
  skip_reason=...
"""

from __future__ import annotations

import base64
import os
import sys
import time
from pathlib import Path


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
    availability_domain = _required("OCI_AVAILABILITY_DOMAIN")
    image_id = _required("OCI_IMAGE_OCID")
    ssh_public_key = _required("OCI_SSH_PUBLIC_KEY")
    display_name = os.environ.get("OCI_INSTANCE_DISPLAY_NAME", "assetmind-api").strip()
    ocpus = float(os.environ.get("OCI_INSTANCE_OCPUS", "1"))
    memory_gb = float(os.environ.get("OCI_INSTANCE_MEMORY_GBS", "6"))
    boot_gb = int(os.environ.get("OCI_BOOT_VOLUME_GBS", "50"))

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
        public_ip = _public_ip(vnet, compartment, instance.id) or ""
        if instance.lifecycle_state != "RUNNING":
            public_ip = _wait_ip(compute, vnet, compartment, instance.id) or public_ip
        _emit("provisioned", "true")
        _emit("instance_id", instance.id)
        _emit("public_ip", public_ip)
        _emit("skip_reason", "already_exists")
        return 0

    details = LaunchInstanceDetails(
        availability_domain=availability_domain,
        compartment_id=compartment,
        display_name=display_name,
        shape="VM.Standard.A1.Flex",
        shape_config=LaunchInstanceShapeConfigDetails(ocpus=ocpus, memory_in_gbs=memory_gb),
        source_details=InstanceSourceViaImageDetails(
            source_type="image",
            image_id=image_id,
            boot_volume_size_in_gbs=boot_gb,
        ),
        create_vnic_details=CreateVnicDetails(
            subnet_id=subnet_id,
            assign_public_ip=True,
            display_name=f"{display_name}-vnic",
            hostname_label="api",
        ),
        metadata={
            "ssh_authorized_keys": ssh_public_key,
            "user_data": user_data,
        },
        freeform_tags={
            "Project": "assetmind",
            "ManagedBy": "github-actions",
            "Environment": "always-free",
        },
    )

    try:
        response = compute.launch_instance(details)
    except ServiceError as exc:
        if _is_capacity_error(exc):
            print("Out of host capacity — skipping provision (soft).")
            _emit("provisioned", "false")
            _emit("instance_id", "")
            _emit("public_ip", "")
            _emit("skip_reason", "out_of_host_capacity")
            return 0
        print(f"OCI ServiceError: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        if _is_capacity_error(exc):
            _emit("provisioned", "false")
            _emit("instance_id", "")
            _emit("public_ip", "")
            _emit("skip_reason", "out_of_host_capacity")
            return 0
        print(f"launch failed: {exc}", file=sys.stderr)
        return 1

    instance = response.data
    print(f"Launching {instance.id} …")
    public_ip = _wait_ip(compute, vnet, compartment, instance.id) or ""
    _emit("provisioned", "true")
    _emit("instance_id", instance.id)
    _emit("public_ip", public_ip)
    _emit("skip_reason", "" if public_ip else "ip_pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
