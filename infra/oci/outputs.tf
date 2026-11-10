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
  description = "Compute instance OCID when Terraform manages compute."
  value       = try(oci_core_instance.api[0].id, null)
}

output "instance_image_id" {
  description = "Ubuntu image OCID selected for the instance."
  value       = local.selected_image_id
}

output "public_ip" {
  description = "Public IP of the API instance when Terraform manages compute."
  value       = try(oci_core_instance.api[0].public_ip, null)
}

output "ssh_command" {
  description = "SSH into the instance after cloud-init finishes."
  value       = try("ssh ubuntu@${oci_core_instance.api[0].public_ip}", "ssh ubuntu@<pending>")
}

output "health_url" {
  description = "Health check URL once Caddy and the API are running."
  value       = try("http://${oci_core_instance.api[0].public_ip}/health", "http://<pending>/health")
}

output "deploy_hint" {
  description = "Next operator step after terraform apply."
  value       = "Prefer GitHub Actions provision-and-deploy-oci for capacity retries. See docs/architecture/oci-credentials.md."
}
