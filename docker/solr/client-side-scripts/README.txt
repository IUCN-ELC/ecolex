Scripts in this folder are to be run from a machine remote from the one running the docker environment.
Scripts that connect from a client machine to the server machine, and possibly run commands inside a docker container
start with 'r' remote. The communication is through ssh.
One needs EDW_MACHINE_HOST and EDW_MACHINE_USER environment variables set for such scripts.
