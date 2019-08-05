# Autoproj import cache
#
# Volume mounted directly in the build pods. Buildbot has a separate
# worker to update it regularly
resource "google_compute_disk" "cache-autoproj-import" {
    name  = "cache-autoproj-import"
    type  = "pd-standard"
    zone  = "${var.zone}"
    size  = "10"
}

resource "kubernetes_persistent_volume" "cache-autoproj-import" {
    metadata {
        name = "cache-autoproj-import"
    }

    spec {
        capacity = {
            storage = "10Gi"
        }
        storage_class_name = "standard"
        access_modes = ["ReadOnlyMany", "ReadWriteOnce"]
        persistent_volume_source {
            gce_persistent_disk {
                pd_name = "${google_compute_disk.cache-autoproj-import.name}"
            }

        }
    }
}

resource "kubernetes_persistent_volume_claim" "cache-autoproj-import" {
    metadata {
        name = "cache-autoproj-import"
    }

    spec {
        access_modes = ["ReadOnlyMany", "ReadWriteOnce"]
        resources {
            requests = {
                storage = "10G"
            }
        }
        volume_name = "${kubernetes_persistent_volume.cache-autoproj-import.metadata.0.name}"
    }
}
