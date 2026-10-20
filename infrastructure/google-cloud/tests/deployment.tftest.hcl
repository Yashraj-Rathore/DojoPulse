mock_provider "google" {}

run "preview_requires_separate_signing_key" {
  command = plan
  variables {
    provisioning_approved = true
    preview = {
      coordinator_image      = "us-central1-docker.pkg.dev/fixture-project/images/coordinator@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      decoder_image          = "us-central1-docker.pkg.dev/fixture-project/images/decoder@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
      web_image              = "fixture.example/web@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
      api_origin             = "https://fixture-api-abc.a.run.app"
      batch_vm_image         = "projects/fixture-project/global/images/batch-docker-001"
      journal_location       = "US"
      journal_kms_key        = "projects/fixture-project/locations/us/keyRings/private/cryptoKeys/journal"
      journal_retention_days = 30
    }
  }
  expect_failures = [terraform_data.preview_preparation]
}

run "isolated_preview_preparation" {
  command = plan
  variables {
    provisioning_approved = true
    secret_versions = {
      DJANGO_SECRET_KEY    = { secret = "django", version = "1" }
      DATABASE_URL         = { secret = "database", version = "1" }
      DATA_SUPPRESSION_KEY = { secret = "suppression", version = "1" }
      CONTROL_JOURNAL_KEY  = { secret = "control", version = "1" }
      PREVIEW_LEDGER_KEY   = { secret = "preview", version = "2" }
    }
    preview = {
      coordinator_image      = "us-central1-docker.pkg.dev/fixture-project/images/coordinator@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      decoder_image          = "us-central1-docker.pkg.dev/fixture-project/images/decoder@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
      web_image              = "fixture.example/web@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
      api_origin             = "https://fixture-api-abc.a.run.app"
      batch_vm_image         = "projects/fixture-project/global/images/batch-docker-001"
      journal_location       = "US"
      journal_kms_key        = "projects/fixture-project/locations/us/keyRings/private/cryptoKeys/journal"
      journal_retention_days = 30
    }
  }
  assert {
    condition     = length(google_storage_bucket.preview_journal) == 3 && alltrue([for bucket in google_storage_bucket.preview_journal : bucket.public_access_prevention == "enforced" && !bucket.force_destroy && bucket.encryption[0].default_kms_key_name == var.preview.journal_kms_key])
    error_message = "Independent private encrypted journals must remain outside media/database restore."
  }
  assert {
    condition     = toset(google_project_iam_custom_role.journal_append[0].permissions) == toset(["storage.objects.create", "storage.objects.get", "storage.objects.list"])
    error_message = "Journal writers must not overwrite or delete records."
  }
  assert {
    condition     = google_compute_instance_template.preview[0].machine_type == "e2-standard-2" && length(google_compute_instance_template.preview[0].network_interface[0].access_config) == 0 && google_compute_instance_template.preview[0].disk[0].auto_delete
    error_message = "One bounded private VM with disposable staging is required."
  }
  assert {
    condition     = output.preview_preparation.live_qualified == false
    error_message = "Prepared infrastructure cannot qualify runtime or activate live media access."
  }
  assert {
    condition     = google_cloud_scheduler_job.preview[0].paused && google_cloud_scheduler_job.preview[0].retry_config[0].retry_count == 0 && google_cloud_run_v2_job.preview_maintenance[0].template[0].task_count == 1 && google_cloud_run_v2_job.preview_maintenance[0].template[0].template[0].max_retries == 0
    error_message = "Maintenance must start paused, serial and without layered retries."
  }
  assert {
    condition     = google_cloud_run_v2_service_iam_member.preview_web_public[0].member == "allUsers" && startswith(google_cloud_run_v2_service_iam_member.preview_api_web[0].member, "serviceAccount:") && google_cloud_run_v2_service.api.ingress == "INGRESS_TRAFFIC_INTERNAL_ONLY"
    error_message = "Only the website may be public; API ingress and invocation must remain private."
  }
}

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
