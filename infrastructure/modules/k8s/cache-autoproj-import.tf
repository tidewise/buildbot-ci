# Autoproj import cache
#
# Volume mounted directly in the build pods. Buildbot has a separate
# worker to update it regularly
resource "kubernetes_persistent_volume_claim" "cache-autoproj-import" {
    metadata {
        name = "cache-autoproj-import"
    }

    spec {
        access_modes = ["ReadOnlyMany"]
        resources {
            requests = {
                storage = "${var.capacities.cache-autoproj-import}Gi"
            }
        }
        volume_name = "cache-autoproj-import"
    }
}

resource "kubernetes_persistent_volume_claim" "cache-autoproj-import-rw" {
    metadata {
        name = "cache-autoproj-import-rw"
    }

    spec {
        access_modes = ["ReadWriteOnce"]
        resources {
            requests = {
                storage = "${var.capacities.cache-autoproj-import}Gi"
            }
        }
        volume_name = "cache-autoproj-import-rw"
    }
}
