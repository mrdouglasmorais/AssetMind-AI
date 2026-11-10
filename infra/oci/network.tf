resource "oci_core_vcn" "assetmind" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.name_prefix}-vcn"
  cidr_blocks    = [var.vcn_cidr]
  dns_label      = replace(local.name_prefix, "-", "")
  freeform_tags  = local.common_tags
}

resource "oci_core_internet_gateway" "assetmind" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.assetmind.id
  display_name   = "${local.name_prefix}-igw"
  enabled        = true
  freeform_tags  = local.common_tags
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.assetmind.id
  display_name   = "${local.name_prefix}-public-rt"
  freeform_tags  = local.common_tags

  route_rules {
    network_entity_id = oci_core_internet_gateway.assetmind.id
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
  }
}

resource "oci_core_subnet" "public" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.assetmind.id
  display_name               = "${local.name_prefix}-public"
  cidr_block                 = var.public_subnet_cidr
  route_table_id             = oci_core_route_table.public.id
  security_list_ids          = [oci_core_security_list.public.id]
  prohibit_public_ip_on_vnic = false
  dns_label                  = "public"
  freeform_tags              = local.common_tags
}
