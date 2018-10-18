#!/bin/bash

USER=$(cat tunnel-request.json | grep my_ssh_user | tr -d '" ,' | cut -d ":" -f2)

if [[ -z "${USER}" ]]; then
  echo "cant get user from json file"
  exit 1
fi

echo "killing tunnels for user ${USER}"
for PID in $(ps -ef | grep "sshd: ${USER}" | grep -Ev 'grep|root' | awk '{ print $2 }'); do
  kill ${PID}
  echo "pid ${PID} killed."
done
echo "done."
