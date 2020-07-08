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

from neutron.common import rpc as n_rpc
from neutron.agent.linux import ip_lib
from neutron_lib.agent import l3_extension
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging

LOG = logging.getLogger(__name__)


class EcmpL3PluginApi(object):
    """ Agent side of the ecmp agent to ecmp Plugin RPC API."""
    def __init__(self, topic, host):

        self.host = host
        target = oslo_messaging.Target(topic=topic, version='1.0')
        self.client = n_rpc.get_client(target)

    def get_route_of_router(self, context, router_id):
        """ Get ecmp route of router"""
        cctxt = self.client.prepare()
        return cctxt.call(context, 'get_route_of_router', router_id=router_id, host=self.host)


class ECMPL3AgentExtension(l3_extension.L3AgentExtension):
    """ECMP Agent support to be used by Neutron L3 agent."""
    def initialize(self, connection, driver_type):
        self._register_rpc_consumers(connection)

    def consume_api(self, agent_api):
        LOG.debug("Ecmp consume_api call occurred with %s", agent_api)
        self.agent_api = agent_api

    def _register_rpc_consumers(self, connection):
        #TODO(njohnston): Add RPC consumer connection loading here.
        pass

    def start_rpc_listeners(self, conf):
        self.endpoints = [self]
        self.conn = n_rpc.Connection()
        self.conn.create_consumer('ecmp_agent', self.endpoints, fanout=False)
        return self.conn.consume_in_threads()

    def __init__(self, host, conf):
        LOG.info("Initializing ECMP agent")
        self.agent_api = None
        self.conf = conf

        self.start_rpc_listeners(conf)
        self.ecmpplugin_rpc = EcmpL3PluginApi('q-ecmp-plugin', host)

    def _get_router_info_for_router_id(self, router_id):
        """Returns the  router info object on which to apply the ecmp."""
        if self.agent_api is None:
            LOG.exception("ECMP RPC call failed; L3 agent_api failure")
        return self.agent_api.get_router_info(router_id)

    def update_ecmp_route(self, context, ecmproute, host):
        LOG.info('Get notify from plugin to update ecmp route : %s', ecmproute)
        router_info = self._get_router_info_for_router_id(ecmproute['router_id'])
        if router_info:

            operation = ecmproute['operation']
            if operation == 'delete':
                cmd = ['ip', 'route', 'delete', 'to', ecmproute['vip']]
            else:
                cmd = ['ip', 'route', 'replace', 'to', ecmproute['vip']]
                for nexthop in ecmproute['next_hops']:
                    cmd.append('nexthop')
                    cmd.append('via')
                    cmd.append(nexthop)
            LOG.debug('ecmp route cmd : %s', cmd)
            router_ns = router_info.ns_name
            LOG.debug('the router namespace is %s', router_ns)
            ip_wrapper = ip_lib.IPWrapper(namespace=router_ns)
            ip_wrapper.netns.execute(cmd, check_exit_code=False)
            set_proxy_parameter_qrs = ecmproute.get('set_arp_proxy_qrs')
            if set_proxy_parameter_qrs:
                LOG.debug('set proxy parameter to 1 for %s', set_proxy_parameter_qrs)
                for qr in set_proxy_parameter_qrs:
                    cmd = ['sysctl', '-w', 'net.ipv4.conf.%s.proxy_arp=1' % qr]
                    ip_wrapper.netns.execute(cmd, check_exit_code=False)
                    cmd = ['sysctl', '-w', 'net.ipv4.conf.%s.proxy_arp_pvlan=1' % qr]
                    ip_wrapper.netns.execute(cmd, check_exit_code=False)

            unset_proxy_parameter_qrs = ecmproute.get('unset_arp_proxy_qrs')
            if unset_proxy_parameter_qrs:
                LOG.debug('set proxy parameter to 0 for %s', unset_proxy_parameter_qrs)
                for qr in unset_proxy_parameter_qrs:
                    cmd = ['sysctl', '-w', 'net.ipv4.conf.%s.proxy_arp=0' % qr]
                    ip_wrapper.netns.execute(cmd, check_exit_code=False)
                    cmd = ['sysctl', '-w', 'net.ipv4.conf.%s.proxy_arp_pvlan=0' % qr]
                    ip_wrapper.netns.execute(cmd, check_exit_code=False)

    def add_router(self, context, data):
        router_id = data['id']
        ecmp_routes = self.ecmpplugin_rpc.get_route_of_router(context, router_id)
        LOG.debug("this router's ecmp_route : %s", ecmp_routes)
        if ecmp_routes:
            router_info = self._get_router_info_for_router_id(router_id)
            router_ns = router_info.ns_name
            ip_wrapper = ip_lib.IPWrapper(namespace=router_ns)
            qr_interfaces = []
            for route in ecmp_routes:
                cmd = ['ip', 'route', 'replace', 'to', route['vip']]
                for nexthop in route['next_hops']:
                    cmd.append('nexthop')
                    cmd.append('via')
                    cmd.append(nexthop)
                ip_wrapper.netns.execute(cmd, check_exit_code=False)
                qr_interfaces.extend(route['qr_interfaces'])
            LOG.debug("add_router in ecmp to set qr interfaces %s", qr_interfaces)
            for qr in set(qr_interfaces):
                cmd = ['sysctl', '-w', 'net.ipv4.conf.%s.proxy_arp=1' % qr]
                ip_wrapper.netns.execute(cmd, check_exit_code=False)
                cmd = ['sysctl', '-w', 'net.ipv4.conf.%s.proxy_arp_pvlan=1' % qr]
                ip_wrapper.netns.execute(cmd, check_exit_code=False)

    def update_router(self, context, updated_router):
        """The update_router method is just a synonym for add_router"""
        pass


    def delete_router(self, context, new_router):
        pass

    def ha_state_change(self, context, data):
        pass


class L3withECMP(ECMPL3AgentExtension):
    def __init__(self, conf=None):
        if conf:
            self.conf = conf
        else:
            self.conf = cfg.CONF
        super(L3withECMP, self).__init__(host=self.conf.host, conf=self.conf)



