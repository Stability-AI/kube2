import jinja2
import os
import subprocess
import sys
import arrow
from terminaltables import AsciiTable


def sh(cmd):
    try:
        subprocess.run(cmd, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print('Command Failed:', e)
        sys.exit(1)


def sh_capture(cmd):
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


def humanize_date(date):
    return arrow.get(date).humanize()


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
