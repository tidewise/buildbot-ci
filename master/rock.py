from buildbot.plugins import *
from twisted.internet import defer

AUTOPROJ_GIT_URL  = "https://github.com/rock-core/autoproj"
AUTOBUILD_GIT_URL = "https://github.com/rock-core/autobuild"

CACHE_IMPORT_DIR = "/var/cache/autoproj/import"
CACHE_BUILD_DIR  = "/var/cache/autoproj/build"

class BaseWorker(worker.KubeLatentWorker):
    @defer.inlineCallbacks
    def getPodSpec(self, build):
        pod_def = yield super().getPodSpec(build)
        spec = pod_def['spec']
        spec['securityContext'] = {
            'fsGroup': 2000
        }
        return pod_def

class ImportCacheWorker(BaseWorker):
    @defer.inlineCallbacks
    def getPodSpec(self, build):
        pod_def = yield super().getPodSpec(build)
        spec = pod_def['spec']

        container = spec['containers'][0]
        container['imagePullPolicy'] = 'Always'
        container['volumeMounts'] = [
            {
                'name': 'cache-autoproj-import',
                'mountPath': '/var/cache/autoproj/import',
                'readOnly': True
            }
        ]
        spec['volumes'] = [
            {
                'name': 'cache-autoproj-import',
                'persistentVolumeClaim': { 'claimName': 'cache-autoproj-import' }
            }
        ]
        return pod_def

class BuildWorker(BaseWorker):
    @defer.inlineCallbacks
    def getPodSpec(self, build):
        pod_def = yield super().getPodSpec(build)
        spec = pod_def['spec']

        container = spec['containers'][0]
        container['imagePullPolicy'] = 'Always'
        container['resources'] = {
            'requests': {
                'cpu': 6,
                'memory': "10G"
            }
        }
        container['volumeMounts'] = [
            {
                'name': 'cache-autoproj-import',
                'mountPath': '/var/cache/autoproj/import',
                'readOnly': True
            },
            {
                'name': 'cache-autoproj-build',
                'mountPath': '/var/cache/autoproj/build'
            }
        ]
        spec['tolerations'] = [{
            'key': 'build-role',
            'operator': 'Exists'
        }]
        spec['volumes'] = [
            {
                'name': 'cache-autoproj-import',
                'persistentVolumeClaim': { 'claimName': 'cache-autoproj-import' }
            },
            {
                'name': 'cache-autoproj-build',
                'persistentVolumeClaim': { 'claimName': 'cache-autoproj-build' }
            }
        ]
        return pod_def


def Update(factory, osdeps=True):
    arguments = []
    if osdeps:
        factory.addStep(steps.ShellCommand(
            name="Update APT cache",
            command=["sudo", "apt-get", "update"],
            haltOnFailure=True))
    else:
        arguments.append("--no-osdeps")

    factory.addStep(steps.ShellCommand(
        name="Update the workspace",
        command=[".autoproj/bin/autoproj", "update", *arguments, "--interactive=f", "-k"],
        env={'AUTOBUILD_CACHE_DIR': CACHE_IMPORT_DIR},
        haltOnFailure=True))

def ImportCache(factory):
    factory.addStep(steps.ShellCommand(
        name="Update the workspace's import cache",
        command=[".autoproj/bin/autoproj", "cache",
            CACHE_IMPORT_DIR, "--interactive=f", "-k"],
        haltOnFailure=True))

def Bootstrap(factory, url, vcstype="git", autoproj_branch=None, autobuild_branch=None,
              seed_config_path=None,
              autoproj_url=AUTOPROJ_GIT_URL,
              autobuild_url=AUTOBUILD_GIT_URL):

    if autoproj_branch is None:
        bootstrap_script_url = "https://rock-robotics.org/autoproj_bootstrap"
    else:
        bootstrap_script_url = f"https://raw.githubusercontent.com/rock-core/autoproj/{autoproj_branch}/bin/autoproj_bootstrap"

    factory.addStep(steps.ShellCommand(
        name="Download the Autoproj bootstrap script",
        command=["wget", bootstrap_script_url],
        haltOnFailure=True))


    if seed_config_path:
        with open(seed_config_path, 'r') as f:
            seed_config = f.read() + f"\n"
    else:
        seed_config = ""

    seed_config += f"import_log_enabled: false"
    factory.addStep(steps.StringDownload(seed_config,
        workerdest="seed-config.yml",
        name=f"Tuning Autoproj configuration"))

    bootstrap_options = []
    if autoproj_branch is not None or autobuild_branch is not None:
        bootstrap_options.extend(['--gemfile', 'Gemfile.buildbot'])
        gemfile = "source 'https://rubygems.org'"
        gemfile += f"\ngem 'autoproj'"
        if autoproj_branch is not None:
            gemfile += f", git: '{autoproj_url}', branch: '{autoproj_branch}'"

        if autobuild_branch is None:
            gemfile += f"\ngem 'autobuild'"
        else:
            gemfile += f"\ngem 'autobuild', git: {autobuild_url}, branch: '{autobuild_branch}'"

        factory.addStep(steps.StringDownload(gemfile,
            workerdest="Gemfile.buildbot",
            name=f"Setup Gemfile to use autoproj={autoproj_branch} and autobuild={autobuild_branch}"))

    factory.addStep(steps.ShellCommand(
        name="Bootstrap the workspace",
        command=[
            "ruby", "autoproj_bootstrap",
            "--seed-config=seed-config.yml",
            "--no-interactive", *bootstrap_options, vcstype, url],
        haltOnFailure=True))


