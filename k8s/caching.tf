resource "google_compute_disk" "cache-apt" {
    name  = "cache-apt"
    type  = "pd-standard"
    zone  = "us-central1-a"
    size  = "10"
}

resource "google_compute_disk" "cache-gem" {
    name  = "cache-gem"
    type  = "pd-standard"
    zone  = "us-central1-a"
    size  = "10"
}

resource "kubernetes_pod" "cache" {
    metadata {
        name = "cache"
        labels {
            app = "package-cache"
        }
    }
    
    spec {
        container = [
            {
                image = "gcr.io/${var.project}/cache-apt"
                name = "cache-apt"
                volume_mount {
                    mount_path = "/var/cache/apt-cacher-ng"
                    name = "cache-apt"
                }
            },
            {
                image = "gcr.io/${var.project}/cache-gem"
                name = "cache-gem"
                volume_mount {
                    mount_path = "/var/cache/gem"
                    name = "cache-gem"
                }
            }
        ]
        volume = [
            {
                name = "cache-apt"
                gce_persistent_disk {
                    pd_name = "${google_compute_disk.cache-apt.name}"
                }
            },
            {
                name = "cache-gem"
                gce_persistent_disk {
                    pd_name = "${google_compute_disk.cache-gem.name}"
                }
            }
        ]
    }
}

resource "kubernetes_service" "cache" {
    metadata {
        name = "package-cache"
    }

    spec {
        selector {
            app = "${kubernetes_pod.cache.metadata.0.labels.app}"
        }
        port = [
            {
                name = "cache-apt"
                port = "3142"
            },
            {
                name = "cache-gem"
                port = "9292"
            }
        ]
    }
}

