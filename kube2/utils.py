from collections import defaultdict
from typing import List, Optional
import jinja2
import os
import subprocess
import sys
import arrow
from terminaltables import AsciiTable
import boto3
from kube2.aws_utils import get_clusters
import json
from datetime import datetime

from kube2.types import Cluster, Context, Job, Volume


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
    templateEnv = jinja2.Environment(loader=templateLoader, undefined=jinja2.StrictUndefined)
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



def get_current_context():
    return sh_capture(f'kubectl config current-context').strip()


def get_context_name_from_cluster_name(cluster_name: str):
    return f'kube2-{cluster_name}'


def get_cluster_name_from_context_name(context_name: str) -> Optional[str]:
    if context_name.startswith('kube2-'):
        return context_name[6:]
    else:
        return None


def get_current_cluster() -> Optional[str]:
    cluster_name = get_cluster_name_from_context_name(get_current_context())
    if cluster_name is None:
        return None
    assert cluster_name in [c.name for c in get_clusters()]
    return cluster_name


def get_contexts(filter_kube2=True) -> List[Context]:
    x = sh_capture(f'kubectl config get-contexts').strip()
    if not x.startswith('CURRENT'):
        print('Error:')
        print(x)
        sys.exit(1)
    x = x.split('\n')[1:]
    contexts = []
    for line in x:
        items = line.strip().split()
        if items[0].strip() == '*':
            name = items[1]
            selected = True
        else:
            name = items[0]
            selected = False
        if filter_kube2 and not name.startswith('kube2'):
            pass  # filter out this local context, b/c it wasn't created with kube2
        else:
            contexts.append(Context(name=name, selected=selected))
    return contexts


def get_volumes() -> List[Volume]:
    x = sh_capture(f'''kubectl get pvc -o=jsonpath='{{@}}' ''').strip()
    data = json.loads(x)
    volumes = []
    for item in data['items']:
        name = item['metadata']['name']
        # remove the "pvc-" from the start
        name = name[name.index('-')+1:]
        created = datetime.strptime(
            item['metadata']['creationTimestamp'],
            '%Y-%m-%dT%H:%M:%SZ'
        )
        capacity = item['status']['capacity']['storage']
        volumes.append(Volume(
            name=name,
            capacity=capacity,
            usage='todo',  # TODO: compute usage
            created=created,
        ))
    # print(json.dumps(data, indent=2))
    return volumes


def get_volume_names_attached_to_job(job_name: str) -> List[str]:
    x = sh_capture(f''' kubectl exec --stdin {job_name}-1 -- /bin/bash -c 'ls /mnt' ''').strip()
    x = [e.strip() for e in x.split()]
    return x


def get_jobs() -> List[Job]:
    x = sh_capture('kubectl get pods')
    x = x.strip()
    if not x.startswith('NAME'):
        return []
    else:
        x = x.strip().split('\n')
        x = x[1:]  # skip titles
        d = defaultdict(lambda: [])
        for line in x:
            name, ready, status, restarts, age = line.split()
            key = '-'.join(name.split('-')[:-1])
            d[key].append([name, ready, status, restarts, age])
        jobs = []
        for k, v in d.items():
            name = k
            if all('Running' == e for e in v[0][2].split(',')):
                attached_volumes = get_volume_names_attached_to_job(name)
            else:
                attached_volumes = []
            nodes = len(v)
            if all(e[2] == 'Running' for e in v):
                status = 'All Running'
            else:
                status = ','.join(e[2] for e in v)
            restarts = v[0][3]
            age = v[0][4]
            jobs.append(Job(
                name=name,
                nodes=nodes,
                restarts=restarts,
                status=status,
                age=age,
                attached_volumes=attached_volumes,
            ))
        return jobs
