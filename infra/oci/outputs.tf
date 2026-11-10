output "availability_domain" {
  description = "Availability domain used for the instance."
  value       = local.availability_domain
}

output "vcn_id" {
  description = "AssetMind VCN OCID."
  value       = oci_core_vcn.assetmind.id
}

output "public_subnet_id" {
  description = "Public subnet OCID."
  value       = oci_core_subnet.public.id
}

output "instance_id" {
  description = "Compute instance OCID."
  value       = oci_core_instance.api.id
}

output "instance_image_id" {
  description = "Ubuntu image OCID selected for the instance."
  value       = local.selected_image_id
}

output "public_ip" {
  description = "Public IP of the API instance. Empty until the VNIC is ready."
  value       = try(oci_core_instance.api.public_ip, null)
}

output "ssh_command" {
  description = "SSH into the instance after cloud-init finishes."
  value       = "ssh ubuntu@${try(oci_core_instance.api.public_ip, "<pending>")}"
}

output "health_url" {
  description = "Health check URL once Caddy and the API are running."
  value       = "http://${try(oci_core_instance.api.public_ip, "<pending>")}/health"
}

output "deploy_hint" {
  description = "Next operator step after terraform apply."
  value       = "Bootstrap Docker, copy infra/oci/.env, then run infra/oci/scripts/deploy.sh. See infra/oci/README.md."
}
