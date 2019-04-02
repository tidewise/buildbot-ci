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
    app.add_url_rule("/index.html", "index", lambda: main(app))
    return app


def main(app):
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


def compute_build_info(builds, builders):
    info = []
    for build in builds:
        for builder in builders:
            if build['builderid'] == builder['builderid']:
                name = f"{builder['name']}-{build['buildid']}"
                report = package_info_for(name)
                build_info = {
                    'id': build['buildid'],
                    'name': name,
                    'builder_name': builder['name'],
                    'report': report
                }
                if not report is None:
                    info.append(build_info)

    return info

def package_info_for(buildname):
    path = Path(f'build_reports/{buildname}/report.json')
    if not path.is_file():
        return

    with open(path) as f:
        info = json.loads(f.read())

    packages = []
    for pkg_name in info['packages']:
        pkg = info['packages'][pkg_name]
        pkg['name'] = pkg_name
        pkg['status'] = compute_package_status(pkg)
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
