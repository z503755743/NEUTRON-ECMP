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


from oslo_log import log as logging
from oslo_utils import uuidutils

import sqlalchemy as sa
from sqlalchemy.orm import exc
from neutron.db import common_db_mixin as base_db
from neutron_ecmp.common import ecmp_exceptions as exception
from neutron_ecmp.extensions.ecmp import EcmpPluginBase
from neutron_lib.plugins import directory
from neutron_lib.db import model_base
from neutron_lib.callbacks import events
from neutron_lib.callbacks import registry
from neutron_lib.callbacks import resources

LOG = logging.getLogger(__name__)

class EcmpRoute(model_base.BASEV2, model_base.HasId, model_base.HasProject):
    """Represents a  ecmproute."""

    # metadata for db
    __tablename__ = 'ecmproutes'
    __table_args__ = ({'mysql_collate': 'utf8_bin'})

    vip = sa.Column(sa.String(46))
    next_hops = sa.Column(sa.String(255))
    router_id = sa.Column(sa.String(36),
                          sa.ForeignKey('routers.id', ondelete="CASCADE"),
                          nullable=False)


class Ecmp_db_mixin(EcmpPluginBase, base_db.CommonDbMixin):
    """Mixin class for ecmp DB implementation."""

    @property
    def _core_plugin(self):
        return directory.get_plugin()

    def _make_ecmp_route_dict(self, ecmp_route, fields=None):
        next_hops_str = ecmp_route['next_hops']

        next_hops_list = next_hops_str.split(',')
        LOG.debug('ecmp: the next_hop string is %s, list is %s', next_hops_str, next_hops_list)
        res = {'id': ecmp_route['id'],
               'tenant_id': ecmp_route['tenant_id'],
               'vip': ecmp_route['vip'],
               'next_hops': next_hops_list,
               'router_id': ecmp_route['router_id']}
        return self._fields(res, fields)

    def _get_ecmproute(self, context, id):
        try:
            return self._get_by_id(context, EcmpRoute, id)
        except exc.NoResultFound:
            raise exception.EcmprouteNotFound(id=id)

    def _get_ecmproute_by_router_id(self, context, router_id):
        query = context.session.query(EcmpRoute)
        query1 = query.filter(EcmpRoute.router_id == router_id).all()
        return query1

    def _get_ecmproute_count_of_router(self, context, router_id):
        query = context.session.query(EcmpRoute)
        query1 = query.filter(EcmpRoute.router_id == router_id)
        return query1.count()

    def _get_all_next_hop_ips_of_router(self, context, router_id):
        all_next_hops = []
        query = context.session.query(EcmpRoute)
        query1 = query.filter(EcmpRoute.router_id == router_id).all()
        for q in query1:
            all_next_hops.extend(q['next_hops'].split(','))
        return all_next_hops

    def _validate_vip_exist(self, context, ecmproute):
        # one router only can have one ecmp route for a vip.
        router_id = ecmproute['router_id']
        vip = ecmproute['vip']
        query = context.session.query(EcmpRoute)
        query1 = query.filter(EcmpRoute.router_id == router_id,
                              EcmpRoute.vip == vip).all()
        LOG.debug('ecmp: the reqult of query vip in router is %s', query1)
        if query1:
            LOG.debug('the router %s already has ecmproute to %s', router_id, vip)
            raise exception.EcmprouteConflict(router_id=router_id, vip=vip)

    def create_ecmp_route(self, context, ecmp_route):
        ecmproute = ecmp_route['ecmp_route']
        self._validate_vip_exist(context, ecmproute)
        next_hops = ecmproute['next_hops']
        next_hops_string = ','.join(next_hops)
        LOG.debug('ecmp: the next_hops is %s', next_hops_string)
        with context.session.begin(subtransactions=True):
            ecmproute_db = EcmpRoute(id=uuidutils.generate_uuid(),
                                     tenant_id=ecmproute['tenant_id'],
                                     vip=ecmproute['vip'],
                                     next_hops=next_hops_string,
                                     router_id=ecmproute['router_id'])
            context.session.add(ecmproute_db)
        return self._make_ecmp_route_dict(ecmproute_db)

    def update_ecmp_route(self, context, id, ecmp_route):
        ecmproute = ecmp_route['ecmp_route']
        next_hops = ecmproute['next_hops']
        next_hops_string = ','.join(next_hops)
        ecmproute['next_hops'] = next_hops_string
        with context.session.begin(subtransactions=True):
            ecmproute_db = self._get_ecmproute(context, id)
            ecmproute_db.update(ecmproute)
        return self._make_ecmp_route_dict(ecmproute_db)

    def get_ecmp_route(self, context, id, fields=None):
        ecmproute_db = self._get_ecmproute(context, id)
        return self._make_ecmp_route_dict(ecmproute_db, fields)

    def get_ecmp_routes(self, context, filters=None, fields=None):
        return self._get_collection(context,
                                    EcmpRoute,
                                    self._make_ecmp_route_dict,
                                    filters=filters,
                                    fields=fields)

    def delete_ecmp_route(self, context, id):
        with context.session.begin(subtransactions=True):
            context.session.query(EcmpRoute).filter_by(id=id).delete()

def ecmp_callback(resource, event, trigger, **kwargs):
    LOG.debug('ecmp callback is called for resource router_interface before_delete, kwargs: %s',
              kwargs)
    ecmp_plugin = directory.get_plugin('ECMP')
    ecmp_plugin.check_router_interface_not_in_use(**kwargs)


def subscribe():
    registry.subscribe(
        ecmp_callback, resources.ROUTER_INTERFACE, events.BEFORE_DELETE)
