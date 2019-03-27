from buildbot.plugins import *
from twisted.internet import defer

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
        container['volumeMount'] = [
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

        spec['containers'][0]['resources'] = {
            'requests': {
                'cpu': 6,
                'memory': "10G"
            }
        }
        spec['containers'][0]['volumeMounts'] = [
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
            'effect': 'NoExecute',
            'key': 'build-role',
            'value': '1'
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


def ImportCache(factory):
    factory.addStep(steps.ShellCommand(
        name="Update the workspace's import cache",
        command=[".autoproj/bin/autoproj", "cache",
            "--interactive=f",
            "-k", "/var/cache/autoproj/import"],
        haltOnFailure=True))

def Bootstrap(factory, url, vcstype="git", autoproj_branch=None, autobuild_branch=None,
              autoproj_url="https://github.com/rock-core/autoproj",
              autobuild_url="https://github.com/rock-core/autobuild"):

    if autoproj_branch is None:
        bootstrap_script_url = "https://rock-robotics.org/autoproj_bootstrap"
    else:
        bootstrap_script_url = f"https://raw.githubusercontent.com/rock-core/autoproj/{autoproj_branch}/bin/autoproj_bootstrap"

    factory.addStep(steps.ShellCommand(
        name="Download the Autoproj bootstrap script",
        command=["wget", bootstrap_script_url],
        haltOnFailure=True))

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
            gemfile += f"\ngem 'autobuild', git: 'https://github.com/rock-core/autobuild', branch: '{autobuild_branch}'"

        factory.addStep(steps.StringDownload(gemfile, "Gemfile.buildbot"))

    factory.addStep(steps.ShellCommand(
        name="Bootstrap the workspace",
        command=["ruby", "autoproj_bootstrap", "--no-interactive", *bootstrap_options, vcstype, url],
        haltOnFailure=True))


