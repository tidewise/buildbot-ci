resource "kubernetes_cluster_role_binding" "sa-admin" {
    metadata {
        name = "sa-admin"
    }
    role_ref {
        api_group = "rbac.authorization.k8s.io"
        kind = "ClusterRole"
        name = "cluster-admin"
    }
    subject {
        kind = "ServiceAccount"
        name = "default"
        namespace = "default"
    }
}
