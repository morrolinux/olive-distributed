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


## Logic overview

A master node is used to dispatch work amongst worker nodes. 
The master node has a "NFS Exporter" service running as root and a "Job dispatcher" process running as user.
Each worker node has a "NFS Mounter" service running as root and a "worker" process running as user.
In both cases the user process communicates with the root process via Pyro (RMI) using a 2-Way SSL connection.
The same approach is used for communication between workers and master:
![Architecture](/doc/architecture.png?raw=true "architecture")

When a job gets assigned to a worker, it is moved to the "ongoing" queue until a worker reports back on the exit status of the export: 
- If it failed, it's moved to the "failed" queue
- If it succeeded, it's moved to the "completed" queue

When the main job queue becomes empty, "failed" jobs are assigned to free workers (if any).

When the "failed" queue becomes empty as well, free workers are assigned "ongoing" jobs as they might belong to crashed/unreachable workers who couldn't report back. The first worker to finish an ongoing job gets to push it to the "completed" queue, the others get discarded:
![States](/doc/states.png?raw=true "states")

