locals {
  name_prefix = var.project_name

  common_tags = {
    "Project"     = var.project_name
    "ManagedBy"   = "terraform"
    "Environment" = "always-free"
  }

  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[
    var.availability_domain_number - 1
  ].name

  # Prefer Ubuntu Minimal aarch64 when present; fall back to the newest Ubuntu match.
  selected_image_id = coalesce(
    try([
      for image in data.oci_core_images.ubuntu.images :
      image.id if can(regex("(?i)minimal", image.display_name))
    ][0], null),
    data.oci_core_images.ubuntu.images[0].id
  )
}
