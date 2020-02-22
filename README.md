# olive-distributed

## Dependencies
`bind-tools python-pyro`

## Setup
On your "master" node, move to the ssl certs folder: `cd olive-distributed/ssl/certs`
1) Generate SSL & CA certs for the master node
`./generate_keys.sh setup`
2) For each worker node you wish to add:
`./generate_keys.sh add <hostname>`

During this setup, SSH service must be running on the worker node in order to copy SSL keys.


## Usage
Move to olive-distributed folder: `cd olive-distributed`
### On your worker nodes
1) Start the NFS mounter service:
`sudo python nfs_mounter.py`
2) Start the worker service:
`./run_worker_node.py`

### On the master node
1) Start the NFS exporter service:
`sudo python nfs_exporter.py`
2) Submit a job anytime:
`main.py --project /path/to/project.ove`
 (to export a single project in a distributed way) or 
`main.py --folder /path/to/folder/containing/projects/`
to enqueue multiple projects to be exported in parallel on multiple workers.


Note1: Your master node can also be a worker node, just do the steps for worker nodes as well.

Note2: Once set-up, worker nodes can come and go during a workload, fault tolerance should cope with changes at runtime.
