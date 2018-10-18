### pytunnel
###
### This utility is used to connet to a remote server behind a firewall using reverse ssh tunnel.
###
### The client (publicly accessible) will send a request for tunnel creation to an SQS queue (since it cant access the server directly)
### The server listens forever to SQS queue and creates a reverse tunnel upon request
###
### Prerequisites:
### 1. the server can access the client (ie. it can authenticate using ssh keys)

SERVER SIDE:
1. set environment variables by edit config file
export AWS_ACCESS_KEY_ID=XXX
export AWS_SECRET_ACCESS_KEY=XXX
export AWS_DEFAULT_REGION=XXX
export QUEUE_URL=XXX

2. source the config file and run the server side
$ . config
$ ./pytunnel.py --d
=================================================================

CLIENT SIDE:
1. edit the tunnel-request.json 
   - ip can be 'dynamic'. this allow the requester host to inject its own public ip

2. source config and request a tunnel
$ . config
$ ./pytunnel.py --r
=================================================================


