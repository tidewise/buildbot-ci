########
## Gem Cache
#
# Deployment of an gemstash container
#
# Bundler is configured in buildbot-worker to use it as gem proxy
# for https://rubygems.org

resource "kubernetes_service" "cache-gem" {
    metadata {
        name = "cache-gem"
    }

    spec {
        selector = {
            app = "${kubernetes_deployment.cache-gem.metadata.0.labels.app}"
        }
        port {
            name = "cache-gem"
            port = 9292
        }
    }
}

resource "google_compute_disk" "cache-gem" {
    name  = "cache-gem"
    type  = "pd-standard"
    zone  = "${var.zone}"
    size  = "10"
}

resource "kubernetes_deployment" "cache-gem" {
    metadata {
        name = "cache-gem"
        labels = {
            app = "cache-gem"
        }
    }

    spec {
        replicas = 1

        selector {
            match_labels = {
                app = "cache-gem"
            }
        }

        template {
            metadata {
                labels = {
                    app = "cache-gem"
                }
            }

            spec {
                container {
                    image = "gcr.io/${var.project}/cache-gem"
                    image_pull_policy = "Always"
                    name = "cache-gem"
                    volume_mount {
                        mount_path = "/var/cache/gem"
                        name = "cache-gem"
                    }
                    resources {
                        requests {
                            cpu = "0"
                        }
                    }
                }
                volume {
                    name = "cache-gem"
                    gce_persistent_disk {
                        pd_name = "${google_compute_disk.cache-gem.name}"
                    }
                }
            }
        }
    }
}

