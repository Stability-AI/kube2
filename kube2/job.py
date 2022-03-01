from datetime import datetime
import os
import tempfile
from typing import List

from kube2.utils import (
    check_name,
    generate_ssh_keypair,
    load_template,
    sh,
    sh_capture,
)


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

    def list(self):
        x = sh_capture('kubectl get pods')
        if not x.strip().startswith('NAME'):
            print(x.strip())
        else:
            x = x.strip().split('\n')
            x = x[1:]  # skip titles
            for line in x:
                name, ready, status, restarts, age = line.split()
                print(name)

    def kill(
        self,
        *,
        name: str,
    ):
        sh(f'kubectl delete statefulsets/{name}')
