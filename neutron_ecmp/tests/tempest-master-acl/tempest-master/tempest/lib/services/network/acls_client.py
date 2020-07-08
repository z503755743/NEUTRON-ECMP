from tempest.lib.services.network import base


class AclsClient(base.BaseNetworkClient):

    def create_acl_policy(self, **kwargs):
        uri = '/acl/acl_policies'
        post_data = {'acl_policy': kwargs}
        return self.create_resource(uri, post_data)

    def update_acl_policy(self, acl_policy_id, **kwargs):
        uri = '/acl/acl_policies/%s' % acl_policy_id
        post_data = {'acl_policy': kwargs}
        return self.update_resource(uri, post_data)

    def show_acl_policy(self, acl_policy_id, **fields):
        uri = '/acl/acl_policies/%s' % acl_policy_id
        return self.show_resource(uri, **fields)

    def list_acl_policies(self, **filters):
        uri = '/acl/acl_policies'
        return self.list_resources(uri, **filters)

    def delete_acl_policy(self, acl_policy_id):
        uri = '/acl/acl_policies/%s' % acl_policy_id
        return self.delete_resource(uri)

    def create_acl_rule(self, **kwargs):
        uri = '/acl/acl_rules'
        post_data = {'acl_rule': kwargs}
        return self.create_resource(uri, post_data)

    def update_acl_rule(self, acl_rule_id, **kwargs):
        uri = '/acl/acl_rules/%s' % acl_rule_id
        post_data = {'acl_rule': kwargs}
        return self.update_resource(uri, post_data)

    def show_acl_rule(self, acl_rule_id, **fields):
        uri = '/acl/acl_rules/%s' % acl_rule_id
        return self.show_resource(uri, **fields)

    def list_acl_rules(self, **filters):
        uri = '/acl/acl_rules'
        return self.list_resources(uri, **filters)

    def delete_acl_rule(self, acl_rule_id):
        uri = '/acl/acl_rules/%s' % acl_rule_id
        return self.delete_resource(uri)

    def create_acl_binding(self, **kwargs):
        uri = '/acl/acl_bindings'
        post_data = {'acl_binding': kwargs}
        return self.create_resource(uri, post_data)

    def delete_acl_binding(self, acl_binding_id):
        uri = '/acl/acl_bindings/%s' % acl_binding_id
        return self.delete_resource(uri)

    def list_acl_bindings(self, **filters):
        uri = '/acl/acl_bindings'
        return self.list_resources(uri, **filters)

    def show_acl_binding(self, acl_binding_id, **fields):
        uri = '/acl/acl_bindings/%s' % acl_binding_id
        return self.show_resource(uri, **fields)