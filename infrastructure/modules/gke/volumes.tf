resource "google_compute_disk" "cache-apt" {
    name  = "cache-apt"
    type  = "pd-standard"
    zone  = var.zone
    size  = var.capacities.cache-apt
}

resource "kubernetes_persistent_volume" "cache-apt" {
    metadata {
        name = "cache-apt-pv"
    }

    spec {
        access_modes = ["ReadWriteOnce"]
        capacity = {
            storage = "${google_compute_disk.cache-apt.size}Gi"
        }

        persistent_volume_source {
            gce_persistent_disk {
                pd_name = google_compute_disk.cache-apt.name
            }
        }
    }
}

resource "google_compute_disk" "cache-autoproj-build" {
    name  = "cache-autoproj-build"
    type  = "pd-standard"
    zone  = var.zone
    size  = var.capacities.cache-autoproj-build
}

resource "kubernetes_persistent_volume" "cache-autoproj-build" {
    metadata {
        name = "cache-autoproj-build-server"
    }

    spec {
        access_modes = ["ReadWriteOnce"]
        capacity = {
            storage = "${google_compute_disk.cache-autoproj-build.size}Gi"
        }

        persistent_volume_source {
            gce_persistent_disk {
                pd_name = google_compute_disk.cache-autoproj-build.name
            }
        }
    }
}

resource "google_compute_disk" "cache-autoproj-import" {
    name  = "cache-autoproj-import"
    type  = "pd-standard"
    zone  = var.zone
    size  = var.capacities.cache-autoproj-import
}

resource "kubernetes_persistent_volume" "cache-autoproj-import" {
    metadata {
        name = "cache-autoproj-import"
    }

    spec {
        capacity = {
            storage = "${google_compute_disk.cache-autoproj-import.size}Gi"
        }
        storage_class_name = "standard"
        access_modes = ["ReadOnlyMany"]
        persistent_volume_source {
            gce_persistent_disk {
                pd_name = google_compute_disk.cache-autoproj-import.name
                read_only = true
            }

        }
    }
}

resource "kubernetes_persistent_volume" "cache-autoproj-import-rw" {
    metadata {
        name = "cache-autoproj-import-rw"
    }

    spec {
        capacity = {
            storage = "${google_compute_disk.cache-autoproj-import.size}Gi"
        }
        storage_class_name = "standard"
        access_modes = ["ReadWriteOnce"]
        persistent_volume_source {
            gce_persistent_disk {
                pd_name = google_compute_disk.cache-autoproj-import.name
            }

        }
    }
}

