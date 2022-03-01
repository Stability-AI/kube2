import jinja2
import os
import subprocess
import sys
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz
from terminaltables import AsciiTable


def sh(cmd):
    os.system(cmd)


def sh_capture(cmd):
    # cmd = shlex.split(cmd)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
    )
    (out, err) = proc.communicate()
    return out.decode()


def load_template(fn: str, args: dict):
    searchpath = os.path.dirname(__file__)
    templateLoader = jinja2.FileSystemLoader(searchpath=searchpath)
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template(fn)
    return template.render(**args)


def generate_ssh_keypair(fn: str, quiet=False):
    '''Generates an ssh keypair into a given directory'''
    mode = '-q' if quiet else ''
    sh(f'ssh-keygen {mode} -t rsa -f {fn} -N ""')


def check_name(name: str):
    for c in name:
        if not c.isalnum() and c not in '-_':
            print(f'Error: Name "{name}" is invalid. Names should contain only alphanumerics or dashes/underscores')
            sys.exit(1)


def get_current_kube_context():
    x = sh_capture(f'kubectl config current-context')
    x = x.strip()
    if x.startswith('error'):
        print(x)
        sys.exit(1)
    return x


def time_ago_string(date):
    rd = relativedelta(pytz.utc.localize(datetime.now()), date)
    if rd.years > 1:
        years = f'{rd.years} years, '
    elif rd.years == 1:
        years = f'{rd.years} year, '
    else:
        years = ''
    if rd.months > 1:
        months = f'{rd.months} months, '
    elif rd.years == 1:
        months = f'{rd.months} month, '
    else:
        months = ''
    if rd.days > 1:
        days = f'{rd.days} days'
    elif rd.days == 1:
        days = f'{rd.days} day'
    else:
        days = ''
    return f'{years}{months}{days} ago'


def make_table(data):
    table = AsciiTable(data)
    table.outer_border = False
    table.inner_row_border = False
    table.inner_column_border = False
    table.inner_heading_row_border = False
    table.padding_left = 0
    table.padding_right = 2
    return table.table


def assert_binary_on_path(binary: str, msg: str = None):
    x = sh_capture('which ' + binary)
    if x.strip() == '' or x.endswith('not found'):
        if msg is None:
            print(f'Unable to find `{binary}` on your path. Aborting!')
        else:
            print(msg)
        sys.exit(1)