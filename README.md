# EKS Management Tool

## Installation

1. Install `kubectl`: https://docs.aws.amazon.com/eks/latest/userguide/install-kubectl.html
2. Install `eksctl`: https://docs.aws.amazon.com/eks/latest/userguide/eksctl.html
3. Clone this repository, and install the dependencies `pip install -r requirements.txt`. You may want to do this in a virtual environment.

You should now be able to use the CLI.
To show the help page, use `python kube2.py --help`.

## Basic Usage

First, ensure you are using the AWS profile, by setting the `AWS_PROFILE` environment variable.
By default, you will use the `default` AWS profile. (view your profiles with `cat ~/.aws/credentials`)

Then, to list the available clusters, type `python kube2.py cluster list`. This will display the available clusters:

```
NAME         CREATED      STATUS  
test-2       2 days ago   ACTIVE  
my-cluster   4 hours ago  ACTIVE  
```

By default, we probably aren't selecting any cluster. Check with `python kube2.py cluster current`:

```
No cluster selected.
```

Select a cluster with `python kube2.py cluster select --name my-cluster`:

Then, use `python kube2.py job [deploy|list|kill|ssh]` to work with jobs on the cluster.
