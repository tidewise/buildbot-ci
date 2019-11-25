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
        selector = {
            app = "${kubernetes_deployment.cache-apt.metadata.0.labels.app}"
        }
        port {
            name = "cache-apt"
            port = 3142
        }
    }
}

resource "google_compute_disk" "cache-apt" {
    name  = "cache-apt"
    type  = "pd-standard"
    zone  = "${var.zone}"
    size  = "10"
}

resource "kubernetes_deployment" "cache-apt" {
    metadata {
        name = "cache-apt-deployment"
        labels = {
            app = "cache-apt"
        }
    }

    spec {
        replicas = 1

        selector {
            match_labels = {
                app = "cache-apt"
            }
        }

        template {
            metadata {
                labels = {
                    app = "cache-apt"
                }
            }

            spec {
                container {
                    image = "gcr.io/${var.project}/cache-apt"
                    image_pull_policy = "Always"
                    name = "cache-apt"
                    volume_mount {
                        mount_path = "/var/cache/apt-cacher-ng"
                        name = "cache-apt"
                    }
                    resources {
                        requests {
                            cpu = "0"
                        }
                    }
                }

                volume {
                    name = "cache-apt"
                    gce_persistent_disk {
                        pd_name = "${google_compute_disk.cache-apt.name}"
                    }
                }
            }
        }
    }
}

