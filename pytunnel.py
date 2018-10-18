#!/usr/bin/python

import boto3
import json
import sys
import time
import os
import subprocess
import traceback
from urllib2 import urlopen

version = '1.03'

sqs = boto3.client('sqs',
                   aws_access_key_id     = os.environ['AWS_ACCESS_KEY_ID'],
                   aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY'],
                   region_name           = os.environ['AWS_DEFAULT_REGION'])

queue_url = os.environ['QUEUE_URL']

def show_usage():
    print ('pytunnel version {}'.format(version))
    print ('usage:')
    print ('./pytunnel.py --daemon')
    print ('./pytunnel.py --request')

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
        print(sys.exc_info()[0])

def create_ssh_reverse_tunnel(tunnel_properties):
    my_ssh_user   = tunnel_properties['my_ssh_user']
    my_ssh_ip     = tunnel_properties['my_ssh_ip']
    my_ssh_port   = tunnel_properties['my_ssh_port']
    my_app_port   = tunnel_properties['my_app_port']
    your_app_port = tunnel_properties['your_app_port']
    log('processing tunnel request: for {} at {}:{}'.format(my_ssh_user, my_ssh_ip, my_ssh_port))

                                     # '-Cfo',
                                     # 'ExitOnForwardFailure=yes',
    try:
        with open("./stdout.txt","wb") as out, open("./stderr.txt","wb") as err:
            # ssh -N -R 2210:localhost:22 bhome.dyndns.com
            subprocess.Popen(['ssh', '-oStrictHostKeyChecking=no',
                                     '-p', my_ssh_port,
                                     '-N', '-R', '{}:localhost:{}'.format(my_app_port, your_app_port),
                                     '{}@{}'.format(my_ssh_user, my_ssh_ip)
                             ])
    except:
        print ('error creating ssh tunnel.')

# read args and decide if operating in request mode / daemon mode
# - request mode: fires a json request once to sqs queue and exit
# - daemon mode: listens forever for a new requests from sqs queue
#
mode = ''
if len(sys.argv) != 2:
    show_usage()
    sys.exit(1)
if sys.argv[1] not in ['--daemon', '--request', '--d', '--r']:
    show_usage()
    sys.exit(1)
else:
    if sys.argv[1] in ['--daemon', '--d']:
        mode = 'daemon'
    else:
        mode = 'request'

########################## request mode ###########################
if mode == 'request':

    data = read_properties('./tunnel-request.json')
    # auto injecting the public ip if value is 'dynamic'
    if data['my_ssh_ip'] == 'dynamic':
        data['my_ssh_ip'] = urlopen('http://ip.42.pl/raw').read()

    send_message(data)

########################## daemon mode ###########################
if mode == 'daemon':
    log ('pytunnel version {}, entering main loop.'.format(version))
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
        time.sleep(60)

