# OCI credentials and GitHub secrets

This guide covers what to create in Oracle Cloud and what to store in GitHub. **Do not commit private keys or tenancy secrets.**

Always Free Ampere VMs can only be created in the **home region** (`sa-saopaulo-1` for this tenancy). Capacity is often unavailable; the provision pipeline soft-skips instead of failing.

## 1. Create an OCI API key (console)

1. Sign in to [cloud.oracle.com](https://cloud.oracle.com).
2. Profile → **API keys** → **Add API key** → generate pair.
3. Store the private key at `~/.oci/oci_api_key.pem` (`chmod 600`).
4. Save the config preview into `~/.oci/config`.

## 2. Local Terraform (network once)

Networking was applied locally. Keep VCN/subnet state. When the GitHub provision workflow owns the VM, disable compute in Terraform:

```hcl
# infra/oci/terraform.tfvars
enable_compute = false
```

Then `terraform apply` so Terraform stops managing `oci_core_instance`.

Stop any local `./scripts/retry-instance.sh` (Ctrl+C) to avoid fighting the pipeline.

## 3. Application secrets on the VM (`infra/oci/.env`)

Prepare the file locally (do not commit):

```bash
cp infra/oci/.env.example infra/oci/.env
# fill POSTGRES_PASSWORD, ASSETMIND_API_KEY, GROQ_API_KEY, …
```

The whole file becomes the GitHub secret `OCI_ENV_FILE`.

## 4. GitHub secrets and variables

**Settings → Secrets and variables → Actions**

### Secrets for provision (`provision-and-deploy-oci.yml`)

| Secret | Value (from your tenancy) |
| --- | --- |
| `OCI_TENANCY_OCID` | `tenancy=` from `~/.oci/config` |
| `OCI_USER_OCID` | `user=` from config |
| `OCI_FINGERPRINT` | API key fingerprint |
| `OCI_PRIVATE_KEY` | Full PEM private key contents |
| `OCI_COMPARTMENT_OCID` | Usually same as tenancy OCID |
| `OCI_SUBNET_OCID` | `terraform output -raw public_subnet_id` |
| `OCI_AVAILABILITY_DOMAIN` | `terraform output -raw availability_domain` |
| `OCI_IMAGE_OCID` | `terraform output -raw instance_image_id` |
| `OCI_SSH_PUBLIC_KEY` | Contents of `~/.ssh/id_ed25519.pub` |

Current networking outputs for this project (home region):

```text
OCI_SUBNET_OCID=ocid1.subnet.oc1.sa-saopaulo-1.aaaaaaaasgzpuqvtwez4r62lhtzjt6pr7iagb2kpolljwfyis6owrksroy5a
OCI_AVAILABILITY_DOMAIN=cdtx:SA-SAOPAULO-1-AD-1
OCI_IMAGE_OCID=ocid1.image.oc1.sa-saopaulo-1.aaaaaaaagx3wh2vaw7hpzohtk5t4v3owd6aqapssq2uzakwprau7eqbrmroq
```

### Secrets for deploy (after VM exists)

| Secret | Purpose |
| --- | --- |
| `OCI_SSH_PRIVATE_KEY` | SSH private key matching `OCI_SSH_PUBLIC_KEY` |
| `OCI_ENV_FILE` | Full production `infra/oci/.env` |
| `OCI_SSH_USER` | Optional, default `ubuntu` |
| `OCI_DEPLOY_PATH` | Optional, default `/opt/assetmind` |

### Optional repository variables

| Variable | Default |
| --- | --- |
| `OCI_REGION` | `sa-saopaulo-1` |
| `OCI_INSTANCE_SHAPE` | `VM.Standard.E2.1.Micro` |
| `OCI_TRY_A1_FALLBACK` | `true` |
| `OCI_INSTANCE_OCPUS` | `1` (A1 Flex only) |
| `OCI_INSTANCE_MEMORY_GBS` | `6` (A1 Flex only) |
| `OCI_AVAILABILITY_DOMAINS` | empty → use `OCI_AVAILABILITY_DOMAIN` only |

`OCI_IMAGE_OCID` remains useful as an A1 fallback. The provision script resolves Ubuntu images per shape via the OCI API (amd64 for Micro, arm64 for A1).

## 5. Pipeline behaviour

Workflow: `.github/workflows/provision-and-deploy-oci.yml`

1. **Every 2 hours** (and manual dispatch): try **E2.1.Micro** first, then **A1.Flex** if still no capacity.
2. Soft-skip (`provisioned=false`) only when **both** shapes return Out of host capacity.
3. If the VM is created or already running → deploy Compose via SSH.
4. Micro deploy uses `COMPOSE_PROFILE=micro` (prod + `docker-compose.micro.yml`, no worker, build amd64 on host). A1 uses `full`.

Manual run: Actions → **provision-and-deploy-oci** → Run workflow.

## 6. Suggested sequence now

1. Ctrl+C on local `retry-instance.sh`.
2. Set `enable_compute = false` in `terraform.tfvars` and `terraform apply`.
3. Add the GitHub secrets above (including `OCI_PRIVATE_KEY` and network OCIDs).
4. Prepare `OCI_ENV_FILE` from a filled `infra/oci/.env`.
5. Run **provision-and-deploy-oci** manually once to verify Micro/A1 wiring.
6. Leave the schedule on; it will deploy when either Always Free shape appears.

## 7. Always Free reminders

- Ampere Always Free is **home-region only** — other regions are not a free Ampere workaround.
- E2.1.Micro is Always Free x86 (~1 GB). Expect swap and a reduced stack; OOM risk under load.
- Capacity is not guaranteed; soft-skip after both shapes fail is intentional.
- Same-disk Postgres backups are not disaster recovery.
