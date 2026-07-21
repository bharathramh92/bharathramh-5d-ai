terraform {
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

variable "gcp_project_id" {
  type        = string
  description = "GCP Project ID for ArchAgent infrastructure"
  default     = "archagent-demo"
}

variable "gcp_region" {
  type        = string
  description = "GCP Region for Cloud Run service"
  default     = "us-central1"
}

resource "google_secret_manager_secret" "gemini_key" {
  secret_id = "gemini-api-key"
  replication {
    auto {}
  }
}

resource "google_cloud_run_v2_service" "archagent_service" {
  name     = "archagent-service"
  location = var.gcp_region

  template {
    containers {
      image = "gcr.io/${var.gcp_project_id}/archagent:latest"
      ports {
        container_port = 8000
      }
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}
