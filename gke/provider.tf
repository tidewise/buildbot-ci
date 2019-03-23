provider "google" {
  credentials = "${var.credentials}"
  project     = "${var.project}"
  region      = "${var.region}"
  zone        = "${var.zone}"
}
provider "google-beta" {
  credentials = "${var.credentials}"
  project     = "${var.project}"
  region      = "${var.region}"
  zone        = "${var.zone}"
}

