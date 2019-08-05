import os
import json

from flask import Flask
from flask import render_template
from pathlib import Path

from buildbot.process.results import statusToString

def Create(name):
    app = Flask(name, root_path=os.path.dirname(__file__))
    # this allows to work on the template without having to restart Buildbot
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.add_url_rule("/index.html", "index", lambda: dashboard(app))
    app.add_url_rule("/logs/<buildname>/<path:packagename>/<logtype>", "log_get", log_get)
    return app


def dashboard(app):
    # This code fetches build data from the data api, and give it to the
    # template
    builders = app.buildbot_api.dataGet("/builders")
    builds   = app.buildbot_api.dataGet("/builds", limit=20)

    # properties are actually not used in the template example, but this is
    # how you get more properties
    for build in builds:
        build['properties'] = app.buildbot_api.dataGet(
            ("builds", build['buildid'], "properties"))

    builds = compute_build_info(builds, builders)
    return render_template('dashboard.html', builds=builds)

def log_get(buildname, packagename, logtype):
    try:
        build_reports = Path("build_reports").resolve(strict=True)
        path = build_reports / buildname / 'logs' / f"{packagename}-{logtype}.log"
        path = path.resolve(strict=True)
        # Make sure our arguments are not trying to get us out of build_reports/
        # This raises if `path` does not start with `build_reports`
        path.relative_to(build_reports)

        log_contents = path.read_text()
        return render_template('log.html',
            buildname=buildname, packagename=packagename,
            logtype=logtype, log_contents=log_contents)
    except Exception as error:
        return render_template('log.html',
            error=error,
            buildname=buildname, packagename=packagename,
            logtype=logtype, log_contents=log_contents)




def compute_build_info(builds, builders):
    info = []
    for build in builds:
        for builder in builders:
            if build['builderid'] == builder['builderid']:
                name = f"{builder['name']}-{build['buildid']}"
                report = package_info_for(name)
                if not report is None:
                    summary = build_summary(report)
                    build_info = {
                        'id': build['buildid'],
                        'name': name,
                        'builder_id': build['builderid'],
                        'builder_name': builder['name'],
                        'summary': summary,
                        'report': report
                    }
                    info.append(build_info)

    return info

def package_info_for(buildname):
    basedir = Path(f'build_reports/{buildname}')
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
        packages.append(pkg)

    status_order = {
        'failed': 0,
        'success': 1,
        'cached': 2,
        'skipped': 3
    }
    packages.sort(key=lambda pkg: [status_order[pkg['status'][0]['text']], pkg['name']])
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
    return min(status_order[s['text']] for s in status)

def compute_package_status(pkg):
    if pkg['cached']:
        return [{'badge': 'SKIPPED', 'text': 'cached'}]
    elif pkg['failed']:
        return [{'badge': 'FAILURE', 'text': 'failed'}]
    elif pkg['built']:
        return [{'badge': 'SUCCESS', 'text': 'success'}]
    else:
        return [{'badge': 'SKIPPED', 'text': 'skipped'}]

def compute_package_logs(pkg, basedir):
    logs = {}
    pkg_elements = pkg['name'].split('/')
    basename = pkg_elements.pop()
    logdir = basedir.joinpath('logs', *pkg_elements)
    slice_start = len(basename) + 1
    for path in logdir.iterdir():
        if path.is_file() and path.match(f"{basename}-*.log"):
            slice_end = len(path.name) - 4
            log_type = path.name[slice_start:slice_end]
            logs[log_type] = path

    return logs
