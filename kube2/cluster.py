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
)


@dataclass
class Cluster(object):
    name: str
    created_at: datetime
    status: str


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

    def current(
        self,
        *,
        name: str,
    ):
        '''
        Get the current cluster.
        '''
        pass

    def switch(
        self,
        *,
        name: str,
    ):
        '''
        Switch to a new cluster.
        '''
        pass
