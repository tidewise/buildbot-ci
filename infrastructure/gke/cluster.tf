resource "google_container_cluster" "primary" {
    name   = var.cluster_name

    # We can't create a cluster with no node pool defined, but we want to only use
    # separately managed node pools. So we create the smallest possible default
    # node pool and immediately delete it.
    remove_default_node_pool = true
    initial_node_count = 1

    enable_legacy_abac = true

    # Setting an empty username and password explicitly disables basic auth
    master_auth {
        username = ""
        password = ""
        client_certificate_config {
            issue_client_certificate = true
        }
    }
}

resource "google_container_node_pool" "system" {
    name       = "system-pool"
    cluster    = google_container_cluster.primary.name
    node_count = 2

    node_config {
        machine_type = "g1-small"
        disk_size_gb = "10"
        preemptible = true

        labels = {
            system-role = "1"
        }

        oauth_scopes = [
          "https://www.googleapis.com/auth/compute",
          "https://www.googleapis.com/auth/devstorage.read_only",
          "https://www.googleapis.com/auth/logging.write",
          "https://www.googleapis.com/auth/monitoring",
        ]
    }
}

resource "google_container_node_pool" "build" {
    name       = "build-pool"
    cluster    = google_container_cluster.primary.name

    autoscaling {
        min_node_count = 0
        max_node_count = 1
    }

    node_config {
        machine_type = "custom-6-12032"
        disk_size_gb = "20"
        disk_type = "pd-ssd"
        preemptible = true

        labels = { build-role = "1" }
        taint {
          key = "build-role"
          value = "1"
          effect = "NO_EXECUTE"
        }

        oauth_scopes = [
          "https://www.googleapis.com/auth/compute",
          "https://www.googleapis.com/auth/devstorage.read_only",
          "https://www.googleapis.com/auth/logging.write",
          "https://www.googleapis.com/auth/monitoring",
        ]
    }
}

# The following outputs allow authentication and connectivity to the GKE Cluster
# by using certificate-based authentication.
output "client_certificate" {
  value = google_container_cluster.primary.master_auth.0.client_certificate
  sensitive = true
}

output "client_key" {
  value = google_container_cluster.primary.master_auth.0.client_key
  sensitive = true
}

output "cluster_ca_certificate" {
  value = google_container_cluster.primary.master_auth.0.cluster_ca_certificate
  sensitive = true
}

output "host" {
  value = google_container_cluster.primary.endpoint
  sensitive = true
}
