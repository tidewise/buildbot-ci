import os
import json

from flask import Flask
from flask import render_template
from pathlib import Path

from buildbot.process.results import statusToString

STATUS_ORDER = {
    'import failed': 0,
    'build failed': 1,
    'test failed': 2,
    'cached: test failed': 3,
    'test': 4,
    'build': 5,
    'import': 6,
    'cached: test': 7,
    'cached: build': 8,
    'unknown': 9
}

def Create(name):
    app = Flask(name, root_path=os.path.dirname(__file__))
    # this allows to work on the template without having to restart Buildbot
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.add_url_rule("/index.html", "index", lambda: dashboard(app))
    app.add_url_rule("/logs/<reports_name>/<path:packagename>/<logtype>", "log_get", log_get)
    app.add_url_rule("/test-results/<reports_name>/<path:packagename>", "test_results_get", test_results_get)
    return app


def dashboard(app):
    # This code fetches build data from the data api, and give it to the
    # template
    builders = app.buildbot_api.dataGet("/builders")
    builds   = app.buildbot_api.dataGet("/builds", limit=20, order=["-buildid"])

    # properties are actually not used in the template example, but this is
    # how you get more properties
    for build in builds:
        build['properties'] = app.buildbot_api.dataGet(
            ("builds", build['buildid'], "properties"))

    builds = compute_build_info(builds, builders)
    toplevel_builds = compute_toplevel_builds(builds)
    return render_template('dashboard.html', builds=builds, toplevel_builds=toplevel_builds)

def test_results_get(reports_name, packagename):
    build_reports = Path("build_reports").resolve(strict=True)
    path = build_reports / reports_name / 'logs' / 'test-results' / f"{packagename}.html"
    path = path.resolve(strict=True)
    # Make sure our arguments are not trying to get us out of build_reports/
    # This raises if `path` does not start with `build_reports`
    path.relative_to(build_reports)

    contents = path.read_text();
    return contents
    #contents = path.read_text();
    #return render_template('tests.html', contents=contents)

def log_get(reports_name, packagename, logtype):
    build_reports = Path("build_reports").resolve(strict=True)
    path = build_reports / reports_name / 'logs' / f"{packagename}-{logtype}.log"
    path = path.resolve(strict=True)
    # Make sure our arguments are not trying to get us out of build_reports/
    # This raises if `path` does not start with `build_reports`
    path.relative_to(build_reports)

    log_contents = path.read_text()
    return render_template('log.html',
        reports_name=reports_name, packagename=packagename,
        logtype=logtype, log_contents=log_contents)

def compute_build_info(builds, builders):
    info = []
    for build in builds:
        for builder in builders:
            if build['builderid'] == builder['builderid']:
                buildername = builder.get(
                    'virtual_builder_name',
                    builder.get('name')
                )
                name = f"{buildername}-{build['number']}"
                reports_name = name.replace('/', ':')

                report = package_info_for(reports_name)
                if not report is None:
                    summary = build_summary(report)
                    build_info = {
                        'id': build['buildid'],
                        'name': name,
                        'reports_name': reports_name,
                        'builder_id': build['builderid'],
                        'build_number': build['number'],
                        'builder_name': buildername,
                        'summary': summary,
                        'report': report
                    }
                    build_info['state'] = compute_build_state(build_info)
                    info.append(build_info)

    return info

def compute_build_state(summary):
    package_info = summary['report']['packages']
    if package_info:
        # report's packages are sorted by order of status priority
        return package_info[0]['status'][0]
    else:
        return { 'text': 'success', 'badge': 'SUCCESS' }

def compute_toplevel_builds(build_info):
    info = {}
    for build in build_info:
        builder_name = build['builder_name']
        if builder_name in info:
            info[builder_name].append(build)
        else:
            info[builder_name] = [build]

    return info

def package_info_for(reports_name):
    basedir = Path(f'build_reports/{reports_name}')
    report_path = basedir / 'report.json'
    if not report_path.is_file():
        return

    with open(report_path) as f:
        info = json.loads(f.read())

    packages = []
    for pkg_name in info['packages']:
        pkg = info['packages'][pkg_name]
        pkg['name'] = pkg_name
        pkg['status'] = compute_package_status(pkg)
        pkg['logs'] = compute_package_logs(pkg, basedir)
        pkg['tests'] = compute_package_tests(pkg, basedir)
        packages.append(pkg)

    packages.sort(key=lambda pkg: [STATUS_ORDER[pkg['status'][0]['text']], pkg['name']])
    info['packages'] = packages
    return info

def build_summary(report):
    results = {}
    for pkg in report['packages']:
        for status in pkg['status']:
            if status['text'] in results:
                results[status['text']]['count'] += 1
            else:
                results[status['text']] = {
                    'badge': status['badge'],
                    'text': status['text'],
                    'count': 1
                }

    return results.values()

def status_order(status):
    return min(STATUS_ORDER[s['text']] for s in status)

def compute_package_main_state(pkg):
    for phase in ['test', 'build', 'import']:
        if phase in pkg and pkg[phase]['invoked']:
            return phase

def compute_package_status(pkg):
    phase = compute_package_main_state(pkg)
    if not phase:
        return [{'badge': 'SKIPPED', 'text': "unknown"}]

    cached = ""
    if pkg[phase]['cached']:
        cached = "cached: "

    if pkg[phase]['success']:
        status = [{'badge': 'SUCCESS', 'text': f"{cached}{phase}"}]
    else:
        status = [{'badge': 'FAILURE', 'text': f"{cached}{phase} failed"}]

    if not 'test' in pkg:
        status.extend([{'badge': 'WARNINGS', 'text': "no tests"}])

    return status


def compute_package_logs(pkg, basedir):
    logs = {}
    pkg_elements = pkg['name'].split('/')
    basename = pkg_elements.pop()
    logdir = basedir.joinpath('logs', *pkg_elements)
    if not logdir.exists():
        return logs

    slice_start = len(basename) + 1
    for path in logdir.iterdir():
        if path.is_file() and path.match(f"{basename}-*.log"):
            slice_end = len(path.name) - 4
            log_type = path.name[slice_start:slice_end]
            logs[log_type] = path

    return logs

def compute_package_tests(pkg, basedir):
    logs = {}
    pkg_elements = pkg['name'].split('/')
    basename = pkg_elements.pop()
    xunit_html = basedir.joinpath('logs', 'test-results', *pkg_elements, f"{basename}.html")
    if xunit_html.is_file():
        return [{ 'path': xunit_html, 'type': 'xunit' }]

    return []
