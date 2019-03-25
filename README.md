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

Copy `infrastructure/main.tfvars.example` in `infrastructure/main.tfvars` and fill
in the variables. You may also set them on the command line if you prefer.

Finally, run

~~~
terraform plan
~~~

To check that things are all OK. If they are, run

~~~
terraform apply
~~~

After running terraform, you should have a Kubernetes cluster ready to use to
build Rock workspaces. You may run `buildbot start --nodaemon` in the
`buildbot/` folder and try to trigger the `autoproj cache` build to see if
everything is fine.

From now, we recommend to copy the buildbot/ folder to your own repository and
tune it to your needs.
