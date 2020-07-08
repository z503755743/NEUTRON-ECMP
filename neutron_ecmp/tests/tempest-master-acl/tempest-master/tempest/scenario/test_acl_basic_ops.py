from oslo_log import log
import testtools

from tempest.common import compute
from tempest.common import utils
from tempest.common.utils import net_info
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.scenario import manager

CONF = config.CONF
LOG = log.getLogger(__name__)

class TestAclBasicOps(manager.NetworkScenarioTest):

    class TenantProperties(object):
        """helper class to save tenant details

            id
            credentials
            network
            subnet
            security groups
            servers
            access point
        """

        def __init__(self, clients):
            # Credentials from manager are filled with both names and IDs
            self.manager = clients
            self.creds = self.manager.credentials
            self.network = None
            self.subnet = None
            self.router = None
            self.security_groups = {}
            self.servers = list()
            self.access_point = None

        def set_network(self, network, subnet, router):
            self.network = network
            self.subnet = subnet
            self.router = router

    @classmethod
    def resource_setup(cls):
        cls.floating_ips = {}
        cls.tenants = {}