resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.assetmind.id
  display_name   = "${local.name_prefix}-public-sl"
  freeform_tags  = local.common_tags

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
    description = "Allow all egress for package installs and provider calls."
  }

  ingress_security_rules {
    protocol    = "6"
    source      = var.ssh_allowed_cidr
    description = "SSH from the operator CIDR."

    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    protocol    = "6"
    source      = var.app_allowed_cidr
    description = "AssetMind API."

    tcp_options {
      min = var.app_port
      max = var.app_port
    }
  }

  ingress_security_rules {
    protocol    = "6"
    source      = var.app_allowed_cidr
    description = "HTTP for a future reverse proxy."

    tcp_options {
      min = 80
      max = 80
    }
  }

  ingress_security_rules {
    protocol    = "6"
    source      = var.app_allowed_cidr
    description = "HTTPS for a future reverse proxy."

    tcp_options {
      min = 443
      max = 443
    }
  }
}
