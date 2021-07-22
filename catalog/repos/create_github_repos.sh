#!/bin/bash

DATA_CATALOG=${1}
GITHUB_SECRET_ID=${2}

basedir="$(dirname "$0")"

OLDIFS="$IFS"
IFS=$'\n'

GITHUB_ACCESS_TOKEN=$(gcloud secrets versions access latest --secret="${GITHUB_SECRET_ID}")

for pr in $(python3 "${basedir}"/listrepos.py "${DATA_CATALOG}"); do
  # (re)Create the repo
  cp "${basedir}"/template_newRepo.json "${basedir}"/newRepo.json

  REPO_TITLE=$(echo "$pr" | python3 -c "import sys, json; print(json.load(sys.stdin)['distribution'][0]['title'])")

  ORGANISATION=$(echo "$REPO_TITLE" | cut -d / -f1)

  REPO_NAME=$(echo "$REPO_TITLE" | cut -d / -f2)

  REPO_DESCRIPTION=$(echo "$pr" | python3 -c "import sys, json; print(json.load(sys.stdin)['title'])")

  REPO_INTERNAL=$(echo "$pr" | python3 -c "import sys, json; print(json.load(sys.stdin)['accessLevel'])")

  echo "${ORGANISATION}"
  echo "${REPO_NAME}"
  echo "${REPO_DESCRIPTION}"
  echo "${REPO_INTERNAL}"

  sed -i "s/REPO_NAME/${REPO_NAME}/g" "${basedir}/newRepo.json"
  sed -i "s/REPO_DESCRIPTION/${REPO_DESCRIPTION}/g" "${basedir}/newRepo.json"

  if [ "$REPO_INTERNAL" == public ]; then
    sed -i "s/REPO_INTERNAL/false/g" "${basedir}/newRepo.json"
  else
    sed -i "s/REPO_INTERNAL/true/g" "${basedir}/newRepo.json"
  fi

  curl -d @"${basedir}"/newRepo.json -X POST -H "Authorization:token ${GITHUB_ACCESS_TOKEN}" "https://api.github.com/orgs/${ORGANISATION}/repos"

  # Create validation and contributing
  curl -i -X PUT -H "Authorization:token ${GITHUB_ACCESS_TOKEN}" "https://api.github.com/repos/${ORGANISATION}/${REPO_NAME}/contents/CONTRIBUTING.md" -d '{"message":"Initial contributing [skip ci]","content":"'"$(less -FX "${basedir}"/contributing.b64)"'"}'
  curl -i -X PUT -H "Authorization:token ${GITHUB_ACCESS_TOKEN}" "https://api.github.com/repos/${ORGANISATION}/${REPO_NAME}/contents/.github/workflows/validation.yaml" -d '{"message":"Initial validation [skip ci]","content":"'"$(less -FX "${basedir}"/validation.b64)"'"}'

  # Add "develop" branch
  # shellcheck disable=SC2155
  export SHA=$(curl -X GET -H "Authorization:token ${GITHUB_ACCESS_TOKEN}" "https://api.github.com/repos/${ORGANISATION}/${REPO_NAME}/git/refs/heads" |
    python3 -c "import sys, json; print(json.load(sys.stdin)[0]['object']['sha'])")

  sed "s/SHA/${SHA}/g" "${basedir}"/template_addBranch.json >"${basedir}"/addBranch.json

  curl -d @"${basedir}"/addBranch.json -X POST -H "Authorization:token ${GITHUB_ACCESS_TOKEN}" "https://api.github.com/repos/${ORGANISATION}/${REPO_NAME}/git/refs"

  # Set default branch to "develop"
  curl -d @"${basedir}"/patchRepo.json -X PATCH -H "Authorization:token ${GITHUB_ACCESS_TOKEN}" "https://api.github.com/repos/${ORGANISATION}/${REPO_NAME}"

  # Set repo restrictions
  curl -d @"${basedir}"/set_github_restrictions.json -X PUT -L -H "Authorization:token ${GITHUB_ACCESS_TOKEN}" -H "Accept: application/vnd.github.luke-cage-preview+json" "https://api.github.com/repos/${ORGANISATION}/${REPO_NAME}/branches/master/protection"
done

IFS="$OLDIFS"

# shellcheck disable=SC2230
if [ -z "$(which pip3)" ]; then
  pip install virtualenv==16.7.9
else
  pip3 install virtualenv
fi
virtualenv -p python3 venv_github_perm
# shellcheck disable=SC1091
source venv_github_perm/bin/activate
pip install requests==2.7.0
python3 "${basedir}"/set_github_team_repo_permissions.py "${DATA_CATALOG}" "${GITHUB_ACCESS_TOKEN}"
deactivate
