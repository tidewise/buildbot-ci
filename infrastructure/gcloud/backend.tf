terraform {
    backend "remote" {
        hostname = "app.terraform.io"
        organization = "tidewise"

        workspaces {
            name = "buildbot-ci"
        }
    }
}

