set -e

USER=$(whoami)
echo $USER
# sudo apt-get update -y
# sudo apt-get install -y sudo pdsh git ssh
sudo chown $USER:$USER ~/.ssh/config
echo '    StrictHostKeyChecking no' >> ~/.ssh/config
echo '    ServerAliveInterval 20' >> ~/.ssh/config
echo '    TCPKeepAlive no' >> ~/.ssh/config
sudo mkdir -p /run/sshd
sudo /usr/sbin/sshd
sudo rm -rf /job
sudo mkdir -p /job ~/.ssh
sudo chown $USER:$USER /job
sudo cp /secrets/id_rsa.pub ~/.ssh/authorized_keys
sudo chown -R $USER:$USER ~/.ssh
sudo chown $USER:$USER ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
echo 'export LC_ALL=C.UTF-8' >> ~/.bashrc
echo 'export LANG=C.UTF-8' >> ~/.bashrc
cd ~
git clone https://github.com/EleutherAI/gpt-neox.git
cd ~/gpt-neox && sudo python ~/gpt-neox/megatron/fused_kernels/setup.py install
