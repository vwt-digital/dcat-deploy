import json
import sys


def get_list_of_gits(json_file_name):
    json_file = open(json_file_name, 'r')
    catalog = json.load(json_file)

    download_urls = []
    for entry in catalog['dataset']:
        if 'distribution' in entry:
            for dist in entry['distribution']:
                if 'downloadURL' in dist and 'format' in dist and dist['format'] == 'gitrepo':
                    download_urls.append(dist['downloadURL'])
    return download_urls


git_list = get_list_of_gits(sys.argv[1])

for githuburl in git_list:
    githuburlsplit = githuburl.split('/')
    print('{}/{}'.format(githuburlsplit[-2], githuburlsplit[-1]))
