# Copyright 2019 Inspur Cloud Service Group.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import neutron.conf.services.provider_configuration

import neutron_ecmp.agent.acl.acl_agent_api
import neutron_ecmp.extensions.acl


def list_agent_opts():
    return [('acl', neutron_ecmp.agent.acl.acl_agent_api.ACLOpts), ]


def list_opts():
    return [('quotas', neutron_ecmp.extensions.acl.acl_quota_opts),
            ('service_providers', neutron.conf.services.provider_configuration.serviceprovider_opts), ]
