# Setting up a Buildbot-based Kubernetes cluster on GKE

## Step 1: Building and pushing the containers

The containers used by the cluster can be built using the `containers.sh` script. Run

~~~
./containers.sh <NAME_OF_PROJECT>
~~~

Note that the script does _not_ build the buildbot-worker-base container,
instead pulling it from the Docker Hub. If you do want to make changes to
it, build it manually first with

~~~
docker build -t rockcore/buildbot-worker-base containers/buildbot-worker-base
~~~

## Step 2: Setting up the infrastructure

The infrastructure will be set up using [Terraform](terraform.io). You need to
download the tool first.

Then, get the credentials of a suitable service account (the GCE default service
account will do). Download them and place them as `infrastructure/account.json`.

Copy `infrastructure/terraform.tfvars.example` in `infrastructure/terraform.tfvars` and fill
in the variables. You may also set them on the command line if you prefer.

Finally, **within the infrastructure/ folder**, run

~~~
terraform init
~~~

(init needs to be run only once). You can then check what will be done with

~~~
terraform plan
~~~

To check that things are all OK. If they are, run

~~~
terraform apply
# The postprocess script MUST BE executed after each terraform apply
./postprocess
~~~

After running terraform, you should have a Kubernetes cluster ready to use to
build Rock workspaces.

## Run buildbot to connect locally to your cluster

You will need first to forward a public-accessible port to
`localhost:9989` for the workers to connect to. I use [ngrok](https://ngrok.com/)
for this.

Once you do have the public IP and port, modify `SLAVE_TO_MASTER_FQDN` at the top of
`master/master.cfg`.

The best way to run the cluster locally is to execute the `buildbot-master`
container. The `master.sh` script is meant to do that. Execute it from `master/`, e.g.

~~~
cd master
../master.sh
~~~

**NOTE** As of now, the `buildbot/buildbot-master` container does not include what is
necessary to run over kubernetes. This script runs `rockcore/buildbot-master` instead,
which does.

I suggest triggering the `autoproj cache` build to see if everything is fine.

At this point, we recommend to copy the `master/` folder to your own repository
and tune it to your needs.

## Using app.terraform.io for state management

Just rename `remote.tf.example` into `remote.tf` and update the empty variables.
You will also need to register your Terraform API token in `~/.terraformrc` by
adding the following block:

~~~
credentials "app.terraform.io" {
    token = "$TOKEN"
}
~~~

**NOTE**: make sure that `.terraformrc` is readable and writable only for the
user.

