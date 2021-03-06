#!/usr/bin/env python
# encoding=utf-8
from __future__ import unicode_literals

import argparse
import datetime
from io import open
import os
import shutil
import subprocess
import yaml

CHANGELOG_FILE = 'CHANGELOG.md'


def get_git_root():
    return subprocess.check_output("git rev-parse --show-toplevel", shell=True).decode('utf-8').strip()


def get_author():
    return subprocess.check_output("git config user.name", shell=True).decode('utf-8').strip()


def move_unreleased_changelogs(version):
    unreleased_folder = os.path.join(get_git_root(), 'changelogs', 'unreleased')
    released_version_folder = os.path.join(get_git_root(), 'changelogs', 'released', version)
    if os.path.exists(released_version_folder):
        print("Changelog for this version already exists.")
        exit(1)
    os.makedirs(released_version_folder)
    files_to_move = list(filter(lambda x: x[-4:] == '.yml', os.listdir(unreleased_folder)))
    if len(files_to_move) == 0:
        print("There is no unreleased changes.")
        exit(1)
    for yml_file in files_to_move:
        shutil.move(os.path.join(unreleased_folder, yml_file), released_version_folder)
    write_release_info(released_version_folder)
    subprocess.call("git add {PATH}".format(PATH=released_version_folder), shell=True)


def write_release_info(released_version_folder):
    if os.path.exists(os.path.join(released_version_folder, 'release-info')):
        print("Release-info already exists and will be erased")
    info = {
        'date': datetime.date.today().isoformat(),
        'released_by': get_author()
    }
    with open(os.path.join(released_version_folder, 'release-info'), 'w') as f:
        yaml.safe_dump(info,
                       f,
                       allow_unicode=True,
                       default_flow_style=False,
                       encoding=None)


def get_version_folders():
    def version_strings_key(version):
        return tuple(map(int, version[1:].split('.')))

    released_folder = os.path.join(get_git_root(), 'changelogs', 'released')
    version_folders = []
    for folder in os.listdir(released_folder):
        if os.path.isdir(os.path.join(released_folder, folder)):
            try:
                check_version(folder)
                version_folders.append(folder)
            except CheckVersionException:
                print("{FOLDER} have unsupported format. Skipping.".format(FOLDER=folder))
        else:
            print("{FOLDER} is not directory. Skipping.".format(FOLDER=folder))
    version_folders = sorted(version_folders, key=version_strings_key, reverse=True)
    return version_folders


def get_version_changes(version):
    changes = {}
    version_folder = os.path.join(get_git_root(), 'changelogs', 'released', version)
    yml_files = filter(lambda x: x[-4:] == '.yml', os.listdir(version_folder))
    for file in yml_files:
        with open(os.path.join(version_folder, file), 'r') as f:
            entry = yaml.load(f)
        if entry['author'] not in changes:
            changes[entry['author']] = []
        changes[entry['author']].append('- ' + entry['title'] + '\n')
    return changes


def get_release_info(version):
    info_file = os.path.join(get_git_root(), 'changelogs', 'released', version, 'release-info')
    if not os.path.exists(info_file):
        return dict()
    with open(info_file, 'r') as f:
        return yaml.load(f)


def build_changelog():
    result = list()
    result.append("**Note:** This file is automatically generated. Use changelog_helper to add your own entry\n")
    result.append("\n")
    for version in get_version_folders():
        release_info = get_release_info(version)
        result.append(
            "## Version {VERSION} ({DATE})\n".format(VERSION=version[1:], DATE=release_info.get('date', '')))
        changes = get_version_changes(version)
        for author in changes:
            result.append("*@{AUTHOR}*\n".format(AUTHOR=author))
            result += changes[author]
        result.append("\n")
    archive_changes_file = os.path.join(get_git_root(), 'changelogs', 'archive.md')
    if os.path.exists(archive_changes_file):
        with open(archive_changes_file, 'r') as f:
            for line in f:
                result.append(line)
    return result


def check_version(version_string):
    if version_string[0] != 'v':
        raise CheckVersionException("Version should start with 'v', like v1.2.19")
    if len(version_string) < 2:
        raise CheckVersionException("You should provide version number, like v1.2.19")
    try:
        tuple(map(int, version_string[1:].split('.')))
    except ValueError:
        raise CheckVersionException("Version can contain only numbers divided by dots, like v1.2.19")


class CheckVersionException(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description='Generate CHANGELOG.md file from changelog yml files.')
    parser.add_argument('version', help="New version, in format like v5.6.7", nargs='?', default='v')
    parser.add_argument('--rebuild', action='store_true')

    app_args = parser.parse_args()

    if not app_args.rebuild:
        try:
            check_version(app_args.version)
        except CheckVersionException as e:
            print(e)
            exit(1)
        move_unreleased_changelogs(app_args.version)

    changelog = build_changelog()

    with open(os.path.join(get_git_root(), CHANGELOG_FILE), 'w', encoding='utf-8') as changes_md:
        changes_md.writelines(changelog)


if __name__ == '__main__':
    main()
