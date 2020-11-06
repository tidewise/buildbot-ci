from buildbot.plugins import *
from twisted.internet import defer

import uuid

AUTOPROJ_GIT_URL  = "https://github.com/rock-core/autoproj"
AUTOBUILD_GIT_URL = "https://github.com/rock-core/autobuild"
AUTOPROJ_CI_GIT_URL = "https://github.com/rock-core/autoproj-ci"

CACHE_IMPORT_DIR = "/var/cache/autoproj/import"
cache_import_lock = util.MasterLock("cache-import", maxCount=512)

CACHE_BUILD_BASE_DIR = '/var/cache/autoproj/build'
CACHE_BUILD_DIR = util.Interpolate(f"{CACHE_BUILD_BASE_DIR}/%(prop:build_cache_key:-%(prop:buildername)s)s")

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
        container['resources'] = {
            'requests': {
                'cpu': 1,
                'memory': f"1G"
            }
        }
        container['volumeMounts'] = [
            {
                'name': 'cache-autoproj-import-rw',
                'mountPath': '/var/cache/autoproj/import'
            }
        ]
        spec['tolerations'] = [{
            'key': 'build-role',
            'operator': 'Exists'
        }]
        spec['volumes'] = [
            {
                'name': 'cache-autoproj-import-rw',
                'persistentVolumeClaim': {
                    'claimName': 'cache-autoproj-import-rw'
                }
            }
        ]
        return pod_def

class BuildCacheWorker(BaseWorker):
    @defer.inlineCallbacks
    def getPodSpec(self, build):
        pod_def = yield super().getPodSpec(build)
        spec = pod_def['spec']

        container = spec['containers'][0]
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
        memory_k = int(build.getProperty('memory_per_build_process_G', 1.5) * 1024)

        container = spec['containers'][0]
        container['resources'] = {
            'requests': {
                'cpu': cpu,
                'memory': f"{memory_k * cpu}k"
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
        spec['restartPolicy'] = 'OnFailure'
        spec['volumes'] = [
            {
                'name': 'cache-autoproj-import',
                'persistentVolumeClaim': {
                    'claimName': 'cache-autoproj-import',
                    'readOnly': True
                }
            },
            {
                'name': 'cache-autoproj-build',
                'persistentVolumeClaim': { 'claimName': 'cache-autoproj-build' }
            }
        ]
        return pod_def


def Barrier(factory, name):
    factory.addStep(
        steps.SetProperty(property=f"{name}BarrierReached", value=True, hideStepIf=True)
    )

def hasReachedBarrier(name):
    return lambda step: step.getProperty(f"{name}BarrierReached", default=False)

def AutoprojStep(factory, *args, wrapper=[], name=None, ifReached=None, **kwargs):
    if name is None:
        name = f"autoproj {args[0]}"

    barrierArgs = {}
    if ifReached:
        barrierArgs = { "alwaysRun": True,
                        "doStepIf": hasReachedBarrier(ifReached) }

    factory.addStep(steps.ShellCommand(name=name,
        command=[*wrapper, ".autoproj/bin/autoproj", *args],
        haltOnFailure=True, **barrierArgs, **kwargs))

def Update(factory, osdeps=True, import_timeout=1200):
    osdeps_update = []
    arguments = []

    if osdeps:
        osdeps_update.append(util.ShellArg(
            command=["sudo", "apt-get", "update"], logfile="apt-update"))
    else:
        arguments.append("--no-osdeps")

    Barrier(factory, "update")
    factory.addStep(steps.ShellSequence(
        name="Update",
        commands=[*osdeps_update,
            util.ShellArg(
                command=[".autoproj/bin/autoproj", "update", *arguments,
                    "--bundler=f", "--autoproj=f", "--interactive=f", "-k"],
                logfile="autoproj-update"
            )
        ],
        timeout=import_timeout,
        haltOnFailure=True))

def CleanBuildCache(factory):
    factory.addStep(steps.ShellCommand(
        name="Clean the build cache",
        command=["sh", "-c", util.Interpolate(f"rm -rf \"{CACHE_BUILD_BASE_DIR}/%(prop:target_buildername)s\"/*")]))
    factory.addStep(steps.ShellCommand(
        name="Check result",
        command=["find", util.Interpolate(f"{CACHE_BUILD_BASE_DIR}/%(prop:target_buildername)s")]))

def UpdateImportCache(factory, gem_compile=["ffi"]):
    factory.addStep(steps.ShellCommand(
        name="Fix permissions on /var/cache/autoproj",
        command=["sudo", "chown", "buildbot", "-R", "/var/cache/autoproj"],
        haltOnFailure=True
    ))
    factory.addStep(steps.ShellCommand(
        name="Install gem-compiler to cache the precompiled gems",
        command=[
            ".autoproj/bin/autoproj", "plugin", "install", "gem-compiler",
            "--git", "https://github.com/tidewise/gem-compiler",
            "--branch", "add_artifact_argument"
        ],
        haltOnFailure=True
    ))
    factory.addStep(steps.ShellCommand(
        name="Update the workspace's import cache",
        command=[
            ".autoproj/bin/autoproj", "cache", '--all=f',
            CACHE_IMPORT_DIR, "--interactive=f", "-k",
            "--gems",
            util.Interpolate("--gems-compile-force=%(prop:gems_compile_force:#?|t|f)s"),
            "--gems-compile", gem_compile
        ],
        haltOnFailure=True
    ))

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
              overrides_file_paths=[],
              flavor="master",
              tests=True,
              build_cache_max_size_GB=None,
              autoproj_url=AUTOPROJ_GIT_URL,
              autobuild_url=AUTOBUILD_GIT_URL,
              autoproj_ci_url=AUTOPROJ_CI_GIT_URL):

    if autoproj_branch is None:
        bootstrap_script_url = "https://rock-robotics.org/autoproj_bootstrap"
    else:
        bootstrap_script_url = f"https://raw.githubusercontent.com/rock-core/autoproj/{autoproj_branch}/bin/autoproj_bootstrap"

    if seed_config_path:
        factory.addStep(steps.FileDownload(
            name=f"copy user-provided seed config",
            workerdest="user-seed-config.yml",
            mastersrc=seed_config_path,
            haltOnFailure=True))
    else:
        factory.addStep(steps.StringDownload("{}",
            name="Create empty user seed config file",
            workerdest="user-seed-config.yml",
            haltOnFailure=True))

    factory.addStep(steps.StringDownload(
        util.Interpolate("%(prop:seed_config:-{})s\n"),
        name="Create seed config from properties",
        workerdest="build-properties-seed-config.yml",
        haltOnFailure=True))

    buildbot_seed_config = f"""
import_log_enabled: false
importer_cache_dir: "{CACHE_IMPORT_DIR}"
separate_prefixes: true
ROCK_SELECTED_FLAVOR: {flavor}
    """

    factory.addStep(steps.StringDownload(
        buildbot_seed_config,
        workerdest="buildbot-seed-config.yml",
        name="Create the buildbot seed config file",
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
            gemfile += f"\ngem 'autobuild', git: '{autobuild_url}', branch: '{autobuild_branch}'"

        factory.addStep(steps.StringDownload(gemfile,
            workerdest="Gemfile.buildbot",
            name=f"Setup Gemfile to use autoproj={autoproj_branch} and autobuild={autobuild_branch}"))

    autoproj_ci_args=[]
    if autoproj_ci_branch is not None:
        autoproj_ci_args=["--git", autoproj_ci_url, "--branch", autoproj_ci_branch]

    test_steps=[]
    if tests:
        test_steps=[
            util.ShellArg(
                command=[".autoproj/bin/autoproj", "test", "default", "on"],
                logfile="enable-tests"
            )
        ]

    cache_cleanup_steps=[]
    if build_cache_max_size_GB is not None:
        cache_cleanup_steps=[
            util.ShellArg(
                command=[
                    ".autoproj/bin/autoproj", "ci", "build-cache-cleanup",
                    f"--max-size={build_cache_max_size_GB}",
                    CACHE_BUILD_BASE_DIR
                ],
                logfile="build cache cleanup"
            )
        ]

    bundle_config = util.Interpolate(
        'echo "BUNDLE_JOBS: \"%(prop:parallel_build_level:-1)s\"" >> /home/buildbot/.bundle/config')
    factory.addStep(steps.ShellSequence(
        name="Bootstrap",
        commands=[
            util.ShellArg(command=["cp", "/var/lib/dpkg/status", "dpkg-status.orig"],
                logfile="save the original dpkg status file", haltOnFailure=True),
            util.ShellArg(command=["wget", bootstrap_script_url],
                logfile="download", haltOnFailure=True),
            util.ShellArg(command="mkdir -p /home/buildbot/.bundle", logfile="bundle-config",
                haltOnFailure=True),
            util.ShellArg(command=bundle_config, logfile="bundle-config",
                haltOnFailure=True),
            util.ShellArg(command=[
                util.Interpolate("%(prop:ruby:-ruby)s"), "autoproj_bootstrap",
                "--seed-config=user-seed-config.yml",
                "--seed-config=build-properties-seed-config.yml",
                "--seed-config=buildbot-seed-config.yml",
                "--no-interactive", *bootstrap_options, vcstype, buildconf_url,
                util.Interpolate(f"branch=%(prop:branch:-{buildconf_default_branch})s")],
                logfile="bootstrap", haltOnFailure=True),
            util.ShellArg(command=[
                ".autoproj/bin/autoproj", "plugin", "install", "autoproj-ci", *autoproj_ci_args],
                logfile="plugins", haltOnFailure=True)
        ] + test_steps + cache_cleanup_steps,
        haltOnFailure=True))

    if overrides_file_paths:
        for file in overrides_file_paths:
            factory.addStep(steps.FileDownload(
                name=f"copy user-provided overrides file {file}",
                workerdest=f"autoproj/overrides.d/{file}",
                mastersrc=file,
                haltOnFailure=True))

def Build(factory, tests=True, test_utilities=['omniorb', 'x11'], build_timeout=1200):
    p = util.Interpolate('-p%(prop:parallel_build_level:-1)s')

    Barrier(factory, "build")
    AutoprojStep(factory, "ci", "build", "--interactive=f", "-k", p,
        "--progress=t",
        "--cache", CACHE_BUILD_DIR,
        "--cache-ignore", util.Transform(str.split, util.Interpolate("%(prop:rebuild)s"), " "),
        name="Building the workspace",
        timeout=build_timeout)

    Barrier(factory, "test")
    if tests:
        for utility in test_utilities:
            factory.addStep(steps.FileDownload(name=f"copy {utility} setup script",
                workerdest=f"/buildbot/start-{utility}",
                mastersrc=f"start-{utility}",
                mode=0o755,
                haltOnFailure=True))
            factory.addStep(steps.ShellCommand(name=f"setup {utility} for tests",
                command=[f"/buildbot/start-{utility}"],
                haltOnFailure=True,
                usePTY=True))

        wrapper=[]
        if 'x11' in test_utilities:
            wrapper=['xvfb-run']

        p = util.Interpolate('-p%(prop:parallel_test_level:-1)s')
        AutoprojStep(factory, "ci", "test", "--interactive=f", "-k", p,
            name="Running unit tests", wrapper=wrapper)

        AutoprojStep(factory, "ci", "process-test-results", "--interactive=f",
            util.Interpolate("--xunit-viewer=%(prop:xunit-viewer:-/usr/local/bin/xunit-viewer)s"),
            name="Postprocess test results",
            ifReached="test")

    AutoprojStep(factory, "ci", "cache-push", "--interactive=f", CACHE_BUILD_DIR,
        name="Pushing to the build cache",
        ifReached="build")

class ReportPathRender:
    def __init__(self, prefix, suffix):
        self.prefix = prefix
        self.suffix = suffix

    def getRenderingFor(self, props):
        name = props.getProperty(
            'virtual_builder_name',
            props.getProperty('buildername')
        )
        name = name.replace('/', ':')
        number = props.getProperty('buildnumber')

        return f"{self.prefix}{name}-{number}{self.suffix}"

def BuildReport(factory):
    AutoprojStep(factory, "ci", "create-report", "--interactive=f", "buildbot-report",
        name="Generating report",
        ifReached="update")

    AutoprojStep(factory, "envsh", "--interactive=f",
        name="Regen the env.sh file",
        ifReached="update")

    AutoprojStep(factory, "versions", "--local", "--fingerprint",
            "--interactive=f", '--save=buildbot-report/versions.yml',
        name="Generating versions file",
        ifReached="update")

    vm_uuid = str(uuid.uuid4())
    factory.addStep(steps.StringDownload(vm_uuid,
        workerdest=f"buildbot-report/uuid",
        name=f"Create a UUID file in the report directory to identify the build image",
        alwaysRun=True,
        doStepIf=hasReachedBarrier("update")
    ))

    report_folder = ReportPathRender("build_reports/", "")
    report_tar    = ReportPathRender("build_reports/", ".tar.bz2")

    factory.addStep(steps.ShellCommand(name="Copy the installation manifest",
        command=["cp", ".autoproj/installation-manifest",
                 "buildbot-report/installation-manifest"],
        alwaysRun=True,
        doStepIf=hasReachedBarrier("update")
    ))
    factory.addStep(steps.ShellCommand(name="Copy the env.sh file",
        command=["cp", "env.sh", "buildbot-report/env.sh"],
        alwaysRun=True,
        doStepIf=hasReachedBarrier("update")
    ))
    factory.addStep(steps.ShellCommand(name="Copy the original dpkg status file",
        command=["cp", "dpkg-status.orig", "buildbot-report/dpkg-status.orig"],
        alwaysRun=True,
        doStepIf=hasReachedBarrier("update")
    ))
    factory.addStep(steps.ShellCommand(name="Copy the final dpkg status file",
        command=["cp", "/var/lib/dpkg/status", "buildbot-report/dpkg-status.new"],
        alwaysRun=True,
        doStepIf=hasReachedBarrier("update")
    ))
    factory.addStep(steps.ShellCommand(name="Compress the report directory",
        command=["tar", "cjf", "build_report.tar.bz2", "buildbot-report"],
        alwaysRun=True,
        doStepIf=hasReachedBarrier("update")
    ))
    factory.addStep(steps.FileUpload(name="Download the report",
        workersrc="build_report.tar.bz2",
        masterdest=report_tar,
        alwaysRun=True,
        doStepIf=hasReachedBarrier("update")))
    factory.addStep(steps.MasterShellCommand(name="Create the report directory",
        command=["mkdir", "-p", report_folder],
        alwaysRun=True,
        doStepIf=hasReachedBarrier("update")
    ))
    factory.addStep(steps.MasterShellCommand(name="Extract the report on the master",
        command=["tar", "xjf", report_tar,
                 "-C", report_folder,
                 "--strip-components=1"],
        alwaysRun=True,
        doStepIf=hasReachedBarrier("update")
    ))

def StandardSetup(c, name, buildconf_url,
                  buildconf_default_branch="master",
                  git_credentials={},
                  vcstype="git",
                  autoproj_branch=None,
                  autobuild_branch=None,
                  autoproj_ci_branch=None,
                  seed_config_path=None,
                  overrides_file_paths=[],
                  flavor="master",
                  import_workers=["import-cache"],
                  build_workers=["build"],
                  parallel_build_level=4,
                  parallel_test_level=1,
                  import_timeout=1200,
                  build_timeout=1200,
                  build_cache_max_size_GB=None,
                  import_properties={},
                  build_properties={},
                  properties={},
                  tests=True,
                  test_utilities=['omniorb', 'x11'],
                  gem_compile=["ffi"],
                  autoproj_url=AUTOPROJ_GIT_URL,
                  autobuild_url=AUTOBUILD_GIT_URL,
                  autoproj_ci_url=AUTOPROJ_CI_GIT_URL,
                  builder_locks=[]):

    import_cache_factory = util.BuildFactory()
    if git_credentials:
        for url in git_credentials:
            GitCredentials(import_cache_factory, url, git_credentials[url])

    Bootstrap(import_cache_factory, buildconf_url,
              buildconf_default_branch=buildconf_default_branch,
              vcstype=vcstype,
              tests=tests,
              autoproj_branch=autoproj_branch,
              autobuild_branch=autobuild_branch,
              autoproj_ci_branch=autoproj_ci_branch,
              seed_config_path=seed_config_path,
              overrides_file_paths=overrides_file_paths,
              flavor=flavor,
              autoproj_url=autoproj_url,
              autobuild_url=autobuild_url,
              autoproj_ci_url=autoproj_ci_url)

    Update(import_cache_factory, import_timeout=import_timeout)
    UpdateImportCache(import_cache_factory, gem_compile=gem_compile)

    import_properties.update(properties)
    c['builders'].append(
        util.BuilderConfig(name=f"{name}-import-cache",
            workernames=import_workers,
            factory=import_cache_factory,
            properties=import_properties,
            locks=[cache_import_lock.access('exclusive')])
    )

    build_factory = util.BuildFactory()
    if git_credentials:
        for url in git_credentials:
            GitCredentials(build_factory, url, git_credentials[url])

    Bootstrap(build_factory, buildconf_url,
              buildconf_default_branch=buildconf_default_branch,
              vcstype=vcstype,
              tests=tests,
              autoproj_branch=autoproj_branch,
              autobuild_branch=autobuild_branch,
              autoproj_ci_branch=autoproj_ci_branch,
              seed_config_path=seed_config_path,
              overrides_file_paths=overrides_file_paths,
              flavor=flavor,
              build_cache_max_size_GB=build_cache_max_size_GB,
              autoproj_url=autoproj_url,
              autobuild_url=autobuild_url,
              autoproj_ci_url=autoproj_ci_url)

    Update(build_factory, import_timeout=import_timeout)
    Build(build_factory, build_timeout=build_timeout,
          tests=tests, test_utilities=test_utilities)
    BuildReport(build_factory)

    build_properties.update({
        'parallel_build_level': parallel_build_level,
        'parallel_test_level': parallel_test_level
    })
    build_properties.update(properties)
    c['builders'].append(
        util.BuilderConfig(name=f"{name}-build",
            workernames=build_workers,
            factory=build_factory,
            properties=build_properties,
            locks=[cache_import_lock.access('counting')] + builder_locks
        )
    )

    return (import_cache_factory, build_factory)

def BuildArtifacts(factory, workspace=None):
    workspaceArgs = []
    if workspace is not None:
        workspaceArgs = ['--workspace', workspace]

    AutoprojStep(factory, "ci", "rebuild-root", 'buildbot-report/',
            CACHE_BUILD_DIR, "build_artifacts.tar", *workspaceArgs,
        name="Create the build artifacts tarball",
        ifReached="test")

    factory.addStep(steps.ShellCommand(name="Add the gems to the artifacts",
        command=[
            "tar", "rf", "build_artifacts.tar", "-C", "/",
             "--owner=root", "--group=root",
             "--exclude", "*.o",
             "--exclude", "*.a",
             "--exclude", "home/buildbot/.local/share/autoproj/gems/ruby/*/gems/*/test",
             "--exclude", "home/buildbot/.local/share/autoproj/gems/ruby/*/gems/*/spec",
             "--exclude", "*.gem",
             "/home/buildbot/.local/share/autoproj/gems"
        ],
        alwaysRun=True,
        doStepIf=hasReachedBarrier("test")
    ))

    factory.addStep(steps.ShellCommand(name="Compress the artifacts",
        command=["gzip", "build_artifacts.tar"],
        alwaysRun=True,
        doStepIf=hasReachedBarrier("test")
    ))

    artifacts_tar    = ReportPathRender("build_artifacts/", ".tar.gz")
    factory.addStep(steps.FileUpload(name="Download the build artifacts",
        workersrc="build_artifacts.tar.gz",
        masterdest=artifacts_tar,
        alwaysRun=True,
        doStepIf=hasReachedBarrier("test")))

    artifacts_dpkg_orig = ReportPathRender("build_artifacts/", ".dpkg-orig")
    artifacts_dpkg_new = ReportPathRender("build_artifacts/", ".dpkg-new")
    factory.addStep(steps.FileUpload(name="Download the original dpkg list",
        workersrc="buildbot-report/dpkg-status.orig",
        masterdest=artifacts_dpkg_orig,
        alwaysRun=True,
        doStepIf=hasReachedBarrier("test")))
    factory.addStep(steps.FileUpload(name="Download the new dpkg list",
        workersrc="buildbot-report/dpkg-status.new",
        masterdest=artifacts_dpkg_new,
        alwaysRun=True,
        doStepIf=hasReachedBarrier("test")))

