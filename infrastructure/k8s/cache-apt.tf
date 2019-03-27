########
## APT Cache
#
# Deployment of an apt-cacher-ng container
#
# The buildbot-worker container is configured to use it as an APT proxy

resource "kubernetes_service" "cache-apt" {
    metadata {
        name = "cache-apt"
    }

    spec {
        selector {
            app = "${kubernetes_pod.cache-apt.metadata.0.name}"
        }
        port = [
            {
                name = "cache-apt"
                port = 3142
            }
        ]
    }
}

resource "google_compute_disk" "cache-apt" {
    name  = "cache-apt"
    type  = "pd-standard"
    zone  = "${var.zone}"
    size  = "10"
}

resource "kubernetes_pod" "cache-apt" {
    metadata {
        name = "cache-apt"
        labels {
            app = "cache-apt"
        }
    }

    spec {
        container = [
            {
                image = "gcr.io/${var.project}/cache-apt"
                image_pull_policy = "Always"
                name = "cache-apt"
                volume_mount {
                    mount_path = "/var/cache/apt-cacher-ng"
                    name = "cache-apt"
                }
            }
        ]
        volume = [
            {
                name = "cache-apt"
                gce_persistent_disk {
                    pd_name = "${google_compute_disk.cache-apt.name}"
                }
            }
        ]
    }
}

