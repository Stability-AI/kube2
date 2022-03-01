#!/usr/bin/env python3

import fire

from kube2.cluster import ClusterCLI
from kube2.job import JobCLI
from kube2.volume import VolumeCLI


class CLI(object):
    '''
    A CLI for working with Kubernetes clusters on EKS.
    '''

    cluster = ClusterCLI()
    job = JobCLI()
    volume = VolumeCLI()


if __name__ == '__main__':
    fire.Fire(CLI)
