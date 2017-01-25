# Deploy architecture

This deployment structure is based on bash scripts and ssh
There are three entities at play here:
1. Your Own machine.
2. The Host machine.
3. The docker container(s)

## Own machine

### General

This is the machine from where the deploy commands are passed to the Host machine.
This machine should hold:
1. deploy scripts 
2. own-to-host deploy environment variables
3. host-to-docker environment and secrets to be copied down to the host machine

This machine should be any machine that can run bash, git and ssh/scp, thus a Windos 10 machine should also work,
besides linux and Mac. Unless you plan to build the to be deployed docker images, no docker is required on Own machine.

TODO: until the architecture is more clear and becomes simpler and more streamlined,
the deploy scripts might be entangled with the source code repo of the project.
Make sure the secret or the specific deploy environment does not get pushed to such a repo.
TODO: add the deploy unified machinery, that will be extended by deploy scripts specific to
each deployment

One could simply ssh into the Host machine, copy secrets there, copy the deploy scripts and and run the deployment from
there. The target however is that such thing will not be required.

### Own machine requirements

* git, and access to deploy/soruce repos
* bash/sh
* ssh-client with public/private keys for the user that will be authorized to log on the Host machine


## Host machine

### General

The Host machine runs the docker daemon and containers.
TODO: On docker swarm addition this will be the swarm host.
I shall assume that this machine is a linux machine. (actually a debian linux machine)
The Host machine should hold:
1. docker and docker-able user used for deployments
2. web server/apache
3. sshd; accept connections from Own machine into the docker-able user
4. docker-compose.yml code, due to the current entanglement - the project repo (thus git)
5. firewall

### Host machine requirements

* sshd
* docker daemon/client (>1.10), docker-compose (>1.6)
* git
* apache
* iptables

### Host machine setup

#### sshd & deploy user

Create the deploy user, I shall call it deploy from now on

```bash
useradd --user-group --create-home --shell /bin/bash deploy
usermod -aG docker deploy
```
Add your the public key from the user you shall use on your Own machine to the `authorized_keys` of the deploy user of
Host machine. For RSA keys, copy `id_rsa.pub` from your user on the Own machine over to `/home/deploy/.ssh/authorized_keys`

Install openssh-server if missing and set AllowUsers to accept deploy if needed.


#### docker

wget a docker-engine deb file from https://apt.dockerproject.org/repo/pool/main/d/docker-engine/

It has to be greater than 1.10.
```bash
apt-get install libapparmor1
dpkg -i <docker.deb>
```
Or use any other method to setup docker

For docker-compose the easyest way is to install pip
```bash
apt-get install python-pip python-dev build-essentials
pip install docker-compose
```

#### git
Get git
`apt-get install git`

#### apache
TODO

#### iptables
TODO


## Docker environment

The docker environment is configured by the environment and files of the Own machine.
Part of that environment is used for identifying the Host machine, where and how to deploy.
Anoter part of it is passed to the Host machine, some in a persistent way - copying files, and is used by
docker/docker-compose at startup/orchestration


# Deploying

## Some considerations

Currently scripts involved in deployment are in soruce repo, in deploy dir and in docker dir.
TODO: Fix this. Gather everything unde deploy dir.
scripts of form `r-<some-name>.sh` are to be executed on a machine remote to the Host machine.
(r = remote) That is your Own machine

The files holding environment variables Own-to-Host are in `.env` files. This files ignored by git.
TODO: This files currently hold both Own-to-Host env vars and Host-to-Docker vars.
TODO: The vars in this file do not have a robust and somple namespace yet.
TODO: This files (the sample, which is commited to git) are poluting the root of the project.

The files holding Host-to-Docker vars are in `deploy/envs/`. With the exception of secret.env the rest of the files are
versioned in git. This means that these enviroment vars are not prone to change often and do not differ between
environments.
*Keep your secret.env file safe*
TODO: Make a clear separation between files that differ from oen deployment to another and files that do not (and are in
git therefore). Also make a clear separation between environment vars that are Own-to-Host and the one Host-to-Docker

*When executing deploy or Own machine scripts (r-<some-name>.sh) one should populate his own environment with the proper
vars*
It is not recomended to do this in a persistend way like exporting env vars.
Rather this method is recomended:
```bash
env `xargs < .env` deploy/build.sh
```
Where .env is a file containing Own-to-Host env vars, but possibly some Host-to-Docker vars too
and the script to be run can be a script in `deploy/` or a `r-<some-script>.sh`
Usually this 'r' scripts are initializing live data and need to be hot instructed where exactly to pull data from
and what to initialize. This kind of information is not set in stone in the source code and thus is not in the repo
files holding env vars.

## Build

Befoare deploying one needs to build and push the required images to docker.hub
