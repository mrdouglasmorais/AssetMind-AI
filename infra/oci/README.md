# OCI Always Free (Terraform)

Provisions a single Ampere A1 host for AssetMind: VCN, public subnet, security list, and Ubuntu 22.04 ARM instance with Docker via cloud-init.

PostgreSQL stays on the same host (Docker). OCI Always Free Autonomous Database is Oracle Database, not PostgreSQL, so it is not used here (ADR 0005 / ADR 0022).

This stack has been authored. It has not been applied to a live tenancy from this repository unless an operator records that fact.

## Always Free budget used by defaults

| Resource | Default | Tenancy Always Free note |
| --- | --- | --- |
| Shape | `VM.Standard.A1.Flex` | Up to 4 OCPU / 24 GB across A1 |
| OCPU / RAM | 2 / 12 GB | Leaves headroom for a second A1 later |
| Boot volume | 50 GB | Counts toward 200 GB block storage |
| Public IP | Ephemeral | Prefer locking SSH to your `/32` |

## Prerequisites

1. Oracle Cloud account with Always Free Ampere capacity in the home region.
2. Terraform `>= 1.6` and the [Oracle OCI provider](https://registry.terraform.io/providers/oracle/oci/latest).
3. API key for an IAM user with permission to manage networking and compute in the target compartment.
4. An SSH key pair. Put only the public key in `terraform.tfvars`.

## Apply

```bash
cd infra/oci
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars
terraform init
terraform plan
terraform apply
```

Outputs include `public_ip`, `ssh_command`, and `health_url`.

Wait for cloud-init (Docker install) before deploying the app:

```bash
ssh ubuntu@$PUBLIC_IP 'cloud-init status --wait'
```

## Deploy the app

Copy `infra/oci/.env.oci.example` to a local gitignored file (for example `.oci-deploy.env`), fill secrets, then:

```bash
chmod +x infra/oci/scripts/remote-up.sh
PUBLIC_IP=x.x.x.x ENV_FILE=./.oci-deploy.env ./infra/oci/scripts/remote-up.sh
```

The script rsyncs the repo to `/opt/assetmind`, uploads `.env`, and runs `docker compose -f infra/docker/docker-compose.oci.yml up -d --build`.

To pull a prebuilt multi-arch image instead of building on the host, set `ASSETMIND_IMAGE` in that env file and omit `--build` on the host.

AgentOS stays disabled. Product routes use `ASSETMIND_API_KEY`.

## Security notes

- Restrict `ssh_allowed_cidr` to your IP. Do not leave SSH open to the world.
- Never commit `terraform.tfvars`, `.tfstate*`, or the host `.env`.
- Rotate API keys if they ever appear in shell history or chat logs.
- TLS termination (Caddy/nginx + DNS) is intentionally out of this first module.

## Destroy

```bash
terraform destroy
```

This deletes the instance and network. The Postgres Docker volume dies with the boot disk unless you added external backups.

## Render

`infra/render.yaml` remains an alternate blueprint. The primary hosting target is OCI Always Free (ADR 0022).
