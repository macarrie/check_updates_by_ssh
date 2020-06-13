#!/usr/bin/env python

# VERSION 09-20-2017

'''
 This script is a check for lookup at memory consumption over ssh without
 having an agent on the other side
'''
import os
import sys
import optparse
import base64
import subprocess

# Ok try to load our directory to load the plugin utils.
my_dir = os.path.dirname(__file__)
sys.path.insert(0, my_dir)

try:
    import schecks
except ImportError:
    print "<span style=\"color:#A9A9A9;font-weight: bold;\">[UNKNOWN]</span> This plugin needs the local schecks.py lib. Please install it."
    sys.exit(3)

VERSION = "0.1"
DEFAULT_WARNING = '75%'
DEFAULT_CRITICAL = '90%'
MOUNTS = None
EXCLUDE = None
UNITS = {'B' : 0,
         'KB': 1,
         'MB': 2,
         'GB': 3,
         'TB': 4
         }
WARNING_NB = 0
CRITICAL_NB = 0


def convert_to(unit, value):
    power = 0
    if unit in UNITS:
        power = UNITS[unit]
    return float(value) / (1024 ** power)


def get_package_manager(client):
    stdin, stdout, stderr = client.exec_command('which apt')


parser = optparse.OptionParser("%prog [options]", version="%prog " + VERSION)
parser.add_option('-H', '--hostname', dest="hostname", help='Hostname to connect to')
parser.add_option('-i', '--ssh-key', dest="ssh_key_file", help='SSH key file to use. By default will take ~/.ssh/id_rsa.')
parser.add_option('-p', '--port', dest="port", type="int", default=22, help='SSH port to connect to. Default : 22')
parser.add_option('-u', '--user', dest="user", help='remote use to use. By default shinken.')
parser.add_option('-P', '--passphrase', dest="passphrase", help='SSH key passphrase. By default will use void')
parser.add_option('-w', '--warning', dest="warning", help='Warning value for physical used memory. In percent. Default : 75%')
parser.add_option('-c', '--critical', dest="critical", help='Critical value for physical used memory. In percent. Must be superior to warning value. Default : 90%')

if __name__ == '__main__':
    # Ok first job : parse args
    opts, args = parser.parse_args()
    if args:
        parser.error("Does not accept any argument.")

    port = opts.port
    hostname = opts.hostname
    if not hostname:
        print "<span style=\"color:#A9A9A9;font-weight: bold;\">[ERROR]</span> Hostname parameter (-H) is mandatory"
        sys.exit(3)

    ssh_key_file = opts.ssh_key_file or os.path.expanduser('~/.ssh/id_rsa')
    user = opts.user or 'shinken'
    passphrase = opts.passphrase or ''

    # Try to get numeic warning/critical values
    s_warning = opts.warning or DEFAULT_WARNING
    s_critical = opts.critical or DEFAULT_CRITICAL
    warning, critical = schecks.get_warn_crit(s_warning, s_critical)

    # Ok now connect, and try to get values for memory
    client = schecks.connect(hostname, port, ssh_key_file, passphrase, user)
    package_manager = get_package_manager(client)

    # Maybe we failed at getting data
    if not package_manager:
        print "<span style=\"color:#A9A9A9;font-weight: bold;\">[UNKNOWN]</span> Cannot find package manager type"
        sys.exit(2)

    perfdata = ''
    status = 0  # all is green until it is no more ok :)
    all_volumes = []
    bad_volumes = []
    for (mount, df) in dfs.iteritems():
    
        size = convert_to(s_unit, df['size'])
        used = convert_to(s_unit, df['used'])
        used_pct = df['used_pct']
        fs = df['fs']
        
        # Let first dump the perfdata
        _size_warn = convert_to(s_unit, df['size'] * float(warning) / 100)
        _size_crit = convert_to(s_unit, df['size'] * float(critical) / 100)
        perfdata += '"%s_used_pct"=%s%%;%s%%;%s%%;0%%;100%% "%s_used"=%s%s;%s;%s;0;%s "%s_total"=%s%s;;;; ' % (mount, used_pct, warning, critical, mount, used, s_unit, _size_warn, _size_crit, size, mount, size, s_unit)
        
        all_volumes.append((fs, mount, used_pct, used, size))
        
        # And compare to limits
        if used_pct >= critical:
            status = 2
            bad_volumes.append((fs, mount, used_pct, used, size))
            CRITICAL_NB += 1
        elif used_pct >= warning:
            if status == 0:
                status = 1
            bad_volumes.append((fs, mount, used_pct, used, size))
            WARNING_NB += 1

    # Make the tab
    all_volumes.sort(reverse=True)
    bad_volumes.sort(reverse=True)
    table = "<style type=\"text/css\"> .disks-table, .disks-table td, .disks-table th { border: 1px solid #000000 !important; border-collapse: collapse !important; color: #000000 !important; } .disks-table { width: 100% !important; } .disks-table-th { background-color: #E8E7E7 !important; width: auto !important; max-width: 20% !important; padding: 2px !important; word-break: break-word !important; background-color: #E8E7E7 !important; text-align: center !important;}"
    table += ".disks-table-td { padding: 2px !important; width: auto !important; max-width: 20% !important; font-weight: normal !important; word-break: break-word !important; background-color: #FFFFFF !important; } .disks-host-command { font-style: italic !important; color: #7F7F7F !important; } .disks-table-center { text-align: center; } </style>"
    
    # OK status
    if status == 0:
        print "<span style=\"color:#2a9a3d;font-weight: bold;\">[OK]</span> All disks are in the limits. <br/>"
        print ""
        print "%s<br/>Disks details :<br/> <table class=\"disks-table\"><tr><th class=\"disks-table-th\">Filesystem</th><th class=\"disks-table-th\">Mounted on</th><th class=\"disks-table-th\">Usage</th><th class=\"disks-table-th\">Used</th><th class=\"disks-table-th\">Total</th></tr>" % table
        for (fs, mount, used_pct, used, size) in all_volumes:
            print " <tr> <td class=\"disks-table-td\">%s</td> <td class=\"disks-table-td\">%s</td> <td class=\"disks-table-td\">%d%%</td><td class=\"disks-table-td\">%.1f%s</td><td class=\"disks-table-td\">%.1f%s</td></tr>" % (
                fs, mount, used_pct, used, s_unit, size, s_unit)
        print "</table><br> | %s" % (perfdata)
        sys.exit(0)

    # Warning status
    if status == 1:
        if WARNING_NB > 1:
            print "<span style=\"color:#e48c19;font-weight: bold;\">[WARNING]</span> %s disks use more than %s%% of their total disk space :<br/>" % (WARNING_NB, warning),
        else:
            print "<span style=\"color:#e48c19;font-weight: bold;\">[WARNING]</span> %s disk uses more than %s%% of his total disk space :<br/>" % (WARNING_NB, warning),
        for (fs, mount, used_pct, used, size) in bad_volumes:
            schecks.printf("<li><span style=\"font-weight: bold;\">%s</span> mounted on <span style=\"font-weight: bold;\">%s</span> with %d%% of usage</li>", fs, mount, used_pct)
        print ""
        print "%s<br/>More than %s%% of total disk space used :<br/> <table class=\"disks-table\"><tr><th class=\"disks-table-th\">Filesystem</th><th class=\"disks-table-th\">Mounted on</th><th class=\"disks-table-th\">Usage</th><th class=\"disks-table-th\">Used</th><th class=\"disks-table-th\">Total</th></tr>" % (
            table, warning)
        for (fs, mount, used_pct, used, size) in bad_volumes:
            print " <tr> <td class=\"disks-table-td\">%s</td> <td class=\"disks-table-td\">%s</td> <td class=\"disks-table-td\">%d%%</td><td class=\"disks-table-td\">%.1f%s</td><td class=\"disks-table-td\">%.1f%s</td></tr>" % (
                fs, mount, used_pct, used, s_unit, size, s_unit)
        print "</table><br> | %s" % (perfdata)
        sys.exit(1)

    # Critical status
    if status == 2:
        if CRITICAL_NB > 1:
            print "<span style=\"color:#dc2020;font-weight: bold;\">[CRITICAL]</span> %s disks use more than %s%% of their total disk space" % (CRITICAL_NB, critical),
        else:
            print "<span style=\"color:#dc2020;font-weight: bold;\">[CRITICAL]</span> %s disk uses more than %s%% of his total disk space" % (CRITICAL_NB, critical),
        # If there is at least 1 disk using more than warning but less than critical we print it too
        if WARNING_NB > 0 and WARNING_NB != 1:
            print ", %s use more than %s%%.<br>" % (WARNING_NB, warning),
        elif WARNING_NB == 1:
            print ", %s uses more than %s%%.<br>" % (WARNING_NB, warning),
        else:
            print ".<br>",
        for (fs, mount, used_pct, used, size) in bad_volumes:
            schecks.printf("<li><span style=\"font-weight: bold;\">%s</span> mounted on <span style=\"font-weight: bold;\">%s</span> with %d%% of usage</li>", fs, mount, used_pct)
        print ""
        print "%s<br/>More than %s%% of total disk space used :<br/> <table class=\"disks-table\"><tr><th class=\"disks-table-th\">Filesystem</th><th class=\"disks-table-th\">Mounted on</th><th class=\"disks-table-th\">Usage</th><th class=\"disks-table-th\">Used</th><th class=\"disks-table-th\">Total</th></tr>" % (
            table, critical)
        for (fs, mount, used_pct, used, size) in bad_volumes:
            if used_pct >= critical:
                print " <tr> <td class=\"disks-table-td\">%s</td> <td class=\"disks-table-td\">%s</td> <td class=\"disks-table-td\">%d%%</td><td class=\"disks-table-td\">%.1f%s</td><td class=\"disks-table-td\">%.1f%s</td></tr>" % (
                    fs, mount, used_pct, used, s_unit, size, s_unit)
        print "</table><br><br>"
        if WARNING_NB > 0:
            print "More than %s%% of total disk space used :<br/> <table class=\"disks-table\"><tr><th class=\"disks-table-th\">Filesystem</th><th class=\"disks-table-th\">Mounted on</th><th class=\"disks-table-th\">Usage</th><th class=\"disks-table-th\">Used</th><th class=\"disks-table-th\">Total</th></tr><tr>" % (
                warning)
            for (fs, mount, used_pct, used, size) in bad_volumes:
                if used_pct < critical:
                    print " <tr> <td class=\"disks-table-td\">%s</td> <td class=\"disks-table-td\">%s</td> <td class=\"disks-table-td\">%d%%</td><td class=\"disks-table-td\">%.1f%s</td><td class=\"disks-table-td\">%.1f%s</td></tr>" % (
                        fs, mount, used_pct, used, s_unit, size, s_unit)
            print "</table><br><br>"
        print " | %s" % (perfdata)
        sys.exit(2)
