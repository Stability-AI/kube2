from typing import List, Optional
import boto3

from kube2.types import (
    Cluster,
)


def get_clusters() -> List[Cluster]:
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


def get_cluster_vpc_id(cluster_name: str):
    eks_client = boto3.client('eks')
    response = eks_client.describe_cluster(
        name=cluster_name
    )
    return response['cluster']['resourcesVpcConfig']['vpcId']


def get_security_group_id(vpc_id: str, group_name: str) -> Optional[str]:
    ec2 = boto3.client('ec2', region_name='us-east-1')
    for sg in ec2.describe_security_groups()['SecurityGroups']:
        if sg['GroupName'] == group_name and sg['VpcId'] == vpc_id:
            return sg['GroupId']
    return None


def get_subnet_id(vpc_id: str) -> Optional[str]:
    ec2 = boto3.client('ec2', region_name='us-east-1')
    for subnet in ec2.describe_subnets()['Subnets']:
        if subnet['VpcId'] == vpc_id:
            return subnet['SubnetId']
    return None
