# Copyright 2013 Huawei Technologies Co.,LTD.
# Copyright 2012 OpenStack Foundation
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

from tempest.lib import exceptions as lib_exc
from tempest.api.network import base
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators


class NegativeAclTest(base.BaseNetworkTest):

    @classmethod
    def resource_setup(cls):
        super(NegativeAclTest, cls).resource_setup()
        cls.network = cls.create_network()
        cls.subnet = cls.create_subnet(cls.network)
        cls.router = cls.create_router()

    def _create_acl_policy(self):
        # create a acl policy
        name = data_utils.rand_name('AclPolicy_')
        network_id = self.network['id']
        vpc_name = self.network['name']
        status = '1'
        kw = {'name': name, 'network_id': network_id, 'vpc_name': vpc_name, 'status': status}
        acl_policy_body = self.acls_client.create_acl_policy(**kw)
        self.addCleanup(self._delete_acl_policy, acl_policy_body['acl_policy']['id'])
        return acl_policy_body['acl_policy']

    def _delete_acl_policy(self, acl_policy_id):
        # Asserting that the acl policy is not found in the list after deletion
        self.acls_client.delete_acl_policy(acl_policy_id)
        body = self.acls_client.list_acl_policies()
        acl_policies_lists = body['acl_policies']
        self.assertNotIn(acl_policy_id, [n['id'] for n in acl_policies_lists])

    def _delete_acl_bindings(self, acl_bings_id):
        # Asserting that the acl binding is not found in the list after deletion
        self.acls_client.delete_acl_binding(acl_bings_id)
        body = self.acls_client.list_acl_bindings()
        self.assertNotIn(acl_bings_id, [n['id'] for n in body['acl_bindings']])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('f442a6a4-98f1-469d-9b91-36f3496b41e7')
    def test_create_acl_policy_miss_required_para(self):
        # Asserting that create acl_policy without network_id
        self.assertRaises(lib_exc.BadRequest,
                          self.acls_client.create_acl_policy,
                          name='miss_network_id',
                          vpc_name=self.network['name'],
                          status='1')
        # Asserting that create acl_policy without vpc_name
        self.assertRaises(lib_exc.BadRequest,
                          self.acls_client.create_acl_policy,
                          name='miss_vpc_name',
                          network_id=self.network['id'],
                          status='1')
        # Asserting that create acl_policy without status
        self.assertRaises(lib_exc.BadRequest,
                          self.acls_client.create_acl_policy,
                          name='miss_status',
                          network_id=self.network['id'],
                          vpc_name=self.network['name'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('1bfa81e3-e929-4404-b30f-b2c89908a1f2')
    def test_show_non_existent_acl_policy(self):
        non_existent_id = data_utils.rand_uuid()
        self.assertRaises(lib_exc.NotFound,
                          self.acls_client.show_acl_policy,
                          non_existent_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('e26c468b-4879-4279-9642-5247e1543d92')
    def test_delete_non_existent_acl_policy(self):
        non_existent_id = data_utils.rand_uuid()
        self.assertRaises(lib_exc.NotFound,
                          self.acls_client.delete_acl_policy,
                          non_existent_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('abb11d08-01d6-4873-afde-2acdf4d05278')
    def test_delete_in_use_acl_policy(self):
        # test delete a acl_policy that is in use
        acl_policy = self._create_acl_policy()
        acl_binding_create_body = self.acls_client.create_acl_binding(
            acl_policy_id=acl_policy['id'],
            router_id=self.router['id'],
            network_id=self.network['id'],
            subnet_id=self.subnet['id'],
            status='1')
        self.addCleanup(self._delete_acl_bindings, acl_binding_create_body['acl_binding']['id'])
        self.assertRaises(lib_exc.Conflict,
                          self.acls_client.delete_acl_policy,
                          acl_policy['id'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('2c2330a3-1961-4886-b32a-4af490836316')
    def test_create_acl_rule_with_invalid_icmp_para(self):
        # source_port or destination_port are not allowed when protocol is icmp
        acl_policy = self._create_acl_policy()
        self.assertRaises(lib_exc.BadRequest, self.acls_client.create_acl_rule,
                          policy_id=acl_policy['id'],
                          protocol='icmp',
                          enabled=True,
                          source_port='60:70')

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('be8e440a-7298-4f7b-87a4-d69df6c31a94')
    def test_create_acl_rule_with_conflict_ipversion(self):
        # Invalid input - IP addresses do not agree with IP Version.
        acl_policy = self._create_acl_policy()
        self.assertRaises(lib_exc.BadRequest, self.acls_client.create_acl_rule,
                          policy_id=acl_policy['id'],
                          protocol='tcp',
                          enabled=True,
                          direction='ingress',
                          ip_version='6',
                          source_ip_address='10.10.1.0/24')

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('c6cc69d1-e32d-49d7-b0c2-baf691cd2327')
    def test_create_acl_rule_with_port_without_protocol(self):
        # Source/destination port requires a protocol.
        acl_policy = self._create_acl_policy()
        self.assertRaises(lib_exc.BadRequest, self.acls_client.create_acl_rule,
                          policy_id=acl_policy['id'],
                          enabled=True,
                          source_port='60:70')

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('7ed429ba-c62f-411b-b526-7e353562dcf7')
    def test_create_acl_rule_with_ref_acl_with_diff_policy(self):
        # the acl_policy_id of insert_before rule and this rule is different
        ref_acl_policy = self._create_acl_policy()
        this_acl_policy = self._create_acl_policy()
        ref_rule = self.acls_client.create_acl_rule(
                    policy_id=ref_acl_policy['id'],
                    protocol='icmp',
                    enabled=True,
                    direction='ingress')
        self.addCleanup(self.acls_client.delete_acl_rule, ref_rule['acl_rule']['id'])
        self.assertRaises(lib_exc.BadRequest, self.acls_client.create_acl_rule,
                          policy_id=this_acl_policy['id'],
                          protocol='icmp',
                          enabled=True,
                          direction='ingress',
                          insert_before=ref_rule['acl_rule']['id'])