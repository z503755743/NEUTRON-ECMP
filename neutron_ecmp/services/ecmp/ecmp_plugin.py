# Copyright 2019 Inspur Cloud Service Group.
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


import netaddr
from neutron_ecmp.db.ecmp import ecmp_db
from neutron_ecmp.api.definitions import ecmp as ecmp_ext
from neutron_ecmp.common import ecmp_exceptions as exception
from neutron import service
from neutron.common import rpc as n_rpc
from neutron_lib.plugins import constants as plugin_constants
from neutron_lib.plugins import directory
from oslo_config import cfg
import oslo_messaging
from oslo_log import log as logging

LOG = logging.getLogger(__name__)

ECMP_AGENT = 'ecmp_agent'
ECMP_PLUGIN = 'q-ecmp-plugin'
LINUX_DEV_LEN = 14
INTERNAL_DEV_PREFIX = 'qr-'

class EcmpAgentApi(object):
    """Plugin side of plugin to agent RPC API"""

    def __init__(self, topic, host):
        self.host = host
        target = oslo_messaging.Target(topic=topic, version='1.0')
        self.client = n_rpc.get_client(target)

    def _prepare_rpc_client(self, host=None):
        if host:
            return self.client.prepare(server=host)
        else:
            # historical behaviour (RPC broadcast)
            return self.client.prepare(fanout=True)

    def update_ecmp_route(self, context, ecmproute, host=None):
        cctxt = self._prepare_rpc_client(host)
        cctxt.cast(context, 'update_ecmp_route', ecmproute=ecmproute, host=self.host)


class EcmpPlugin(ecmp_db.Ecmp_db_mixin):
    """ECMP service plugin class"""
    supported_extension_aliases = [ecmp_ext.ALIAS]


    def __init__(self):
        """Do the initialization for the ecmp service plugin here."""
        LOG.info("Initializing ECMP plugin")
        self.agent_rpc = EcmpAgentApi(ECMP_AGENT, cfg.CONF.host)
        ecmp_db.subscribe()
        rpc_worker = service.RpcWorker([self], worker_process_count=0)
        self.add_worker(rpc_worker)

    def start_rpc_listeners(self):
        self.endpoints = [self]
        self.conn = n_rpc.Connection()
        self.conn.create_consumer(ECMP_PLUGIN, self.endpoints, fanout=False)
        return self.conn.consume_in_threads()

    def _get_hosts_to_notify(self, context, router_id):
        """Notify changed routers to hosting l3 agents."""
        adminContext = context if context.is_admin else context.elevated()
        l3_plugin = directory.get_plugin(plugin_constants.L3)
        hosts = l3_plugin.get_hosts_to_notify(adminContext, router_id)
        return hosts

    def _rpc_notify_ecmp_route(self, context, operation, vip, next_hops, router_id, related_qr_interfaces=None, unused_qr_interfaces=None):
        data = {'router_id': router_id,
                'vip': vip,
                'next_hops': next_hops,
                'operation': operation,
                'set_arp_proxy_qrs': related_qr_interfaces,
                'unset_arp_proxy_qrs': unused_qr_interfaces}
        hosts = self._get_hosts_to_notify(context, router_id)
        for host in hosts:
            LOG.debug('ecmp: start notify host %s to update ecmproute %s', host, data)
            self.agent_rpc.update_ecmp_route(context, data, host=host)

    def _get_router_qr_name(self, port_id):
        return (INTERNAL_DEV_PREFIX + port_id)[:LINUX_DEV_LEN]

    def _get_router_gw_port_with_cidr(self, context, router_id):
        context = context.elevated()
        filters = {'device_id': [router_id], 'device_owner': ['network:router_interface_distributed']}
        ports = self._core_plugin.get_ports(context, filters)
        router_subnet = []
        for port in ports:
            for ip in port['fixed_ips']:
                cidr = self._core_plugin.get_subnet(
                    context, ip['subnet_id'])['cidr']
                subnet = {'cidr': netaddr.IPNetwork(cidr),
                          'port_id': port['id']}
                router_subnet.append(subnet)
        LOG.debug('Test the router_subnet is %s', router_subnet)
        return router_subnet

    def _validate_next_hops(self, context, router_id, add_next_hops, router_subnet):
        next_hops_gw_ports = set()
        for next_hop_ip in add_next_hops:
            ip = netaddr.IPAddress(next_hop_ip)
            for rs in router_subnet:
                if ip in rs['cidr']:
                    next_hops_gw_ports.add(rs['port_id'])
                    break
            else:
                raise exception.EcmpInvalidRoutes(next_hop=next_hop_ip, router_id=router_id)
        LOG.debug('Test the next_hop related router gw port is %s', next_hops_gw_ports)
        return next_hops_gw_ports

    def _get_unused_qr_from_remove_next_hops(self, context, router_id, remove_next_hops, router_subnet):
        all_next_hops = self._get_all_next_hop_ips_of_router(context, router_id)
        all_related_qr_port = set()
        for next_hop in set(all_next_hops):
            ip = netaddr.IPAddress(next_hop)
            for rs in router_subnet:
                if ip in rs['cidr']:
                    all_related_qr_port.add(rs['port_id'])
                    break
        remove_related_qr_port = set()
        for remove_next_hop in remove_next_hops:
            remove_ip = netaddr.IPAddress(remove_next_hop)
            for rs in router_subnet:
                if remove_ip in rs['cidr']:
                    remove_related_qr_port.add(rs['port_id'])
                    break
        unused_qr_interface = []
        unused_qr_port = remove_related_qr_port - all_related_qr_port

        for port in unused_qr_port:
            unused_qr_interface.append(self._get_router_qr_name(port))
        LOG.debug('The ecmp unsed qr port is %s', unused_qr_interface)
        return unused_qr_interface

    def create_ecmp_route(self, context, ecmp_route):
        LOG.debug('start create ecmp route : %s', ecmp_route)
        next_hops = ecmp_route['ecmp_route'].get('next_hops', [])
        router_id = ecmp_route['ecmp_route'].get('router_id')
        router_port_with_cidr = self._get_router_gw_port_with_cidr(context, router_id)
        next_hops_gw_ports = self._validate_next_hops(context, router_id, next_hops, router_port_with_cidr)
        ecmp_r = super(EcmpPlugin, self).create_ecmp_route(context, ecmp_route)
        related_qr_interfaces = []
        for port in next_hops_gw_ports:
            related_qr_interfaces.append(self._get_router_qr_name(port))
        self._rpc_notify_ecmp_route(context, 'replace', ecmp_r['vip'], next_hops, router_id,
                                    related_qr_interfaces=related_qr_interfaces)
        return ecmp_r

    def update_ecmp_route(self, context, id, ecmp_route):
        LOG.debug('start update ecmp route : %s', ecmp_route)
        new_next_hops = ecmp_route['ecmp_route'].get('next_hops', [])
        if new_next_hops:
            old_ecmproute = self._get_ecmproute(context, id)
            old_next_hops = old_ecmproute['next_hops'].split(',')
            added = set(new_next_hops) - set(old_next_hops)
            removed = set(old_next_hops) - set(new_next_hops)
            vip = old_ecmproute['vip']
            router_id = old_ecmproute['router_id']

            router_port_with_cidr = self._get_router_gw_port_with_cidr(context, router_id)
            next_hops_gw_ports = self._validate_next_hops(context, router_id, added, router_port_with_cidr)

            ecmproute_db = super(EcmpPlugin, self).update_ecmp_route(context, id, ecmp_route)
            #new_next_hops.sort()
            related_qr_interfaces = []
            for port in next_hops_gw_ports:
                related_qr_interfaces.append(self._get_router_qr_name(port))

            unused_qr_interfaces = self._get_unused_qr_from_remove_next_hops(context, router_id, removed,
                                                                            router_port_with_cidr)

            self._rpc_notify_ecmp_route(context, 'replace', vip, new_next_hops, router_id,
                                        related_qr_interfaces=related_qr_interfaces,
                                        unused_qr_interfaces=unused_qr_interfaces)
            return ecmproute_db

    def get_ecmp_route(self, context, id, fields=None):
        return super(EcmpPlugin, self).get_ecmp_route(context, id, fields)

    def get_ecmp_routes(self, context, filters=None, fields=None):
        return super(EcmpPlugin, self).get_ecmp_routes(context, filters, fields)

    def delete_ecmp_route(self, context, id):
        LOG.debug('start delete ecmp route : %s', id)
        ecmp_r = self._get_ecmproute(context, id)
        router_id = ecmp_r['router_id']
        next_hops = ecmp_r['next_hops'].split(',')
        super(EcmpPlugin, self).delete_ecmp_route(context, id)

        router_port_with_cidr = self._get_router_gw_port_with_cidr(context, router_id)
        unused_qr_interfaces = self._get_unused_qr_from_remove_next_hops(context, router_id, next_hops,
                                                                        router_port_with_cidr)
        self._rpc_notify_ecmp_route(context, 'delete', ecmp_r['vip'], next_hops, router_id,
                                    unused_qr_interfaces=unused_qr_interfaces)

    def _get_qr_interface(self, context, netxt_hops, router_id):
        router_port_with_cidr = self._get_router_gw_port_with_cidr(context, router_id)
        next_hops_gw_ports = set()
        for next_hop_ip in netxt_hops:
            ip = netaddr.IPAddress(next_hop_ip)
            for rs in router_port_with_cidr:
                if ip in rs['cidr']:
                    next_hops_gw_ports.add(rs['port_id'])
                    break

        qr_interfaces = []
        for port in next_hops_gw_ports:
            qr_interfaces.append(self._get_router_qr_name(port))
        return qr_interfaces

    def check_router_interface_not_in_use(self, **kwargs):
        context = kwargs.get('context')
        router_id = kwargs.get('router_id')
        subnet_id = kwargs.get('subnet_id')
        subnet = self._core_plugin.get_subnet(context, subnet_id)
        subnet_cidr = netaddr.IPNetwork(subnet['cidr'])
        all_next_hops = self._get_all_next_hop_ips_of_router(context, router_id)
        for next_hop_ip in set(all_next_hops):
            if netaddr.all_matching_cidrs(next_hop_ip, [subnet_cidr]):
                raise exception.RouterInterfaceInUseBySlbEcmp(
                    router_id=router_id, subnet_id=subnet_id)


    def get_route_of_router(self, context, router_id, host):
        LOG.debug('get rpc call from %s to get ecmp route of router %s', host, router_id)
        ecmpdb = self._get_ecmproute_by_router_id(context, router_id)
        ecmp_route = []
        for ecmpr in ecmpdb:
            next_hop = ecmpr['next_hops'].split(',')
            qr_interfaces = self._get_qr_interface(context, next_hop, router_id)
            data = {'vip': ecmpr['vip'],
                    'next_hops': next_hop,
                    'qr_interfaces': qr_interfaces}
            ecmp_route.append(data)
        return ecmp_route

