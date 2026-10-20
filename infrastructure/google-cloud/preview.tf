# Preparation only. No runtime qualification flag is set by Terraform.
variable "preview" {
  type = object({
    coordinator_image      = string
    decoder_image          = string
    web_image              = string
    api_origin             = string
    batch_vm_image         = string
    journal_location       = string
    journal_kms_key        = string
    journal_retention_days = number
  })
  default  = null
  nullable = true
  validation {
    condition = var.preview == null ? true : (
      can(regex("@sha256:[a-f0-9]{64}$", var.preview.coordinator_image)) &&
      can(regex("@sha256:[a-f0-9]{64}$", var.preview.decoder_image)) &&
      can(regex("@sha256:[a-f0-9]{64}$", var.preview.web_image)) &&
      can(regex("^https://[a-z0-9.-]+\\.run\\.app$", var.preview.api_origin)) &&
      can(regex("^projects/[^/]+/global/images/[^/]+$", var.preview.batch_vm_image)) &&
      can(regex("^projects/[^/]+/locations/[^/]+/keyRings/[^/]+/cryptoKeys/[^/]+$", var.preview.journal_kms_key)) &&
      var.preview.journal_retention_days >= 1 && var.preview.journal_retention_days <= 3650
    )
    error_message = "Preview preparation needs immutable images, a named tested Batch VM image, explicit journal geography/CMEK and bounded retention."
  }
}

locals {
  preview_enabled  = var.preview != null
  preview_channels = local.preview_enabled ? toset(["preview", "control", "execution"]) : toset([])
  preview_env = local.preview_enabled ? {
    DEPLOYMENT_NAMESPACE            = "${var.project_id}:${var.environment}"
    GCS_PRIVATE_BUCKET              = google_storage_bucket.media.name
    GOOGLE_PREVIEW_LEDGER_BUCKET    = google_storage_bucket.preview_journal["preview"].name
    GOOGLE_CONTROL_JOURNAL_BUCKET   = google_storage_bucket.preview_journal["control"].name
    GOOGLE_EXECUTION_JOURNAL_BUCKET = google_storage_bucket.preview_journal["execution"].name
  } : {}
  preview_secrets = local.preview_enabled ? {
    for name in ["DATABASE_URL", "DJANGO_SECRET_KEY", "DATA_SUPPRESSION_KEY", "CONTROL_JOURNAL_KEY", "PREVIEW_LEDGER_KEY"] :
    name => "projects/${var.project_id}/secrets/${try(var.secret_versions[name].secret, "missing")}/versions/${try(var.secret_versions[name].version, "0")}"
  } : {}
  preview_api_env = local.preview_enabled ? merge(local.preview_env, {
    PREVIEW_LEDGER_BACKEND           = "GCS"
    CONTROL_JOURNAL_BACKEND          = "GCS"
    PREVIEW_CLOUD_BACKEND            = "BATCH"
    RESUMABLE_STORAGE_PROVIDER       = "GCS"
    DJANGO_TRUST_GATEWAY_HOST        = "1"
    TRUST_MANAGED_PROXY              = "1"
    GOOGLE_TASK_QUEUE                = google_cloud_tasks_queue.analysis.id
    GOOGLE_TASK_TARGET               = "${var.preview.api_origin}/internal/dispatch"
    GOOGLE_TASK_AUDIENCE             = var.preview.api_origin
    GOOGLE_TASK_SERVICE_ACCOUNT      = google_service_account.api.email
    GOOGLE_TASK_GATEWAY_HOST         = var.api_host
    GOOGLE_BATCH_PARENT              = "projects/${var.project_id}/locations/${var.region}"
    GOOGLE_BATCH_TEMPLATE            = "projects/${var.project_id}/global/instanceTemplates/${google_compute_instance_template.preview[0].name}"
    GOOGLE_PREVIEW_COORDINATOR_IMAGE = var.preview.coordinator_image
    GOOGLE_PREVIEW_DECODER_IMAGE     = var.preview.decoder_image
    GOOGLE_PREVIEW_SERVICE_ACCOUNT   = google_service_account.preview[0].email
    GOOGLE_PREVIEW_ENV_JSON          = jsonencode(local.preview_env)
    GOOGLE_PREVIEW_SECRETS_JSON      = jsonencode(local.preview_secrets)
  }) : {}
}

resource "terraform_data" "preview_preparation" {
  count = local.preview_enabled ? 1 : 0
  lifecycle {
    precondition {
      condition     = contains(keys(var.secret_versions), "PREVIEW_LEDGER_KEY")
      error_message = "Preview preparation requires a separately pinned PREVIEW_LEDGER_KEY secret version."
    }
  }
  depends_on = [terraform_data.approval]
}

resource "google_project_service" "preview" {
  for_each           = local.preview_enabled ? toset(["batch.googleapis.com", "compute.googleapis.com", "cloudkms.googleapis.com", "artifactregistry.googleapis.com", "cloudtasks.googleapis.com", "run.googleapis.com", "cloudscheduler.googleapis.com"]) : toset([])
  service            = each.key
  disable_on_destroy = false
  depends_on         = [terraform_data.preview_preparation]
}

resource "google_service_account" "preview" {
  count        = local.preview_enabled ? 1 : 0
  account_id   = "${local.prefix}-preview"
  display_name = "Trusted preview coordinator; never mounted into the offline decoder"
  depends_on   = [terraform_data.preview_preparation]
}

resource "google_project_iam_custom_role" "journal_append" {
  count       = local.preview_enabled ? 1 : 0
  role_id     = "dojopulse_${var.environment}_journal_append"
  title       = "DojoPulse append-only journal"
  permissions = ["storage.objects.create", "storage.objects.get", "storage.objects.list"]
  depends_on  = [terraform_data.preview_preparation]
}

resource "google_storage_bucket" "preview_journal" {
  for_each                    = local.preview_channels
  name                        = "${var.project_id}-${local.prefix}-${each.key}-journal"
  location                    = var.preview.journal_location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels
  versioning { enabled = true }
  encryption { default_kms_key_name = var.preview.journal_kms_key }
  retention_policy {
    retention_period = var.preview.journal_retention_days * 86400
    is_locked        = false # Never irrevocably lock retention as part of preparation.
  }
  depends_on = [terraform_data.preview_preparation, google_kms_crypto_key_iam_member.preview_storage]
}

data "google_storage_project_service_account" "preview" {
  count   = local.preview_enabled ? 1 : 0
  project = var.project_id
}

resource "google_kms_crypto_key_iam_member" "preview_storage" {
  count         = local.preview_enabled ? 1 : 0
  crypto_key_id = var.preview.journal_kms_key
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${data.google_storage_project_service_account.preview[0].email_address}"
  depends_on    = [terraform_data.preview_preparation]
}

resource "google_storage_bucket_iam_member" "preview_journal_api" {
  for_each = local.preview_channels
  bucket   = google_storage_bucket.preview_journal[each.key].name
  role     = google_project_iam_custom_role.journal_append[0].name
  member   = "serviceAccount:${google_service_account.api.email}"
}

resource "google_storage_bucket_iam_member" "preview_journal_worker" {
  for_each = local.preview_channels
  bucket   = google_storage_bucket.preview_journal[each.key].name
  role     = google_project_iam_custom_role.journal_append[0].name
  member   = "serviceAccount:${google_service_account.preview[0].email}"
}

resource "google_storage_bucket_iam_member" "preview_media" {
  count  = local.preview_enabled ? 1 : 0
  bucket = google_storage_bucket.media.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.preview[0].email}"
}

resource "google_project_iam_custom_role" "preview_dispatch" {
  count       = local.preview_enabled ? 1 : 0
  role_id     = "dojopulse_${var.environment}_preview_dispatch"
  title       = "DojoPulse bounded Batch dispatch and VM observation"
  permissions = ["batch.jobs.create", "batch.jobs.get", "batch.jobs.delete", "batch.operations.get", "compute.instances.list"]
}

resource "google_project_iam_member" "preview_dispatch" {
  count   = local.preview_enabled ? 1 : 0
  project = var.project_id
  role    = google_project_iam_custom_role.preview_dispatch[0].name
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_service_account_iam_member" "preview_act_as" {
  count              = local.preview_enabled ? 1 : 0
  service_account_id = google_service_account.preview[0].name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "preview_worker" {
  for_each = local.preview_enabled ? toset(["roles/batch.agentReporter", "roles/logging.logWriter", "roles/cloudsql.client", "roles/artifactregistry.reader"]) : toset([])
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.preview[0].email}"
}

resource "google_secret_manager_secret_iam_member" "preview_worker" {
  for_each  = local.preview_enabled ? var.secret_versions : {}
  secret_id = each.value.secret
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.preview[0].email}"
}

resource "google_compute_instance_template" "preview" {
  count        = local.preview_enabled ? 1 : 0
  name_prefix  = "${local.prefix}-preview-"
  machine_type = "e2-standard-2"
  labels       = local.labels
  disk {
    source_image = var.preview.batch_vm_image
    auto_delete  = true
    boot         = true
    disk_size_gb = 30
    disk_type    = "pd-balanced"
  }
  network_interface {
    network    = var.private_network
    subnetwork = var.private_subnetwork
    # No public IP. Private Google Access/NAT must be independently qualified.
  }
  service_account {
    email  = google_service_account.preview[0].email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }
  metadata = { block-project-ssh-keys = "true", enable-oslogin = "TRUE", disable-legacy-endpoints = "true" }
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }
  lifecycle { create_before_destroy = true }
  depends_on = [google_project_service.preview]
}

output "preview_preparation" {
  value = local.preview_enabled ? {
    api_environment = local.preview_api_env
    batch_template  = google_compute_instance_template.preview[0].self_link
    live_qualified  = false
    web_uri         = google_cloud_run_v2_service.preview_web[0].uri
  } : null
}

resource "terraform_data" "preview_route" {
  count = local.preview_enabled ? 1 : 0
  lifecycle {
    precondition {
      condition     = var.preview.api_origin == google_cloud_run_v2_service.api.uri
      error_message = "Prepare the quarantined API first, then copy its exact api_uri output; the web gateway must never send cookies to a different service."
    }
  }
}

resource "google_service_account" "preview_web" {
  count      = local.preview_enabled ? 1 : 0
  account_id = "${local.prefix}-web"
  depends_on = [terraform_data.preview_preparation]
}

resource "google_cloud_run_v2_service" "preview_web" {
  count               = local.preview_enabled ? 1 : 0
  name                = "${local.prefix}-web"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true
  template {
    service_account                  = google_service_account.preview_web[0].email
    max_instance_request_concurrency = 4
    timeout                          = "60s"
    scaling { max_instance_count = 2 }
    vpc_access {
      network_interfaces {
        network    = var.private_network
        subnetwork = var.private_subnetwork
      }
      egress = "ALL_TRAFFIC"
    }
    containers {
      image = var.preview.web_image
      ports { container_port = 8080 }
      resources { limits = { cpu = "1", memory = "512Mi" } }
      env {
        name  = "DOJOPULSE_API_ORIGIN"
        value = var.preview.api_origin
      }
      env {
        name  = "DOJOPULSE_API_IDENTITY"
        value = "GCP"
      }
      env {
        name  = "DOJOPULSE_API_HOST"
        value = var.api_host
      }
    }
  }
  depends_on = [terraform_data.preview_route]
}

resource "google_cloud_run_v2_service_iam_member" "preview_web_public" {
  count    = local.preview_enabled ? 1 : 0
  name     = google_cloud_run_v2_service.preview_web[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers" # Website only. The API remains internal and IAM authenticated.
}

resource "google_cloud_run_v2_service_iam_member" "preview_api_web" {
  count    = local.preview_enabled ? 1 : 0
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.preview_web[0].email}"
}

resource "google_cloud_run_v2_service_iam_member" "preview_api_tasks" {
  count    = local.preview_enabled ? 1 : 0
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.api.email}"
}

resource "google_cloud_tasks_queue_iam_member" "preview_enqueue" {
  count    = local.preview_enabled ? 1 : 0
  name     = google_cloud_tasks_queue.analysis.name
  location = var.region
  role     = "roles/cloudtasks.enqueuer"
  member   = "serviceAccount:${google_service_account.api.email}"
}

resource "google_service_account_iam_member" "preview_task_identity" {
  count              = local.preview_enabled ? 1 : 0
  service_account_id = google_service_account.api.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.api.email}"
}

resource "google_cloud_run_v2_job" "preview_maintenance" {
  count    = local.preview_enabled ? 1 : 0
  name     = "${local.prefix}-preview-maintenance"
  location = var.region
  template {
    task_count  = 1
    parallelism = 1
    template {
      service_account = google_service_account.api.email
      max_retries     = 0
      timeout         = "600s"
      vpc_access {
        network_interfaces {
          network    = var.private_network
          subnetwork = var.private_subnetwork
        }
        egress = "PRIVATE_RANGES_ONLY"
      }
      containers {
        image   = var.api_image
        command = ["python", "manage.py", "hosted_preview_maintenance"]
        resources { limits = { cpu = "1", memory = "1Gi" } }
        dynamic "env" {
          for_each = merge(local.preview_api_env, { DJANGO_DEBUG = "0", RESTORE_QUARANTINE = "1", DJANGO_ALLOWED_HOSTS = var.api_host })
          content {
            name  = env.key
            value = env.value
          }
        }
        dynamic "env" {
          for_each = var.secret_versions
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value.secret
                version = env.value.version
              }
            }
          }
        }
      }
    }
  }
  depends_on = [terraform_data.preview_route, google_project_service.preview]
}

resource "google_service_account" "preview_scheduler" {
  count      = local.preview_enabled ? 1 : 0
  account_id = "${local.prefix}-scheduler"
}

resource "google_cloud_run_v2_job_iam_member" "preview_scheduler" {
  count    = local.preview_enabled ? 1 : 0
  name     = google_cloud_run_v2_job.preview_maintenance[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.preview_scheduler[0].email}"
}

resource "google_cloud_scheduler_job" "preview" {
  count            = local.preview_enabled ? 1 : 0
  name             = "${local.prefix}-preview"
  region           = var.region
  schedule         = "* * * * *"
  time_zone        = "Etc/UTC"
  paused           = true # Requires a reviewed activation after real cloud acceptance.
  attempt_deadline = "20s"
  retry_config { retry_count = 0 }
  http_target {
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.preview_maintenance[0].name}:run"
    http_method = "POST"
    body        = base64encode("{}")
    headers     = { Content-Type = "application/json" }
    oauth_token { service_account_email = google_service_account.preview_scheduler[0].email }
  }
  depends_on = [google_project_service.preview, google_cloud_run_v2_job_iam_member.preview_scheduler]
}
