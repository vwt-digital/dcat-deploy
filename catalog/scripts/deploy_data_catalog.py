# To run this script, a variable catalog should be defined, containing the data catalog to be deployed by
# this deployment template.
import re
from datetime import timedelta


def find_topic(dataset):
    for distribution in dataset['distribution']:
        if distribution['format'] == 'topic':
            return distribution['title']
    return None


def update_bindings(bindings, role_to_add, member_to_add):
    if not bindings:
        bindings = []

    binding = next((b for b in bindings if b['role'] == role_to_add), None)
    if not binding:
        binding = {
            'role': role_to_add,
            'members': []
        }
        bindings.append(binding)

    if member_to_add not in binding['members']:
        binding['members'].append(member_to_add)

    return bindings


resource_default_policy_bindings = {
    'blob-storage': {
        'public': [
            {
                'role': 'roles/storage.legacyBucketOwner',
                'members': [
                    'projectEditor:{project_id}',
                    'projectOwner:{project_id}'
                ]
            },
            {
                'role': 'roles/storage.legacyObjectOwner',
                'members': [
                    'projectEditor:{project_id}',
                    'projectOwner:{project_id}'
                ]
            },
            {
                'role': 'roles/storage.legacyObjectReader',
                'members': [
                    'projectViewer:{project_id}',
                    'allUsers'
                ]
            },
            {
                'role': 'roles/storage.legacyBucketReader',
                'members': [
                    'projectViewer:{project_id}',
                    'allUsers'
                ]
            }
        ],
        'internal': [
            {
                'role': 'roles/storage.legacyBucketOwner',
                'members': [
                    'projectEditor:{project_id}',
                    'projectOwner:{project_id}'
                ]
            },
            {
                'role': 'roles/storage.legacyObjectOwner',
                'members': [
                    'projectEditor:{project_id}',
                    'projectOwner:{project_id}'
                ]
            },
            {
                'role': 'roles/storage.legacyObjectReader',
                'members': [
                    'projectViewer:{project_id}'
                ]
            },
            {
                'role': 'roles/storage.legacyBucketReader',
                'members': [
                    'projectViewer:{project_id}'
                ]
            }
        ],
        'restricted': [
            {
                'role': 'roles/storage.legacyBucketOwner',
                'members': [
                    'projectEditor:{project_id}',
                    'projectOwner:{project_id}'
                ]
            },
            {
                'role': 'roles/storage.legacyObjectOwner',
                'members': [
                    'projectEditor:{project_id}',
                    'projectOwner:{project_id}'
                ]
            },
            {
                'role': 'roles/storage.legacyObjectReader',
                'members': [
                    'projectViewer:{project_id}'
                ]
            },
            {
                'role': 'roles/storage.legacyBucketReader',
                'members': [
                    'projectViewer:{project_id}'
                ]
            }
        ],
        'confidential': [
        ]
    },
    'topic': {
        'public': None,
        'internal': None,
        'restricted': None,
        'confidential': None
    },
    'subscription': {
    }
}


resource_odrl_policy_bindings = {
    'blob-storage': {
        'read': [
            'roles/storage.legacyBucketReader',
            'roles/storage.legacyObjectReader'
        ],
        'write': [
            'roles/storage.legacyBucketWriter',
            'roles/storage.legacyObjectOwner'
        ],
        'modify': [
            'roles/storage.legacyBucketOwner',
            'roles/storage.legacyObjectOwner'
        ]
    },
    'topic': {
        'read': [
            'roles/pubsub.subscriber'
        ],
        'write': [
            'roles/pubsub.publisher'
        ],
        'modify': [
            'roles/pubsub.editor'
        ]
    },
    'subscription': {
        'read': [
            'roles/pubsub.subscriber'
        ],
        'write': [],
        'modify': []
    }
}

excluded_odrl_policy_bindings = {
    'bigquery-dataset': {
        'read': [
            'roles/bigquery.dataViewer'
        ],
        'modify': [
            'roles/bigquery.dataEditor'
        ]
    }
}


def gather_odrl_policy_roles_to_add(resource_format, action):
    if resource_format in resource_odrl_policy_bindings:
        return resource_odrl_policy_bindings[resource_format].get(action, [])
    else:
        return []


def gather_permissions(access_level, resource_title, resource_format, project_id, odrlPolicy):
    bindings_per_level = resource_default_policy_bindings.get(resource_format, None)
    bindings = None

    if bindings_per_level:
        bindings = bindings_per_level[access_level]

    if odrlPolicy:
        for permission in odrlPolicy.get('permission', []):
            target = permission.get('target')
            if target == resource_title and target != excluded_odrl_policy_bindings.get(target):
                for role_to_add in gather_odrl_policy_roles_to_add(resource_format, permission['action']):
                    if not bindings:
                        bindings = []
                    binding = next((b for b in bindings if b['role'] == role_to_add), None)
                    if not binding:
                        binding = {
                            'role': role_to_add,
                            'members': []
                        }
                        bindings.append(binding)
                    if not permission['assignee'] in binding['members']:
                        binding['members'].append(permission['assignee'])

    if bindings is not None:
        for binding in bindings:
            binding['members'] = [member.format(project_id=project_id) for member in binding['members']]

        return bindings
    else:
        return None


# Note: bigquery still uses legacy access property to set permissions
# https://github.com/GoogleCloudPlatform/deploymentmanager-samples/issues/502
def get_bigquery_access_policy(resource, odrlPolicy):
    access_policy = []
    for permission in odrlPolicy.get('permission', []):
        if permission['target'] == resource['title']:
            if 'serviceAccount' in permission['assignee'] or 'user' in permission['assignee']:
                access_policy.append({
                    'role': excluded_odrl_policy_bindings[resource['format']]['action'],
                    'userByEmail': permission['assignee'].split(':')[1]
                })
            elif 'group' in permission['assignee']:
                access_policy.append({
                    'role': excluded_odrl_policy_bindings[resource['format']]['action'],
                    'groupByEmail': permission['assignee'].split(':')[1]
                })
    return access_policy


def append_gcp_policy(resource, resource_title, resource_format, access_level, project_id, odrlPolicy):
    permissions = gather_permissions(access_level, resource_title, resource_format, project_id, odrlPolicy)
    if permissions is not None:
        resource['accessControl'] = {
            'gcpIamPolicy': {
                'bindings': permissions
            }
        }


def gather_bucket_lifecycle(temporal):
    print('temporal {}'.format(temporal))
    if temporal and temporal.startswith('P'):
        duration = parse_duration(temporal)
        return {
            'rule': [
                {
                    'action': {
                        'type': 'Delete'
                    },
                    'condition': {
                        'age': duration.days
                    }
                }
            ]
        }
    else:
        return {}


def gather_bucket_retentionPolicy(temporal):
    print('temporal {}'.format(temporal))
    if temporal and temporal.startswith('P'):
        retentionPeriod = parse_duration(temporal)
        return {
            'retentionPeriod': int(retentionPeriod.total_seconds())
        }
    else:
        return {}


def generate_config(context):
    resources = []
    project_level_bindings = []

    for dataset in catalog['dataset']:  # noqa: F821
        for distribution in dataset['distribution']:
            resource_to_append = None
            if distribution['format'] == 'blob-storage':
                resource_to_append = {
                        'name': distribution['title'],
                        'type': 'storage.v1.bucket'
                    }
                resource_to_append['properties'] = {}
                if 'deploymentZone' in distribution:
                    resource_to_append['properties'].update({
                        'location': distribution['deploymentZone']
                    })
                if 'accessLevel' in dataset:
                    resource_to_append['properties'].update({
                        'iamConfiguration': {
                            'bucketPolicyOnly': {'enabled': True}
                        }
                    })
                resource_to_append['properties']['lifecycle'] = gather_bucket_lifecycle(dataset.get('temporal', ''))
                resource_to_append['properties']['retentionPolicy'] = gather_bucket_retentionPolicy(dataset.get('temporal', ''))
            if distribution['format'] == 'topic':
                resource_to_append = {
                    'name': distribution['title'],
                    'type': 'pubsub.v1.topic',
                    'properties':
                        {
                            'topic': distribution['title']
                        }
                }
                if 'odrlPolicy' in dataset:
                    for permission in dataset['odrlPolicy']['permission']:
                        if permission['target'] == distribution['title'] and permission['action'] == 'modify':
                            # topic modify requires pubsub.editor at project level
                            project_level_bindings = update_bindings(project_level_bindings, 'roles/pubsub.editor', permission['assignee'])
            if distribution['format'] == 'subscription':
                resource_to_append = {
                    'name': distribution['title'],
                    'type': 'pubsub.v1.subscription',
                    'properties': {
                        'topic': '$(ref.'+find_topic(dataset)+'.name)',
                        'subscription': distribution['title']
                    },
                    'metadata': {
                        'dependsOn': [find_topic(dataset)]
                    }
                }
                if distribution.get('deploymentProperties'):
                    resource_to_append['properties'].update(distribution['deploymentProperties'])
            if distribution['format'] == 'cloudsql-instance':
                resource_to_append = {
                    'name': distribution['title'],
                    'type': 'gcp-types/sqladmin-v1beta4:instances'
                }
            if distribution['format'] == 'cloudsql-db':
                resource_to_append = {
                    'name': distribution['title'],
                    'type': 'gcp-types/sqladmin-v1beta4:databases',
                    'properties': distribution['deploymentProperties'],
                    'metadata': {
                        'dependsOn': [distribution['deploymentProperties']['instance']]
                    }
                }
            if distribution['format'] == 'bigquery-dataset':
                resource_to_append = {
                    'name': distribution['title'],
                    'type': 'gcp-types/bigquery-v2:datasets',
                    'properties': {
                        'datasetReference':
                            {
                                'datasetId': distribution['title'],
                                'projectId': catalog['projectId']  # noqa: F821
                            },
                        'location': distribution['deploymentZone'],
                        'access': get_bigquery_access_policy(distribution, dataset.get('odrlPolicy'))
                    }
                }

            if resource_to_append:
                # Add deployment properties, unless it's a subscription as pushConfig is not updatable through Deployment Manager (DAT-816)
                if 'deploymentProperties' in distribution and distribution['format'] != 'subscription':
                    if 'properties' not in resource_to_append:
                        resource_to_append['properties'] = {}
                    resource_to_append['properties'].update(distribution['deploymentProperties'])

                if 'accessLevel' in dataset:
                    append_gcp_policy(resource_to_append, distribution['title'], distribution['format'], dataset['accessLevel'],
                                      context.env['project'], dataset.get('odrlPolicy'))

                resources.append(resource_to_append)

    if project_level_bindings:
        resources.append({
            'name': 'get-iam-policy-' + context.env['project'],
            'action': 'gcp-types/cloudresourcemanager-v1:cloudresourcemanager.projects.getIamPolicy',
            'properties': {
                'resource': context.env['project'],
            },
            'metadata': {
                'runtimePolicy': ['UPDATE_ALWAYS']
            }
        })
        resources.append({
            'name': 'patch-iam-policy-' + context.env['project'],
            'action': 'gcp-types/cloudresourcemanager-v1:cloudresourcemanager.projects.setIamPolicy',
            'properties': {
                'resource': context.env['project'],
                'policy': '$(ref.get-iam-policy-' + context.env['project'] + ')',
                'gcpIamPolicyPatch': {
                    'add': project_level_bindings
                }
            }
        })

    return {'resources': resources}


# Code below is a modified version of duration calculation of isodate package.
# (https://github.com/gweis/isodate)
# Original copyright notice:
##############################################################################
# Copyright 2009, Gerhard Weis
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT
##############################################################################


ISO8601_PERIOD_REGEX = re.compile(
    r"^(?P<sign>[+-])?"
    r"P(?!\b)"
    r"(?P<years>[0-9]+([,.][0-9]+)?Y)?"
    r"(?P<months>[0-9]+([,.][0-9]+)?M)?"
    r"(?P<weeks>[0-9]+([,.][0-9]+)?W)?"
    r"(?P<days>[0-9]+([,.][0-9]+)?D)?"
    r"((?P<separator>T)(?P<hours>[0-9]+([,.][0-9]+)?H)?"
    r"(?P<minutes>[0-9]+([,.][0-9]+)?M)?"
    r"(?P<seconds>[0-9]+([,.][0-9]+)?S)?)?$")
# regular expression to parse ISO duartion strings.


def parse_duration(datestring):
    """
    Parses an ISO 8601 durations into datetime.timedelta.
    The implementation handles a year's duration as 365 days and a
    month's duration as 30 days.

    The following duration formats are supported:
      -PnnW                  duration in weeks
      -PnnYnnMnnDTnnHnnMnnS  complete duration specification

    The '-' is optional.

    Limitations:  ISO standard defines some restrictions about where to use
      fractional numbers and which component and format combinations are
      allowed. This parser implementation ignores all those restrictions and
      returns something when it is able to find all necessary components.
      In detail:
        it does not check, whether only the last component has fractions.
        it allows weeks specified with all other combinations
    """
    if not isinstance(datestring, str):
        raise TypeError("Expecting a string %r" % datestring)
    match = ISO8601_PERIOD_REGEX.match(datestring)
    if not match:
        raise ValueError("Expecting ISO8601 duration format, which is not %r" % datestring)
    groups = match.groupdict()
    for key, val in groups.items():
        if key not in ('separator', 'sign'):
            if val is None:
                groups[key] = '0n'
            print('groups {} val {}'.format(key, groups[key]))
            groups[key] = float(groups[key][:-1].replace(',', '.'))
    ret = timedelta(days=groups["days"]+(groups['years']*365)+(groups['months']*30), hours=groups["hours"],
                    minutes=groups["minutes"], seconds=groups["seconds"], weeks=groups["weeks"])
    if groups["sign"] == '-':
        ret = timedelta(0) - ret
    return ret
