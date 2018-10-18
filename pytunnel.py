#!/usr/bin/python

import boto3
import json
import sys
import time
import os
import subprocess
import traceback
from urllib2 import urlopen
import socket
from contextlib import closing

version = '1.05'
polling_interval = 60
port_check_interval = 10

# aws sqs parameters
sqs = boto3.client('sqs',
                   aws_access_key_id     = os.environ['AWS_ACCESS_KEY_ID'],
                   aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY'],
                   region_name           = os.environ['AWS_DEFAULT_REGION'])
queue_url = os.environ['QUEUE_URL']

# commands and shortcuts
daemon  = ['--daemon',  '--d']
request = ['--request', '--r']
clear   = ['--clear',   '--c']

# list of all legal commands
commands = daemon + request + clear

def show_usage():
    print ('pytunnel version {}'.format(version))
    print ('usage:')
    print ('./pytunnel.py --daemon')
    print ('./pytunnel.py --request')
    print ('./pytunnel.py --clear')

def read_properties(filename):
    with open(filename) as json_data:
        data = json.load(json_data)
    return data

def log(msg):
    print ('{} - {}'.format(time.strftime("%x %H:%M:%S"), msg))

def delete_message():
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)

def send_message(jsonobject):
    try:
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(jsonobject)
        )
    except Exception:
        log(sys.exc_info()[0])

# client function
def check_port(port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex(('127.0.0.1', port)) == 0:
            return True
        else:
            return False

# client function
def kill_tunnels(username):
    # will kill reverse tunnels on client (that was created from server)
    # it uses a shell pattern to recognize the pid to kill
    find_pid_command = "ps -ef | grep 'sshd: chenchuk' | grep -Ev 'grep|root' | awk \"{ print $2 }\"".format(username)
    log(find_pid_command)
    client_pid = os.system(find_pid_command)
    os.system("kill -9 {}".format(client_pid))

# server function to create tunnel on remote client
def create_ssh_reverse_tunnel(tunnel_properties):
    my_ssh_user   = tunnel_properties['my_ssh_user']
    my_ssh_ip     = tunnel_properties['my_ssh_ip']
    my_ssh_port   = tunnel_properties['my_ssh_port']
    my_app_port   = tunnel_properties['my_app_port']
    your_app_port = tunnel_properties['your_app_port']
    log('processing tunnel request: for {} at {}:{}'.format(my_ssh_user, my_ssh_ip, my_ssh_port))
    try:
        with open("./stdout.txt","wb") as out, open("./stderr.txt","wb") as err:
            # example command : ssh -N -R 2210:localhost:22 bhome.dyndns.com
            subprocess.Popen(['ssh', '-oStrictHostKeyChecking=no',
                                     '-p', my_ssh_port,
                                     '-N', '-R', '{}:localhost:{}'.format(my_app_port, your_app_port),
                                     '{}@{}'.format(my_ssh_user, my_ssh_ip)])
    except:
        log('error creating ssh tunnel.')

# read args and decide if operating in request mode / daemon mode
# - request mode: fires a json request once to sqs queue and exit
# - daemon mode:  listens forever for a new requests from sqs queue
# - clear mode:   clear all tunnels of the username
mode = ''
if len(sys.argv) != 2:
    show_usage()
    sys.exit(1)
if sys.argv[1] not in commands:
    show_usage()
    sys.exit(1)
else:
    if sys.argv[1] in daemon:
        mode = 'daemon'
    elif sys.argv[1] in request:
        mode = 'request'
    elif sys.argv[1] in clear:
        mode = 'clear'
    else:
        show_usage()
        sys.exit(1)

########################## request mode (client) ###########################
if mode == 'request':
    log('pytunnel client version {}, sending tunnel request.'.format(version))

    data = read_properties('./tunnel-request.json')
    # auto injecting the public ip if value is 'dynamic'
    if data['my_ssh_ip'] == 'dynamic':
        data['my_ssh_ip'] = urlopen('http://ip.42.pl/raw').read()

    send_message(data)
    log('request sent, check local port {}'.format(data['my_app_port']))

    while not check_port(int(data['my_app_port'])):
        log('waiting for local port {} to listen ...'.format(data['my_app_port']))
        time.sleep(port_check_interval)
    log('tunnel created. you can now connect to localhost:{}'.format(data['my_app_port']))

########################## clear mode (client) ###########################
if mode == 'clear':
    #data = read_properties('./tunnel-request.json')
    #log('clearing all tunnels for user {}'.format(data['my_ssh_user']))
    #kill_tunnels(data['my_ssh_user'])
    #log('tunnel killed for user {}.'.format(username))
    log('not implemented.')

########################## daemon mode (server) ###########################
if mode == 'daemon':
    log ('pytunnel server version {}, entering main loop.'.format(version))
    while True:
        # get message
        response = sqs.receive_message(
            QueueUrl=queue_url,
            AttributeNames=['SentTimestamp'],
            MaxNumberOfMessages=1,
            MessageAttributeNames=['All'],
            VisibilityTimeout=0,
            WaitTimeSeconds=0
        )

        # if message exists
        if response.has_key('Messages'):

            # parse
            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']

            # decoding json
            try:
                body = json.loads(message['Body'])
                log('handling new tunnel request.')
                create_ssh_reverse_tunnel(body)
                log('tunnel created.')
            # if not json content
            except ValueError:
                log('ignoring, non json content')
                log(body)

            delete_message()

        else:
            log('no messages in sqs')
        time.sleep(polling_interval)

