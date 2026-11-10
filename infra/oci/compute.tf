resource "oci_core_instance" "api" {
  count = var.enable_compute ? 1 : 0

  availability_domain = local.availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = var.instance_display_name
  shape               = var.shape
  fault_domain        = var.fault_domain != "" ? var.fault_domain : null
  freeform_tags       = local.common_tags

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_memory_in_gbs
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = var.assign_public_ip
    display_name     = "${local.name_prefix}-api-vnic"
    hostname_label   = "api"
  }

  source_details {
    source_type             = "image"
    source_id               = local.selected_image_id
    boot_volume_size_in_gbs = var.boot_volume_size_in_gbs
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(file("${path.module}/cloud-init.yaml"))
  }

  agent_config {
    are_all_plugins_disabled = false
    is_management_disabled   = false
    is_monitoring_disabled   = false
  }

  timeouts {
    create = "30m"
  }

  lifecycle {
    ignore_changes = [
      source_details[0].source_id,
    ]
  }
}
