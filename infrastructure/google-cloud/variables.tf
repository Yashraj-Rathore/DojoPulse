variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" {
  type = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Use a separate development/staging/production environment."
  }
}
variable "provisioning_approved" {
  type    = bool
  default = false
}
variable "monthly_budget_usd" { type = number }
variable "recovery_rpo_minutes" { type = number }
variable "recovery_rto_minutes" { type = number }
variable "sql_tier" { type = string }
variable "private_network" { type = string }
variable "private_subnetwork" { type = string }
variable "api_host" { type = string }
variable "api_image" {
  type = string
  validation {
    condition     = can(regex("@sha256:[a-f0-9]{64}$", var.api_image))
    error_message = "An immutable API image digest is required."
  }
}
variable "secret_versions" {
  type = map(object({ secret = string, version = string }))
  validation {
    condition     = alltrue([for name in ["DJANGO_SECRET_KEY", "DATABASE_URL", "DATA_SUPPRESSION_KEY", "CONTROL_JOURNAL_KEY"] : contains(keys(var.secret_versions), name)]) && alltrue([for secret in values(var.secret_versions) : can(regex("^[1-9][0-9]*$", secret.version))])
    error_message = "Explicit secret names and pinned numeric versions required. Do not put secret values in Terraform."
  }
}
