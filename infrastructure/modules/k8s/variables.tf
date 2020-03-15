variable "project" {}
variable "region" {}
variable "zone" {}
variable "credentials" {}

variable "host" {}
variable client_certificate {}
variable client_key {}
variable cluster_ca_certificate {}

variable "capacities" {
    type = object({
        cache-apt = number
        cache-autoproj-build = number
        cache-autoproj-import = number
    })
}
