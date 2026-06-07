#!/bin/bash

set -e -u

scriptdir=$(dirname $(readlink -f "$0"))

bugreportfile="${scriptdir}/bugreport.txt"

current_token=$(cat "${bugreportfile}" | jq -r .projectAccessToken)
client_id=$(cat "${bugreportfile}" | jq -r .clientID)

new_token=$(curl --silent \
                 --show-error \
                 --fail \
                 --request POST \
                 --header "PRIVATE-TOKEN: ${current_token}" \
                 "https://gitlab.com/api/v4/projects/71776868/access_tokens/self/rotate?expires_at=$(date -I -d '+100 days')" | jq -r .token)
     
newbugreportfile="${bugreportfile}.new"                
cat > "${newbugreportfile}" <<EOF
{
"clientID": "${client_id}",
"projectAccessToken": "${new_token}"
}
EOF

mv "${newbugreportfile}" "${bugreportfile}"
