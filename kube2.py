#!/usr/bin/env python3

import fire

from kube2.cluster import ClusterCLI
from kube2.job import JobCLI
from kube2.utils import assert_binary_on_path
from kube2.volume import VolumeCLI


class CLI(object):
    '''
    A CLI for working with Kubernetes clusters on EKS.
    '''

    cluster = ClusterCLI()
    job = JobCLI()
    volume = VolumeCLI()


if __name__ == '__main__':
    assert_binary_on_path('eksctl', 'You must install `eksctl` to use this tool.')
    assert_binary_on_path('kubectl', 'You must install `kubectl` to use this tool.')
    fire.Fire(CLI)
