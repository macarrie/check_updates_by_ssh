#!/usr/bin/env python

import os
import sys

try:
    import lib_shinken_plugin.python.main as lib
except ImportError as err:
    print "<span style=\"color:#A9A9A9;font-weight: bold;\">[UNKNOWN]</span> Unable to load lib_shinken_plugin."
    sys.exit(3)

VERSION = "0.1"
DEFAULT_WARNING = 10
DEFAULT_CRITICAL = 15

STATUS = 0


def get_package_manager(client):
    package_managers = [
            "yum",
            "apt",
            "portmaster",
            "pkg",
            ]

    for pm in package_managers:
        stdin, stdout, stderr = client.exec_command('which %s' % pm)
        if stdout.channel.recv_exit_status() == 0:
            return pm


def count_yum_updates(security_only = False):
    check_cmd = 'yum check-update'
    count_cmd = 'yum list updates'

    if security_only:
        check_cmd = 'yum --security check-update'
        count_cmd = 'yum --security list updates'

    stdin, stdout, stderr = client.exec_command("LC_ALL=C %s" % check_cmd)
    if stdout.channel.recv_exit_status() == 0:
        return 0

    stdin, stdout, stderr = client.exec_command("LC_ALL=C %s" % count_cmd)
    start_count = False
    updates_count = 0
    for line in stdout:
        line = line.strip()
        if line.startswith('Available Upgrades') or line.startswith("Updated Packages"):
            start_count = True
            continue

        if start_count:
            updates_count += 1

    if not start_count:
        lib.exit_with_status(lib.UNKNOWN, "Cannot parse yum output to count updates")

    return updates_count


def count_apt_updates(security_only = False):
    count_cmd = 'aptitude search "~U"'

    if security_only:
        count_cmd = 'aptitude search "~U" -F "%p %O" | grep -- "-Security"'

    stdin, stdout, stderr = client.exec_command('LC_ALL=C %s' % count_cmd)
    updates_count = 0
    for line in stdout:
        line = line.strip()
        updates_count += 1

    return updates_count


def count_portmaster_updates(security_only = False):
    if security_only:
        lib.exit_with_status(lib.UNKNOWN, "Portmaster security updates count not supported yet")

    stdin, stdout, stderr = client.exec_command('LC_ALL=C portmaster -L -P')
    updates_count = 0
    for line in stdout:
        line = line.strip()

        if "New version available" in line:
            updates_count += 1

    return updates_count


def count_pkg_updates(security_only = False):
    lib.exit_with_status(lib.UNKNOWN, "freebsd pkg updates not yet implemented")



if __name__ == '__main__':
    parser = lib.get_ssh_parser(VERSION)
    parser.add_argument('-s', '--security', dest="security", type=int, default=0, help='Count security updates only. Default: 0')

    # Ok first job : parse args
    opts = parser.parse_args()

    port = opts.port
    hostname = opts.hostname

    lib.check_ssh_opts(opts)

    ssh_key_file = opts.ssh_key_file or os.path.expanduser('~/.ssh/id_rsa')
    user = opts.user or 'shinken'
    passphrase = opts.passphrase or ''
    security_only = (opts.security == 1) or False

    # Try to get numeric warning/critical values
    s_warning = int(opts.warning or DEFAULT_WARNING)
    s_critical = int(opts.critical or DEFAULT_CRITICAL)

    # Ok now connect, and try to get values for memory
    client = lib.ssh_connect(hostname, port, ssh_key_file, passphrase, user)

    pending_updates = 0

    package_manager = get_package_manager(client)
    if not package_manager:
        lib.exit_with_status(lib.UNKNOWN, "Cannot find package manager or package manager unsupported")

    if package_manager == "yum":
        pending_updates = count_yum_updates(security_only)

    if package_manager == "apt":
        pending_updates = count_apt_updates(security_only)

    if package_manager == "portmaster":
        pending_updates = count_portmaster_updates(security_only)

    if package_manager == "pkg":
        pending_updates = count_pkg_updates(security_only)

    lib.add_perfdata("pending_updates", pending_updates, s_warning, s_critical)
    pm_message = "Package manager detected: '%s'" % package_manager

    if pending_updates > s_critical:
        lib.exit_with_status(lib.CRITICAL, "%d pending updates" % pending_updates, pm_message)
    if pending_updates > s_warning:
        lib.exit_with_status(lib.WARNING, "%d pending updates" % pending_updates, pm_message)

    if pending_updates == 0:
        lib.exit_with_status(lib.OK, "No pending updates", pm_message)
    else:
        lib.exit_with_status(lib.OK, "%d pending updates" % pending_updates, pm_message)
