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

from tempest.api.network import base
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators


class AclsTest(base.BaseNetworkTest):

    @classmethod
    def resource_setup(cls):
        super(AclsTest, cls).resource_setup()
        cls.network = cls.create_network()
        cls.subnet = cls.create_subnet(cls.network)
        cls.router = cls.create_router()

    def _create_acl_policy(self):
        # create a acl policy
        name = data_utils.rand_name('AclPolicy-')
        network_id = self.network['id']
        vpc_name = self.network['name']
        status = '1'
        kw={'name': name, 'network_id': network_id, 'vpc_name': vpc_name, 'status': status}
        acl_policy_body = self.acls_client.create_acl_policy(**kw)
        self.addCleanup(self._delete_acl_policy, acl_policy_body['acl_policy']['id'])
        return acl_policy_body['acl_policy']

    def _delete_acl_policy(self, acl_policy_id):
        # Asserting that the acl policy is not found in the list after deletion
        self.acls_client.delete_acl_policy(acl_policy_id)
        body = self.acls_client.list_acl_policies()
        acl_policies_lists = body['acl_policies']
        self.assertNotIn(acl_policy_id, [n['id'] for n in acl_policies_lists])

    def _delete_acl_policy_rule(self, acl_policy_rule_id):
        # Asserting that the acl policy rule is not found in the list after deletion
        self.acls_client.delete_acl_rule(acl_policy_rule_id)
        body = self.acls_client.list_acl_rules()
        self.assertNotIn(acl_policy_rule_id, [n['id'] for n in body['acl_rules']])

    def _delete_acl_bindings(self, acl_bings_id):
        # Asserting that the acl binding is not found in the list after deletion
        self.acls_client.delete_acl_binding(acl_bings_id)
        body = self.acls_client.list_acl_bindings()
        self.assertNotIn(acl_bings_id, [n['id'] for n in body['acl_bindings']])

    @decorators.idempotent_id('691ffb85-f7ce-4f93-a8db-c232854691c0')
    def test_create_list_update_show_delete_acl_policy(self):
        # create the acl policy
        acl_policy = self._create_acl_policy()
        self.assertEqual(acl_policy['network_id'], self.network['id'])
        self.assertEqual(acl_policy['admin_state_up'], '1')

        # List acl_policies and verify if created acl_policy is there in response
        list_acl_policies = self.acls_client.list_acl_policies()
        aclpolicy_list = []
        for aclp in list_acl_policies['acl_policies']:
            aclpolicy_list.append(aclp['id'])
        self.assertIn(acl_policy['id'], aclpolicy_list)

        # Update the name of acl_policy and verify if it is updated
        name = 'updated' + acl_policy['name']
        des = 'acl_policy description'
        update_body = self.acls_client.update_acl_policy(acl_policy['id'], name=name, description=des)
        self.assertEqual(update_body['acl_policy']['name'], name)
        self.assertEqual(update_body['acl_policy']['description'], des)

        # show details of the updated acl_policy
        show_body = self.acls_client.show_acl_policy(acl_policy['id'])
        self.assertEqual(show_body['acl_policy']['name'], name)
        self.assertEqual(show_body['acl_policy']['description'], des)

    @decorators.idempotent_id('4deb4334-0ce2-48b8-ab1a-01bd0120bea9')
    def test_create_update_show_delete_acl_policy_rule(self):
        acl_policy = self._create_acl_policy()
        protocols = ['tcp', 'udp', 'icmp']
        for protocol in protocols:
            # create acl_rule with required parameter
            rule_create_body = self.acls_client.create_acl_rule(
                policy_id=acl_policy['id'],
                protocol=protocol,
                enabled=True,
                direction='ingress')
            self.addCleanup(self._delete_acl_policy_rule, rule_create_body['acl_rule']['id'])
            self.assertEqual(rule_create_body['acl_rule']['acl_policy_id'], acl_policy['id'])
            self.assertEqual(rule_create_body['acl_rule']['action'], 'deny')
            # update the direction of rule
            rule_update_body = self.acls_client.update_acl_rule(rule_create_body['acl_rule']['id'],
                                                                direction='egress')
            self.assertEqual(rule_update_body['acl_rule']['direction'], 'egress')
            # show created rules
            rule_show_body = self.acls_client.show_acl_rule(rule_create_body['acl_rule']['id'])
            update_dict = rule_update_body['acl_rule']
            # Asserting that the show rule
            for key, value in update_dict.items():
                if key != 'update_time':
                    self.assertEqual(value,
                                    rule_show_body['acl_rule'][key],
                                    "%s does not match." % key)

            # list rules and verify created rule is in response
            rule_list_body = self.acls_client.list_acl_rules()
            rule_list = [role['id'] for role in rule_list_body['acl_rules']]
            self.assertIn(rule_create_body['acl_rule']['id'], rule_list)

    @decorators.idempotent_id('a3ee876a-ad2c-48b0-95b5-07a2d23d6f38')
    def test_create_acl_policy_rule_with_additional_args(self):
        # Verify acl policy rule with additional arguments works.
        # source_port and source_ip_address
        acl_policy = self._create_acl_policy()
        acl_policy_id = acl_policy['id']
        protocol = 'tcp'
        direction = 'ingress'
        action = 'allow'
        enabled = True
        source_port = '60:70'
        source_ip_address = str(self.cidr)
        rule_create_body = self.acls_client.create_acl_rule(
            policy_id=acl_policy_id,
            protocol=protocol,
            direction=direction,
            action=action,
            source_port=source_port,
            enabled=enabled,
            source_ip_address=source_ip_address)
        self.addCleanup(self._delete_acl_policy_rule, rule_create_body['acl_rule']['id'])
        self.assertEqual(rule_create_body['acl_rule']['source_port'], '60:70')
        self.assertEqual(rule_create_body['acl_rule']['source_ip_address'], source_ip_address)

    @decorators.idempotent_id('bc109d2a-43fa-4a0f-b95c-b39b3d3785cd')
    def test_create_acl_policy_rule_with_insert(self):
        # test create acl policy rule with insert_before parameter
        acl_policy = self._create_acl_policy()
        acl_policy_id = acl_policy['id']
        protocol = 'tcp'
        enabled = True
        direction = 'ingress'
        first_rule_create = self.acls_client.create_acl_rule(
            policy_id=acl_policy_id,
            protocol=protocol,
            direction=direction,
            enabled=enabled)
        self.addCleanup(self._delete_acl_policy_rule, first_rule_create['acl_rule']['id'])
        first_acl_rules = self.acls_client.show_acl_policy(acl_policy_id)['acl_policy']['acl_rules']
        first_acl_rule_position = first_acl_rules.index(first_rule_create['acl_rule']['id'])
        insert_before = first_rule_create['acl_rule']['id']
        second_rule_create = self.acls_client.create_acl_rule(
            policy_id=acl_policy_id,
            protocol=protocol,
            direction=direction,
            enabled=enabled,
            insert_before=insert_before)
        self.addCleanup(self._delete_acl_policy_rule, second_rule_create['acl_rule']['id'])

        second_acl_rules = self.acls_client.show_acl_policy(acl_policy_id)['acl_policy']['acl_rules']
        second_acl_rule_position = second_acl_rules.index(second_rule_create['acl_rule']['id'])
        # Asserting that the second rule insert before the first rule
        self.assertEqual(second_acl_rule_position, first_acl_rule_position)

    @decorators.idempotent_id('891ffe2a-404d-4976-81eb-a36386d98b67')
    def test_create_show_list_delete_acl_binding(self):
        acl_policy = self._create_acl_policy()
        # create acl binding
        acl_binding_create_body = self.acls_client.create_acl_binding(
            acl_policy_id=acl_policy['id'],
            router_id=self.router['id'],
            network_id=self.network['id'],
            subnet_id=self.subnet['id'],
            status = '1')
        self.addCleanup(self._delete_acl_bindings, acl_binding_create_body['acl_binding']['id'])
        self.assertEqual(acl_binding_create_body['acl_binding']['acl_policy_id'], acl_policy['id'])
        # Show details of the acl binding
        acl_binding_show_body = self.acls_client.show_acl_binding(acl_binding_create_body['acl_binding']['id'])
        create_dict = acl_binding_create_body['acl_binding']
        for key, value in create_dict.items():
            if key != 'create_time':
                self.assertEqual(value,
                                acl_binding_show_body['acl_binding'][key],
                                "%s does not match." % key)

        # List acl bindings and verify created acl binding is in response
        acl_binding_list_body = self.acls_client.list_acl_bindings()
        aclb_list = [binding['id'] for binding in acl_binding_list_body['acl_bindings']]
        self.assertIn(acl_binding_create_body['acl_binding']['id'], aclb_list)
