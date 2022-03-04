from dataclasses import dataclass
import os
import sys
import tempfile
from typing import List

from kube2.utils import (
    check_name,
    get_context_name_from_cluster_name,
    get_contexts,
    get_current_cluster,
    get_current_context,
    humanize_date,
    load_template,
    make_table,
    sh,
)

from kube2.aws_utils import (
    get_clusters,
)


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
        new_context_name = get_context_name_from_cluster_name(name)
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

        cluster_name = get_current_cluster()
        if cluster_name is None:
            print('No kube2 cluster selected.')
            print('Note: You may be using a different cluster, not created by kube2.py.'\
                  'To check, use `kubectl config current-context`.')
            sys.exit(1)

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

        context_name = get_context_name_from_cluster_name(name)
        contexts = get_contexts()
        for c in contexts:
            if c.name == context_name:
                # cluster is already here, just need to switch to it
                sh(f'kubectl config use-context {context_name}')
                return
        # the cluster isn't added yet, we need to add it
        sh(f'aws eks --region us-east-1 update-kubeconfig --name {name} --alias {context_name}')
        # TODO: update aws-auth ConfigMap
        print('For now, you must manually add your user account to the ConfigMap for this cluster: https://aws.amazon.com/premiumsupport/knowledge-center/eks-cluster-connection/')
