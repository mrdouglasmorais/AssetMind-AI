variable "tenancy_ocid" {
  type        = string
  description = "OCI tenancy OCID."
}

variable "user_ocid" {
  type        = string
  description = "OCI API user OCID."
}

variable "fingerprint" {
  type        = string
  description = "API key fingerprint for the OCI user."
}

variable "private_key_path" {
  type        = string
  description = "Path to the PEM private key for the OCI API user."
}

variable "region" {
  type        = string
  description = "OCI region home, for example sa-saopaulo-1 or us-ashburn-1."
}

variable "compartment_ocid" {
  type        = string
  description = "Compartment OCID where resources are created. Often the tenancy root for a personal Always Free account."
}

variable "project_name" {
  type        = string
  description = "Short name prefix for OCI display names."
  default     = "assetmind"
}

variable "availability_domain_number" {
  type        = number
  description = "1-based availability domain index from the tenancy list."
  default     = 1
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key installed on the instance for the ubuntu user."
}

variable "ssh_allowed_cidr" {
  type        = string
  description = "CIDR allowed to reach SSH. Prefer your own /32, not 0.0.0.0/0."
}

variable "app_allowed_cidr" {
  type        = string
  description = "CIDR allowed to reach HTTP/HTTPS on Caddy."
  default     = "0.0.0.0/0"
}

variable "vcn_cidr" {
  type        = string
  description = "CIDR for the AssetMind VCN."
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  type        = string
  description = "CIDR for the public subnet."
  default     = "10.0.1.0/24"
}

variable "instance_display_name" {
  type        = string
  description = "Display name for the Ampere A1 instance."
  default     = "assetmind-api"
}

variable "shape" {
  type        = string
  description = "Always Free Ampere shape."
  default     = "VM.Standard.A1.Flex"
}

variable "instance_ocpus" {
  type        = number
  description = "OCPUs for the Flex shape. Always Free Ampere budget is 4 OCPU across the tenancy."
  default     = 2
}

variable "instance_memory_in_gbs" {
  type        = number
  description = "Memory in GB. Always Free Ampere budget is 24 GB across the tenancy."
  default     = 12
}

variable "boot_volume_size_in_gbs" {
  type        = number
  description = "Boot volume size. Always Free block storage budget is 200 GB across the tenancy."
  default     = 50
}

variable "assign_public_ip" {
  type        = bool
  description = "Assign an ephemeral public IP. Set false if you attach a reserved IP outside this module."
  default     = true
}

variable "ubuntu_version" {
  type        = string
  description = "Canonical Ubuntu version for the ARM image lookup."
  default     = "22.04"
}

variable "fault_domain" {
  type        = string
  description = "Optional fault domain (FAULT-DOMAIN-1|2|3). Leave empty for Oracle to choose."
  default     = ""
}

variable "enable_compute" {
  type        = bool
  description = "When false, Terraform manages only networking. The GitHub provision workflow owns the VM."
  default     = true
}

