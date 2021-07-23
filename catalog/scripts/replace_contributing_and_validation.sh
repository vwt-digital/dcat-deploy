#!/bin/bash

cd repos || exit
for i in $(curl -H "Authorization:token ${TOKEN}" "https://api.github.com/orgs/vwt-digital/repos?type=all&per_page=100" | grep -oP '"full_name": "vwt-digital/\K.*?(?=")'); do
    git clone https://github.com/vwt-digital/"$i"
    cd "$i" || exit
    FILE=CONTRIBUTING.md
    rm CONTRIBUTING.md
    if [ ! -f "$FILE" ]; then
        cp /CONTRIBUTING.md CONTRIBUTING.md
      	echo "Removing from ""$i"
      	git add CONTRIBUTING.md
    fi
    FILE=.github/workflows/validation.yaml
    rm .github/workflows/validation.yaml
    if [ ! -f "$FILE" ]; then
      	echo "Removing from ""$i"
      	mkdir -p .github/workflows
      	cp /validation.yaml .github/workflows/validation.yaml
      	git add .github/workflows/validation.yaml
    fi
    git commit -nm "[skip ci]"
    git push
    cd ../
done