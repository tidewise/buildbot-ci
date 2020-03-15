variable "project" {
    type = string
}
variable "region" {
    type = string
}
variable "zone" {
    type = string
}
variable "credentials" {}
variable "cluster_name" {
    type = string
}

variable "capacities" {
    type = object({
        cache-apt = number
        cache-autoproj-build = number
        cache-autoproj-import = number
    })
}
