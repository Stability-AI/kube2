# 1. kubectl create -k "github.com/kubernetes-sigs/aws-fsx-csi-driver/deploy/kubernetes/overlays/stable/?ref=master"

# 2. python get_security_group.py

# 3. kubectl apply -f specs/eks/fsx.yml

import os
import sys
import tempfile
import time
from typing import List
import boto3
from kube2.types import Volume

from kube2.utils import (
    check_name,
    get_current_cluster,
    get_volumes,
    humanize_date,
    load_template,
    make_table,
    sh,
    sh_capture,
)

from kube2.aws_utils import (
    get_cluster_vpc_id,
    get_clusters,
    get_security_group_id,
    get_subnet_id,
)


def enable_fsx():
    sh(f'kubectl create -k "github.com/kubernetes-sigs/aws-fsx-csi-driver/deploy/kubernetes/overlays/stable/?ref=master"')


def is_fsx_enabled():
    s = sh_capture(f'kubectl get csidrivers.storage.k8s.io fsx.csi.aws.com').strip()
    return s.startswith('NAME')


def create_and_configure_security_group(
    *,
    cluster_name: str,
    volume_name: str,
    vpc_id: str,
):
    client = boto3.client('ec2', region_name='us-east-1')
    group_name = f'{cluster_name}-{volume_name}-fsx'

    sg_id = get_security_group_id(vpc_id=vpc_id, group_name=group_name)

    # create if doesn't already exist
    if sg_id is None:
        print('Security group does not exist for cluster. Creating one...')
        response = client.create_security_group(
            GroupName=group_name,
            Description=f'SG for FSx {cluster_name}-{volume_name}',
            VpcId=vpc_id,
        )
        sg_id: str = response['GroupId']

        client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 988,
                    'ToPort': 988,
                    'IpRanges': [{'CidrIp': '192.168.0.0/16'}],
                },
            ],
        )

    else:
        print('Security group already exists for cluster...')

    return sg_id


def get_pvc_name(volume_name: str):
    return f'pvc-{volume_name}'


def get_sc_name(volume_name: str):
    return f'sc-{volume_name}'


class VolumeCLI(object):
    '''
    Create or destroy shared persistent volumes on FSx.
    '''

    def create(
        self,
        *,
        name: str,
        storage_size: str,
    ):
        '''
        Create a new FSx volume backed by S3.
        '''

        check_name(name)
        if name in [v.name for v in get_volumes()]:
            print(f'Error: Volume "{name}" already exists.')
            sys.exit(1)

        cluster_name = get_current_cluster()
        if cluster_name is None:
            print('No cluster selected. Switch to or create a cluster first.')
            sys.exit(1)

        # enable the FSx feature on this cluster
        if not is_fsx_enabled():
            enable_fsx()

        vpc_id = get_cluster_vpc_id(cluster_name)
        sg_id = create_and_configure_security_group(
            cluster_name=cluster_name,
            volume_name=name,
            vpc_id=vpc_id
        )
        pvc_name = get_pvc_name(name)
        sc_name = get_sc_name(name)
        subnet_id = get_subnet_id(vpc_id)
        assert subnet_id is not None

        with tempfile.TemporaryDirectory() as tmpdir:

            script_fn = os.path.join(tmpdir, 'fsx.yml')
            script = load_template(
                fn='templates/fsx.yml',
                args={
                    'storage_class_name': sc_name,
                    's3_import_path': f's3://kube2-volumes/{name}',
                    's3_export_path': f's3://kube2-volumes/{name}/export',
                    'security_group_id': sg_id,
                    'persistent_volume_claim_name': pvc_name,
                    'storage_size': storage_size,
                    'storage_class_name': sc_name,
                    'subnet_id': subnet_id,
                }
            )
            with open(script_fn, 'w') as f:
                f.write(script)

            print('Creating volume...')
            sh(f'kubectl apply -f {script_fn}')
            print('Waiting for FSx filesystem to be created (check progress here: https://console.aws.amazon.com/fsx/home?region=us-east-1)...')
            for _ in range(60*2):
                s = sh_capture(f'''kubectl get pvc pvc-my-vol -o 'jsonpath={{..status.phase}}' ''').strip()
                if s == 'Bound':
                    break
                time.sleep(1)
            sh(f'kubectl describe pvc | tail -n 1')

    def delete(
        self,
        *,
        name: str,
    ):
        '''
        Delete an FSx volume.
        '''

        # TODO: more checks here around what can can't be deleted:
        #    - doesn't exist?
        #    - is attached to pods?
        #    - has some files? (maybe y/n checks)

        pvc_name = get_pvc_name(name)
        sc_name = get_sc_name(name)

        try:
            sh(f'kubectl delete pvc {pvc_name}')
        except Exception as e:
            print(e)
        try:
            sh(f'kubectl delete sc {sc_name}')
        except Exception as e:
            print(e)

    def list(self):
        '''
        List all the volumes in the current cluster.
        '''

        volumes = get_volumes()
        if len(volumes) == 0:
            print('No volumes.')
        else:
            table = [['NAME', 'CAPACITY', 'USAGE', 'CREATED']]
            for v in volumes:
                table.append([
                    v.name,
                    v.capacity,
                    v.usage,
                    humanize_date(v.created),
                ])
            print(make_table(table))
