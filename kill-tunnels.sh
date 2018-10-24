#!/bin/bash

USER=$(cat tunnel-request.json | grep my_ssh_user | tr -d '" ,' | cut -d ":" -f2)

MY_APP_PORT=$(cat tunnel-request.json | grep my_app_port | tr -d '" ,' | cut -d ":" -f2)

if [[ -z "${USER}" ]]; then
  echo "cant get user from json file"
  exit 1
fi

if [[ -z "${MY_APP_PORT}" ]]; then
  echo "cant get application local port from json file"
  exit 1
fi


echo "killing tunnels for user ${USER}"

PID=$(sudo lsof -i -n | egrep '\<sshd\>' | grep IPv4 | grep ${MY_APP_PORT} | grep \(LISTEN\) | awk '{ print $2 }')

#for PID in $(ps -ef | grep "sshd: ${USER}" | grep -Ev 'grep|root' | awk '{ print $2 }'); do
  #kill ${PID}
  echo "pid ${PID} killed."
##done
echo "done."
