variable "project" {
    default = "seabots"
}
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

    client_certificate     = "${module.gke.client_certificate}"
    client_key             = "${module.gke.client_key}"
    cluster_ca_certificate = "${module.gke.cluster_ca_certificate}"
}

