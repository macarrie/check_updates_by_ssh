import argparse
import paramiko
import os
import sys


OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3

perfdata = []

def get_ssh_parser(version = ""):
    parser = argparse.ArgumentParser(
            "%prog [options]", version="%prog " + str(version)
            )
    parser.add_argument('-H', '--hostname', dest="hostname", help='Hostname to connect to')
    parser.add_argument('-i', '--ssh-key', dest="ssh_key_file", help='SSH key file to use. By default will take ~/.ssh/id_rsa.')
    parser.add_argument('-p', '--port', dest="port", type=int, default=22, help='SSH port to connect to. Default : 22')
    parser.add_argument('-u', '--user', dest="user", help='remote user to use. By default shinken.')
    parser.add_argument('-P', '--passphrase', dest="passphrase", help='SSH key passphrase. By default will use void')
    parser.add_argument('-w', '--warning', dest="warning", help='Warning threshold')
    parser.add_argument('-c', '--critical', dest="critical", help='Critical threshold')

    return parser


def check_ssh_opts(opts):
    if not opts.hostname:
        exit_with_status(UNKNOWN, "Hostname parameter (-H) is mandatory")


def __convert_perfdata_value_to_str(val):
    if val == "":
        return val

    return "%d" % val


def add_perfdata(name, value, warning = "", critical = "", min = "", max = ""):
    perfdata.append({
        "name": name,
        "value": __convert_perfdata_value_to_str(value),
        "warning": __convert_perfdata_value_to_str(warning),
        "critical": __convert_perfdata_value_to_str(critical),
        "min": __convert_perfdata_value_to_str(min),
        "max": __convert_perfdata_value_to_str(max),
        })


def __render_perfdata(perf):
    return "\"%s\"=%s;%s;%s;%s;%s" % (perf["name"], perf["value"], perf["warning"], perf["critical"], perf["min"], perf["max"])


def exit_with_status(status, output, long_output = ""):
    color = ''
    label = ''

    if status == OK:
        color = '#2a9a3d'
        label = 'OK'
    elif status == WARNING:
        color = '#e48c19'
        label = 'WARNING'
    elif status == CRITICAL:
        color = '#dc2020'
        label = 'CRITICAL'
    else:
        color = '#A9A9A9'
        label = 'UNKNOWN'

    print "<span style=\"color:%s;font-weight: bold;\">[%s]</span> %s" % (color, label, output)

    if long_output != "":
        print long_output

    # TODO: Handle perfdata
    if len(perfdata) > 0:
        perfdata_formatted = map(__render_perfdata, perfdata)
        print "| %s" % ' '.join(perfdata_formatted)

    sys.exit(status)


# From naparuba/check_linux_by_ssh/schecks.py
def ssh_connect(hostname, port, ssh_key_file, passphrase, user):
    # Maybe paramiko is missing, but now we relly need ssh...
    if paramiko is None:
        exit_with_status(CRITICAL, "this plugin needs the python-paramiko module. Please install it")
    
    if not os.path.exists(os.path.expanduser(ssh_key_file)):
        exit_with_status(CRITICAL, "Missing ssh key file. please specify it with -i parameter")

    ssh_key_file = os.path.expanduser(ssh_key_file)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 

    ssh_config = paramiko.SSHConfig()
    user_config_file = os.path.expanduser("~/.ssh/config")
    if os.path.exists(user_config_file):
        with open(user_config_file) as f:
            ssh_config.parse(f)

    cfg = {'hostname': hostname, 'port': port, 'username': user, 'key_filename': ssh_key_file, 'password': passphrase}

    user_config = ssh_config.lookup(cfg['hostname'])
    for k in ('hostname', port, 'username', 'key_filename', 'password'):
        if k in user_config:
            cfg[k] = user_config[k]

    if 'proxycommand' in user_config:
        cfg['sock'] = paramiko.ProxyCommand(user_config['proxycommand'])

    try:
        client.connect(**cfg)
    except Exception, exp:
        err = "Connexion failed '%s'" % exp
        exit_with_status(CRITICAL, err)

    return client


def close(client):
    try:
        client.close()
    except Exception, exp:
        pass
