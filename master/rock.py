from buildbot.plugins import *
from twisted.internet import defer

AUTOPROJ_GIT_URL  = "https://github.com/rock-core/autoproj"
AUTOBUILD_GIT_URL = "https://github.com/rock-core/autobuild"
AUTOPROJ_CI_GIT_URL = "https://github.com/rock-core/autoproj-ci"

CACHE_IMPORT_DIR = "/var/cache/autoproj/import"
cache_import_lock = util.MasterLock("cache-import")
CACHE_BUILD_DIR = util.Interpolate('/var/cache/autoproj/build/%(prop:buildername)s')
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
                'readOnly': False
            }
        ]
        spec['volumes'] = [
            {
                'name': 'cache-autoproj-import',
                'persistentVolumeClaim': { 'claimName': 'cache-autoproj-import' }
            }
        ]
        return pod_def

class BuildCacheWorker(BaseWorker):
    @defer.inlineCallbacks
    def getPodSpec(self, build):
        pod_def = yield super().getPodSpec(build)
        spec = pod_def['spec']

        container = spec['containers'][0]
        container['imagePullPolicy'] = 'Always'
        container['volumeMounts'] = [
            {
                'name': 'cache-autoproj-build',
                'mountPath': '/var/cache/autoproj/build',
            }
        ]
        spec['volumes'] = [
            {
                'name': 'cache-autoproj-build',
                'persistentVolumeClaim': { 'claimName': 'cache-autoproj-build' }
            }
        ]
        return pod_def

class BuildWorker(BaseWorker):
    @defer.inlineCallbacks
    def getPodSpec(self, build):
        pod_def = yield super().getPodSpec(build)
        spec = pod_def['spec']

        cpu = build.getProperty('parallel_build_level', 1)
        memory = build.getProperty('memory_per_build_process_G', 2)

        container = spec['containers'][0]
        container['imagePullPolicy'] = 'Always'
        container['resources'] = {
            'requests': {
                'cpu': cpu,
                'memory': f"{memory * cpu}G"
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


def AutoprojStep(factory, *args, name=None, **kwargs):
    if name is None:
        name = f"autoproj {args[0]}"

    factory.addStep(steps.ShellCommand(name=name,
        command=[".autoproj/bin/autoproj", *args],
        haltOnFailure=True, **kwargs))

def Update(factory, osdeps=True):
    osdeps_update = []
    arguments = []

    if osdeps:
        osdeps_update.append(util.ShellArg(
            command=["sudo", "apt-get", "update"], logfile="apt-update"))
    else:
        arguments.append("--no-osdeps")

    factory.addStep(steps.ShellSequence(
        name="Update",
        commands=[*osdeps_update,
            util.ShellArg(
                command=[".autoproj/bin/autoproj", "update", *arguments,
                    "--interactive=f", "-k"],
                logfile="autoproj-update"
            )
        ],
        env={'AUTOBUILD_CACHE_DIR': CACHE_IMPORT_DIR},
        locks=[cache_import_lock.access('counting')],
        haltOnFailure=True))

def CleanBuildCache(factory):
    factory.addStep(steps.ShellCommand(
        name="Clean the build cache",
        command=["rm", "-rf", CACHE_BUILD_DIR]))
    factory.addStep(steps.ShellCommand(
        name="Check result",
        command=["find", CACHE_BUILD_DIR]))

def UpdateImportCache(factory):
    factory.addStep(steps.ShellCommand(
        name="Update the workspace's import cache",
        command=[".autoproj/bin/autoproj", "cache",
            CACHE_IMPORT_DIR, "--interactive=f", "-k"],
        locks=[cache_import_lock.access('exclusive')],
        haltOnFailure=True))

def GitCredentials(factory, url, credentials):
    """Register credentials to be used by git to access a given url

    Parameters: 
    factory: the Buildbot factory
    url (string): the git base URL, e.g. https://github.com
    credentials (string|secret): the credentials, in a format that the git
        credential helper understands

    For instance, to use a GitHub personal access token, one could define a
    Buildbot secret with

    protocol=https
    host=github.com
    username=$API_KEY
    password=

    And use it with

    rock.GitCredentials(factory, "https://github.com", util.Secret("github_credentials"))
    """

    factory.addStep(steps.ShellCommand(
        name=f"Setting up git to use our credentials for {url}",
        command=["git", "config", "--global", f"credential.{url}.helper", "cache"],
        haltOnFailure=True))
    factory.addStep(steps.ShellCommand(
        name=f"Setting up credentials for {url}",
        command=["git", "credential", "approve"],
        initialStdin=credentials,
        haltOnFailure=True))

def Bootstrap(factory, buildconf_url,
              buildconf_default_branch="master",
              vcstype="git",
              autoproj_branch=None,
              autobuild_branch=None,
              autoproj_ci_branch=None,
              seed_config_path=None,
              flavor="master",
              autoproj_url=AUTOPROJ_GIT_URL,
              autobuild_url=AUTOBUILD_GIT_URL,
              autoproj_ci_url=AUTOPROJ_CI_GIT_URL):

    if autoproj_branch is None:
        bootstrap_script_url = "https://rock-robotics.org/autoproj_bootstrap"
    else:
        bootstrap_script_url = f"https://raw.githubusercontent.com/rock-core/autoproj/{autoproj_branch}/bin/autoproj_bootstrap"

    if seed_config_path:
        with open(seed_config_path, 'r') as f:
            seed_config = f.read() + f"\n"
    else:
        seed_config = ""

    seed_config += f"""
import_log_enabled: false
separate_prefixes: true
ROCK_SELECTED_FLAVOR: {flavor}
    """

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
            gemfile += f"\ngem 'autobuild', git: '{autobuild_url}', branch: '{autobuild_branch}'"

        factory.addStep(steps.StringDownload(gemfile,
            workerdest="Gemfile.buildbot",
            name=f"Setup Gemfile to use autoproj={autoproj_branch} and autobuild={autobuild_branch}"))

    autoproj_ci_args=[]
    if autoproj_ci_branch is not None:
        autoproj_ci_args=["--git", autoproj_ci_url, "--branch", autoproj_ci_branch]

    bundle_config = util.Interpolate(
        'echo "BUNDLE_JOBS: \"%(prop:parallel_build_level:-1)s\"" >> /home/buildbot/.bundle/config')
    factory.addStep(steps.ShellSequence(
        name="Bootstrap",
        commands=[
            util.ShellArg(command=["wget", bootstrap_script_url],
                logfile="download", haltOnFailure=True),
            util.ShellArg(command=bundle_config, logfile="bundle-config",
                haltOnFailure=True),
            util.ShellArg(command=[
                "ruby", "autoproj_bootstrap",
                "--seed-config=seed-config.yml",
                "--no-interactive", *bootstrap_options, vcstype, buildconf_url,
                util.Interpolate(f"branch=%(prop:branch:-{buildconf_default_branch})s")],
                logfile="bootstrap", haltOnFailure=True),
            util.ShellArg(command=[
                ".autoproj/bin/autoproj", "plugin", "install", "autoproj-ci", *autoproj_ci_args],
                logfile="plugins", haltOnFailure=True),
            util.ShellArg(
                command=[".autoproj/bin/autoproj", "test", "default", "on"],
                logfile="enable-tests"),
        ],
        haltOnFailure=True))

def Build(factory):
    p = util.Interpolate('-p%(prop:parallel_build_level:-1)s')

    AutoprojStep(factory, "ci", "build", "--interactive=f", "-k", p,
        "--cache", CACHE_BUILD_DIR, "--cache-ignore", util.Interpolate("%(prop:rebuild)s"),
        env={'AUTOBUILD_CACHE_DIR': CACHE_IMPORT_DIR},
        name="Building the workspace")
    AutoprojStep(factory, "ci", "cache-push", "--interactive=f", CACHE_BUILD_DIR, "--force", util.Interpolate("%(prop:rebuild)s"),
        name="Pushing to the build cache",
        env={'AUTOBUILD_CACHE_DIR': CACHE_IMPORT_DIR},
        alwaysRun=True)

def BuildReport(factory):
    AutoprojStep(factory, "ci", "build-report", "--interactive=f", "buildbot-report",
        name="Generating build report",
        alwaysRun=True)
    factory.addStep(steps.DirectoryUpload(name="Download the generated report",
        workersrc="buildbot-report",
        masterdest=util.Interpolate("build_reports/%(prop:buildername)s-%(prop:buildnumber)s"),
        alwaysRun=True))

def StandardSetup(c, name, buildconf_url,
                  buildconf_default_branch="master",
                  git_credentials={},
                  vcstype="git",
                  autoproj_branch=None,
                  autobuild_branch=None,
                  autoproj_ci_branch=None,
                  seed_config_path=None,
                  flavor="master",
                  import_workers=["import-cache"],
                  build_workers=["build"],
                  parallel_build_level=4,
                  autoproj_url=AUTOPROJ_GIT_URL,
                  autobuild_url=AUTOBUILD_GIT_URL,
                  autoproj_ci_url=AUTOPROJ_CI_GIT_URL):

    import_cache_factory = util.BuildFactory()
    if git_credentials:
        for url in git_credentials:
            GitCredentials(import_cache_factory, url, git_credentials[url])

    Bootstrap(import_cache_factory, buildconf_url,
              buildconf_default_branch=buildconf_default_branch,
              vcstype=vcstype,
              autoproj_branch=autoproj_branch,
              autobuild_branch=autobuild_branch,
              autoproj_ci_branch=autoproj_ci_branch,
              seed_config_path=seed_config_path,
              flavor=flavor,
              autoproj_url=autoproj_url,
              autobuild_url=autobuild_url,
              autoproj_ci_url=autoproj_ci_url)

    Update(import_cache_factory, osdeps=False)
    UpdateImportCache(import_cache_factory)

    c['builders'].append(
        util.BuilderConfig(name=f"{name}-import-cache",
            workernames=import_workers,
            factory=import_cache_factory)
    )

    build_factory = util.BuildFactory()
    if git_credentials:
        for url in git_credentials:
            GitCredentials(build_factory, url, git_credentials[url])

    Bootstrap(build_factory, buildconf_url,
              buildconf_default_branch=buildconf_default_branch,
              vcstype=vcstype,
              autoproj_branch=autoproj_branch,
              autobuild_branch=autobuild_branch,
              autoproj_ci_branch=autoproj_ci_branch,
              seed_config_path=seed_config_path,
              flavor=flavor,
              autoproj_url=autoproj_url,
              autobuild_url=autobuild_url,
              autoproj_ci_url=autoproj_ci_url)

    Update(build_factory)
    Build(build_factory)
    BuildReport(build_factory)

    c['builders'].append(
        util.BuilderConfig(name=f"{name}-build",
        workernames=build_workers,
        factory=build_factory,
        properties={ 'parallel_build_level': parallel_build_level })
    )

    return [import_cache_factory, build_factory]
