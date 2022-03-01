from dataclasses import dataclass
import os
import sys
import tempfile
from typing import List
import boto3
from datetime import datetime

from kube2.utils import (
    check_name,
    humanize_date,
    load_template,
    make_table,
    sh,
    sh_capture,
)


@dataclass
class Cluster(object):
    name: str
    created_at: datetime
    status: str


@dataclass
class Context(object):
    name: str
    selected: bool


def get_clusters():
    EKS = boto3.client('eks')
    response = EKS.list_clusters()
    clusters: List[Cluster] = []
    for cluster_name in response['clusters']:
        response2 = EKS.describe_cluster(name=cluster_name)
        created_at = response2['cluster']['createdAt']
        status = response2['cluster']['status']
        clusters.append(Cluster(
            name=cluster_name,
            created_at=created_at,
            status=status,
        ))
    return clusters


def get_current_context():
    return sh_capture(f'kubectl config current-context').strip()


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

class ClusterCLI(object):
    '''
    Create or destroy EKS clusters. These commands take a long time!
    '''

    def create(
        self,
        *,
        name: str,
        nodes: int,
        instance_type: str,
    ):
        '''
        Creates a new EKS cluster.
        '''

        check_name(name)

        if name in [c.name for c in get_clusters()]:
            print(f'Error: There is already a cluster named "{name}"')
            sys.exit(1)

        with tempfile.TemporaryDirectory() as tmpdir:
            cluster_config_fn = os.path.join(tmpdir, 'cluster.yml')
            cluster_config = load_template(
                fn='templates/cluster.yml',
                args={
                    'name': name,
                    'nodes': nodes,
                    'instance_type': instance_type,
                }
            )
            with open(cluster_config_fn, 'w') as f:
                f.write(cluster_config)
            print('\n>> '.join(cluster_config.split('\n')))
            y = input('\nEKS cluster will be created with the above YAML configuration. This will take anywhere from 10 minutes to an hour. Proceed? [y|n] ')
            if y.lower() != 'y':
                print('Aborting!')
                sys.exit(1)
            sh(f'eksctl create cluster -f {cluster_config_fn}')

        # change the context name so it matches the cluster name
        context_name = get_current_context()
        new_context_name = f'kube2-{name}'
        sh(f'kubectl config rename-context {context_name} {new_context_name}')

    def list(self):
        '''
        Lists all of the available clusters.
        '''

        data = [['NAME', 'CREATED', 'STATUS']]
        for c in get_clusters():
            data.append([c.name, humanize_date(c.created_at), c.status])
        print(make_table(data))

    def delete(
        self,
        *,
        name: str,
    ):
        '''
        Deletes a cluster.
        '''

        if name not in [c.name for c in get_clusters()]:
            print(f'Error: No cluster named "{name}"')
            sys.exit(1)

        sh(f'eksctl delete cluster --name {name}')

    def current(
        self,
    ):
        '''
        Get the current cluster.
        '''

        context = get_current_context()
        cluster_name = context[context.index('-')+1:]
        print(cluster_name)

    def switch(
        self,
        *,
        name: str,
    ):
        '''
        Switch to a new cluster.
        '''

        if name not in [c.name for c in get_clusters()]:
            print(f'Error: No cluster named "{name}"')
            sys.exit(1)

        context_name = f'kube2-{name}'
        contexts = get_contexts()
        for c in contexts:
            if c.name == context_name:
                # cluster is already here, just need to switch to it
                sh(f'kubectl config use-context {context_name}')
                return
        sh(f'aws eks --region us-east-1 update-kubeconfig --name {name} --alias {context_name}')
