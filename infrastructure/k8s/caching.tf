locals {
    cache_app_selector = "caches"
}

# This file instanciates all caching needs for the cluster:
# - a pod that runs gemstash and apt-cacher-ng
# - a pod that exports a build cache through NFS
# - a volume that is mounted in the build pods to provide import cache
#
# The two pods are exposed through the same "cache" service
resource "kubernetes_service" "caches" {
    metadata {
        name = "caches"
    }

    spec {
        selector {
            app = "${local.cache_app_selector}"
        }
        port = [
            {
                name = "cache-apt"
                port = 3142
            },
            {
                name = "cache-gem"
                port = 9292
            },
            {
                name = "nfs4"
                port = 2049
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

resource "google_compute_disk" "cache-gem" {
    name  = "cache-gem"
    type  = "pd-standard"
    zone  = "${var.zone}"
    size  = "10"
}

resource "kubernetes_pod" "package-cache" {
    metadata {
        name = "package-cache"
        labels {
            app = "${local.cache_app_selector}"
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
            },
            {
                image = "gcr.io/${var.project}/cache-gem"
                image_pull_policy = "Always"
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

###### Autoproj related caches

# The autoproj import cache. It is mounted directly in the build pods
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
        capacity {
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

# The autoproj build cache. It is mounted through NFS. We use our own
# NFS export pod because Google Filestore is way too damn expensive

resource "google_compute_disk" "cache-autoproj-build" {
    name  = "cache-autoproj-build"
    type  = "pd-standard"
    zone  = "${var.zone}"
    size  = "20"
}

resource "kubernetes_persistent_volume" "cache-autoproj-build" {
    metadata {
        name = "cache-autoproj-build"
    }

    spec {
        capacity {
            storage = "20G"
        }
        # Without this, the claim (where class_name == "standard") would
        # not match
        storage_class_name = "standard"
        access_modes = ["ReadWriteMany"]
        persistent_volume_source {
            nfs {
                # MUST MATCH the path exported by the cache-autoproj-build-server pod
                path = "/exports"
                server = "${kubernetes_service.caches.metadata.0.name}.default.svc.cluster.local"
            }
        }
    }
}

resource "kubernetes_persistent_volume_claim" "cache-autoproj-build" {
    metadata {
        name = "cache-autoproj-build"
    }

    spec {
        access_modes = ["ReadWriteMany"]
        resources {
            requests {
                storage = "20G"
            }
        }
        volume_name = "${kubernetes_persistent_volume.cache-autoproj-build.metadata.0.name}"
    }
}

resource "kubernetes_pod" "cache-autoproj-build-server" {
    metadata {
        name = "cache-autoproj-build-server"
        labels {
            app = "${local.cache_app_selector}"
        }
    }

    spec {
        container = [
            {
                name = "cache-autoproj-build-server"
                image = "gcr.io/${var.project}/volume-nfs"
                image_pull_policy = "Always"

                security_context {
                    privileged = true
                }

                volume_mount {
                    name = "cache-autoproj-build"
                    # MUST BE /exports
                    #
                    # You cannot mount more than one NFS folder
                    # in /exports as NFS does NOT support exposing overlayfs
                    # folders. This would simply NOT work
                    mount_path = "/exports"
                }
            }
        ]
        volume = [
            {
                name = "cache-autoproj-build"
                gce_persistent_disk {
                    pd_name = "${google_compute_disk.cache-autoproj-build.name}"
                }
            }
        ]
    }
}

resource "kubernetes_pod" "nfs-test" {
    metadata {
        name = "nfs-test"
    }

    spec {
        container = [{
            name = "alpine"
            image = "alpine"

            volume_mount {
                name = "cache-autoproj-build"
                mount_path = "/var/cache/autoproj/build"
            }
        }]
        volume = [
            {
                name = "cache-autoproj-build"
                persistent_volume_claim {
                    claim_name = "${kubernetes_persistent_volume_claim.cache-autoproj-build.metadata.0.name}"
                }
            }
        ]
    }
}
