terraform {
  required_version = ">= 1.15, < 2.0"
  required_providers {
    google = { source = "hashicorp/google", version = ">= 7.0, < 8.0" }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  prefix = "dojopulse-${var.environment}"
  labels = { application = "dojopulse", environment = var.environment }
}

resource "terraform_data" "approval" {
  lifecycle {
    precondition {
      condition     = var.provisioning_approved && var.monthly_budget_usd > 0 && var.recovery_rpo_minutes > 0 && var.recovery_rto_minutes > 0
      error_message = "Provisioning requires explicit region/cost/privacy/security approval and recovery objectives."
    }
  }
}

resource "google_service_account" "api" {
  account_id   = "${local.prefix}-api"
  display_name = "DojoPulse API ${var.environment}"
  depends_on   = [terraform_data.approval]
}

resource "google_project_iam_member" "sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_secret_manager_secret_iam_member" "api_secrets" {
  for_each  = var.secret_versions
  secret_id = each.value.secret
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

resource "google_sql_database_instance" "postgres" {
  name                = "${local.prefix}-postgres"
  database_version    = "POSTGRES_17"
  region              = var.region
  deletion_protection = true
  settings {
    tier              = var.sql_tier
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    disk_size         = 10
    disk_autoresize   = false
    user_labels       = local.labels
    ip_configuration {
      ipv4_enabled    = false
      private_network = var.private_network
    }
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings { retained_backups = 7 }
    }
  }
  depends_on = [terraform_data.approval]
}

resource "google_sql_database" "application" {
  name     = "dojopulse"
  instance = google_sql_database_instance.postgres.name
}

resource "google_storage_bucket" "media" {
  name                        = "${var.project_id}-${local.prefix}-media"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels
  versioning { enabled = true }
  soft_delete_policy { retention_duration_seconds = 0 }
  # No retention lock: owner deletion must purge every object generation.
  # Backups and control journals require separately approved independent policies.
  depends_on = [terraform_data.approval]
}

resource "google_storage_bucket_iam_member" "media_api" {
  bucket = google_storage_bucket.media.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.api.email}"
}

resource "google_cloud_tasks_queue" "analysis" {
  name     = "${local.prefix}-analysis"
  location = var.region
  rate_limits {
    max_concurrent_dispatches = 2
    max_dispatches_per_second = 1
  }
  retry_config {
    max_attempts       = 8
    max_retry_duration = "3600s"
    min_backoff        = "5s"
    max_backoff        = "300s"
    max_doublings      = 5
  }
  depends_on = [terraform_data.approval]
}

resource "google_cloud_run_v2_service" "api" {
  name                = "${local.prefix}-api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = true
  template {
    service_account                  = google_service_account.api.email
    timeout                          = "60s"
    max_instance_request_concurrency = 4
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
    vpc_access {
      network_interfaces {
        network    = var.private_network
        subnetwork = var.private_subnetwork
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
    containers {
      image = var.api_image
      ports { container_port = 8080 }
      resources { limits = { cpu = "1", memory = "1Gi" } }
      env {
        name  = "DJANGO_DEBUG"
        value = "0"
      }
      env {
        name  = "RESTORE_QUARANTINE"
        value = "1"
      }
      env {
        name  = "DEPLOYMENT_NAMESPACE"
        value = "${var.project_id}:${var.environment}"
      }
      env {
        name  = "DJANGO_ALLOWED_HOSTS"
        value = var.api_host
      }
      env {
        name  = "GCS_PRIVATE_BUCKET"
        value = google_storage_bucket.media.name
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
  depends_on = [google_project_iam_member.sql_client, google_secret_manager_secret_iam_member.api_secrets]
}

# Cloud Run Jobs media execution is intentionally absent: Cloud Run cannot run
# the qualified nested Docker sandbox. A separately reviewed execution profile
# and signed journal service are prerequisites, not flag overrides.

output "api_uri" { value = google_cloud_run_v2_service.api.uri }
output "sql_connection_name" { value = google_sql_database_instance.postgres.connection_name }
output "media_bucket" { value = google_storage_bucket.media.name }
