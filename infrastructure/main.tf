variable "project" { }
variable "region" {
    default = "us-central1"
}
variable "zone" {
    default = "us-central1-a"
}

module "gke" {
    source   = "./gke"
    credentials = "${file("account.json")}"
    project  = "${var.project}"
    region   = "${var.region}"
    zone     = "${var.zone}"
}

module "k8s" {
    source = "./k8s"
    host     = "${module.gke.host}"

    credentials = "${file("account.json")}"
    project  = "${var.project}"
    region   = "${var.region}"
    zone     = "${var.zone}"
    client_certificate     = "${module.gke.client_certificate}"
    client_key             = "${module.gke.client_key}"
    cluster_ca_certificate = "${module.gke.cluster_ca_certificate}"
}

output "k8s_host" {
    value = "${module.gke.host}"
}
output "gce_project" {
    value = "${var.project}"
}
output "gce_zone" {
    value = "${var.zone}"
}

resource "template_dir" "buildbot" {
    source_dir = "buildbot"
    destination_dir = "${path.module}/../master/tf"

    vars = {
        sa_credentials = "${jsonencode(module.k8s.sa_credentials)}"
        k8s_host = "${module.gke.host}",
        ca_certificate = "${module.gke.cluster_ca_certificate}"
    }
}

