mock_provider "google" {}

variables {
  project_id           = "fixture-project"
  region               = "fixture-region"
  environment          = "staging"
  monthly_budget_usd   = 1
  recovery_rpo_minutes = 1
  recovery_rto_minutes = 1
  sql_tier             = "db-custom-1-3840"
  private_network      = "projects/fixture-project/global/networks/private"
  private_subnetwork   = "projects/fixture-project/regions/fixture-region/subnetworks/private"
  api_host             = "fixture.example"
  api_image            = "fixture.example/api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  secret_versions = {
    DJANGO_SECRET_KEY    = { secret = "django", version = "1" }
    DATABASE_URL         = { secret = "database", version = "1" }
    DATA_SUPPRESSION_KEY = { secret = "suppression", version = "1" }
    CONTROL_JOURNAL_KEY  = { secret = "journal", version = "1" }
  }
}

run "unapproved_provisioning_fails" {
  command         = plan
  expect_failures = [terraform_data.approval]
}

run "private_bounded_preparation" {
  command = plan
  variables { provisioning_approved = true }
  assert {
    condition     = google_storage_bucket.media.public_access_prevention == "enforced" && google_storage_bucket.media.uniform_bucket_level_access
    error_message = "Media must remain private."
  }
  assert {
    condition     = google_storage_bucket.media.soft_delete_policy[0].retention_duration_seconds == 0 && !google_storage_bucket.media.force_destroy
    error_message = "Deletion/teardown controls must match the reviewed policy."
  }
  assert {
    condition     = !google_sql_database_instance.postgres.settings[0].ip_configuration[0].ipv4_enabled && google_sql_database_instance.postgres.settings[0].backup_configuration[0].point_in_time_recovery_enabled
    error_message = "Database requires private access and PITR."
  }
  assert {
    condition     = google_cloud_tasks_queue.analysis.retry_config[0].max_attempts == 8 && google_cloud_tasks_queue.analysis.rate_limits[0].max_concurrent_dispatches == 2
    error_message = "Task delivery must be bounded."
  }
  assert {
    condition     = google_cloud_run_v2_service.api.ingress == "INGRESS_TRAFFIC_INTERNAL_ONLY" && google_cloud_run_v2_service.api.template[0].scaling[0].max_instance_count == 2
    error_message = "API must have private ingress and a finite scale cap."
  }
}

run "mutable_image_fails" {
  command = plan
  variables {
    provisioning_approved = true
    api_image             = "fixture.example/api:latest"
  }
  expect_failures = [var.api_image]
}
