resource "kubernetes_service_account" "buildbot" {
    metadata {
        name = "buildbot"
    }
}

resource "kubernetes_cluster_role_binding" "buildbot-roles" {
    metadata {
        name = "buildbot-roles"
    }
    role_ref {
        api_group = "rbac.authorization.k8s.io"
        kind = "ClusterRole"
        name = "cluster-admin"
    }
    subject {
        kind = "ServiceAccount"
        name = kubernetes_service_account.buildbot.metadata.0.name
        namespace = "default"
    }
}

data "kubernetes_secret" "buildbot" {
    metadata {
        name = kubernetes_service_account.buildbot.default_secret_name
    }
}

output "ca_certificate" {
    value = base64decode(var.cluster_ca_certificate)
}

output "sa_info" {
    value = data.kubernetes_secret.buildbot.data
}

