#!/bin/bash

DATA_CATALOG=$1
GITHUB_ACCESS_TOKEN=$2

OLDIFS="$IFS"
IFS=$'\n'

for pr in $(python3 $(dirname $0)/listrepos.py ${DATA_CATALOG})
do
  # (re)Create the repo
  cp $(dirname $0)/template_newRepo.json $(dirname $0)/newRepo.json

  REPO_TITLE=$(echo $pr | python3 -c "import sys, json; print(json.load(sys.stdin)['distribution'][0]['title'])")

  ORGANISATION=$(echo $REPO_TITLE | cut -d / -f1)

  REPO_NAME=$(echo $REPO_TITLE | cut -d / -f2)

  REPO_DESCRIPTION=$(echo $pr | python3 -c "import sys, json; print(json.load(sys.stdin)['title'])")

  REPO_INTERNAL=$(echo $pr | python3 -c "import sys, json; print(json.load(sys.stdin)['accessLevel'])")

  echo $ORGANISATION
  echo $REPO_NAME
  echo $REPO_DESCRIPTION
  echo $REPO_INTERNAL

  sed -i "s/REPO_NAME/${REPO_NAME}/g" $(dirname $0)/newRepo.json
  sed -i "s/REPO_DESCRIPTION/${REPO_DESCRIPTION}/g" $(dirname $0)/newRepo.json

  if [ $REPO_INTERNAL == public ]
  then
    sed -i "s/REPO_INTERNAL/false/g" $(dirname $0)/newRepo.json
  else
    sed -i "s/REPO_INTERNAL/true/g" $(dirname $0)/newRepo.json
  fi

  curl -d @$(dirname $0)/newRepo.json -X POST -H "Authorization:token $(cat ${GITHUB_ACCESS_TOKEN})" "https://api.github.com/orgs/$(echo ${ORGANISATION})/repos"

  # Add "develop" branch
  export SHA=$(curl -X GET -H "Authorization:token $(cat ${GITHUB_ACCESS_TOKEN})" "https://api.github.com/repos/$(echo ${ORGANISATION})/$(echo ${REPO_NAME})/git/refs/heads" | \
	  python3 -c "import sys, json; print(json.load(sys.stdin)[0]['object']['sha'])")

  sed "s/SHA/${SHA}/g" $(dirname $0)/template_addBranch.json > $(dirname $0)/addBranch.json

  curl -d @$(dirname $0)/addBranch.json -X POST -H "Authorization:token $(cat ${GITHUB_ACCESS_TOKEN})" "https://api.github.com/repos/$(echo ${ORGANISATION})/$(echo ${REPO_NAME})/git/refs"

  # Set default branch to "develop"
  curl -d @$(dirname $0)/patchRepo.json -X PATCH -H "Authorization:token $(cat ${GITHUB_ACCESS_TOKEN})" "https://api.github.com/repos/$(echo ${ORGANISATION})/$(echo ${REPO_NAME})"

  # Set repo restrictions
  curl -d @$(dirname $0)/set_github_restrictions.json -X PUT -L -H "Authorization:token $(cat ${GITHUB_ACCESS_TOKEN})"  -H "Accept: application/vnd.github.luke-cage-preview+json" "https://api.github.com/repos/$(echo ${ORGANISATION})/$(echo ${REPO_NAME})/branches/master/protection"
done

IFS="$OLDIFS"

exit
