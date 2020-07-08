from neutron_lib._i18n import _
from neutron_lib import exceptions

class EcmprouteNotFound(exceptions.NotFound):
    message = _("Ecmproute %(id)s could not be found.")

class EcmprouteConflict(exceptions.Conflict):
    message = _("This router %(router_id)s already have ecmp route for vip %(vip)s.")

class EcmpInvalidRoutes(exceptions.InvalidInput):
    message = _("Invalid format for routes: the nexthop ip %(next_hop)s is not connected with router %(router_id)s")

class RouterInterfaceInUseBySlbEcmp(exceptions.InUse):
    message = _("Router interface for subnet %(subnet_id)s on router "
                "%(router_id)s cannot be deleted, as it is required "
                "by one or more slb_ecmp.")