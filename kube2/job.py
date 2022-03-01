from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import os
import sys
import tempfile
from typing import List

from kube2.utils import (
    check_name,
    generate_ssh_keypair,
    load_template,
    make_table,
    sh,
    sh_capture,
)


@dataclass
class Job(object):
    name: str
    replicas: int
    restarts: int
    status: str
    age: str


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
            replicas = len(v)
            if all(e[2] == 'Running' for e in v):
                status = 'All Running'
            else:
                status = ','.join(e[2] for e in v)
            restarts = v[0][3]
            age = v[0][4]
            jobs.append(Job(
                name=name,
                replicas=replicas,
                restarts=restarts,
                status=status,
                age=age,
            ))
        return jobs


class JobCLI(object):
    '''
    Deploy, kill, and list jobs (aka groups of pods).
    '''

    def deploy(
        self,
        *,
        name: str,
        docker_image: str = 'leogao2/gpt-neox:main',
        replicas: int = 1,
        attach_volumes: List[str] = [],
    ):
        '''
        Deploy a new job to the cluster (aka, a group of networked pods).
        '''

        check_name(name)
        jobs = get_jobs()
        if name in [j.name for j in jobs]:
            print(f'Error: A job already exists with name "{name}".')
            sys.exit(1)

        with tempfile.TemporaryDirectory() as tmpdir:

            # put start script and keys in secret volume
            date = datetime.now().strftime("%Y-%m-%d-%H-%M")
            secret_name = f'{name}-{date}'
            script = load_template(
                fn='templates/post-start-script.sh',
                args={}
            )
            keypair_fn = os.path.join(tmpdir, 'id_rsa')
            script_fn = os.path.join(tmpdir, 'tmp.sh')
            generate_ssh_keypair(keypair_fn)
            with open(script_fn, 'w') as f:
                f.write(script)
            sh(
                f'kubectl create secret generic {secret_name}'
                f'    --from-file=id_rsa.pub={keypair_fn}'
                f'    --from-file=post_start_script.sh={script_fn}'
            )

            # create the pods
            ss = load_template(
                fn='templates/statefulset.yml',
                args={
                    'name': name,
                    'docker_image': docker_image,
                    'replicas': replicas,
                    'secret_name': secret_name,
                }
            )
            ss_fn = os.path.join(tmpdir, 'ss.yml')
            with open(ss_fn, 'w') as f:
                f.write(ss)
            sh(f'kubectl apply -f {f.name}')

            # wait for them to be ready
            sh(f'kubectl rollout status --watch --logtostderr --timeout=300s statefulsets/{name}')

            # generate the hostfile
            hostfile_fn = os.path.join(tmpdir, 'hostfile')
            hosts_fn = os.path.join(tmpdir, 'hosts')
            sh(f'''kubectl get pods -o wide | grep {name} | awk '{{print $6 " slots=8"}}' > {hostfile_fn}''')
            sh(f"cat {hostfile_fn} | cut -f1 -d' ' > {hosts_fn}")

            # copy them to the node
            home_dir = sh_capture(f'kubectl exec {name}-0 -- /bin/bash -c "cd ~; pwd"').strip()
            sh(f'kubectl cp {hostfile_fn} {name}-0:/job')
            sh(f'kubectl cp {hosts_fn} {name}-0:/job')
            sh(f'kubectl cp {keypair_fn} {name}-0:{home_dir}/.ssh')

    def list(
        self,
    ):
        '''
        List all the running jobs.
        '''

        table = [['NAME', 'REPLICAS', 'RESTARTS', 'STATUS', 'AGE']]
        jobs = get_jobs()
        if len(jobs) == 0:
            # just show the raw kubectl output (it might actually be an error)
            sh('kubectl get pods')
        else:
            for job in jobs:
                table.append([job.name, job.replicas, job.restarts, job.status, job.age])
            print(make_table(table))

    def kill(
        self,
        *,
        name: str,
    ):
        '''
        Kill a running job.
        '''

        sh(f'kubectl delete statefulsets/{name}')

    def ssh(
        self,
        *,
        name: str,
    ):
        '''
        SSH into the root replica of a job.
        '''

        check_name(name)
        sh(f'kubectl exec --stdin --tty {name}-0 -- /bin/bash')
