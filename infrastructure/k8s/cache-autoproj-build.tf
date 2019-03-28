# Autoproj build cache
#
# It is a GCE disk exposed as a NFSv4 server, then mounted in the
# build workers. NFS is necessary to get a ReadWriteMany mount

resource "kubernetes_service" "cache-autoproj-build" {
    metadata {
        name = "cache-autoproj-build"
    }

    spec {
        selector {
            app = "${kubernetes_pod.cache-autoproj-build-server.metadata.0.labels.app}"
        }
        port = [
            {
                name = "nfs4"
                port = 2049
            }
        ]
    }
}

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
                server = "${kubernetes_service.cache-autoproj-build.metadata.0.name}.default.svc.cluster.local"
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
            app = "cache-autoproj-build"
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

