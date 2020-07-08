from neutron_lib.api import converters
from neutron_lib.db import constants

ALIAS = 'ecmp'
# Whether or not this extension is simply signaling behavior to the user
# or it actively modifies the attribute map.
IS_SHIM_EXTENSION = False


# Whether the extension is marking the adoption of standardattr model for
# legacy resources, or introducing new standardattr attributes. False or
# None if the standardattr model is adopted since the introduction of
# resource extension.
# If this is True, the alias for the extension should be prefixed with
# 'standard-attr-'.
IS_STANDARD_ATTR_EXTENSION = False

# The name of the extension.
NAME = 'network ecmp'

# The description of the extension.
DESCRIPTION = "Provides support of ecmp for Inspur public cloud network."

# A timestamp of when the extension was introduced.
UPDATED_TIMESTAMP = "2020-03-01T10:00:00-00:00"
ECMPROUTES = 'ecmp_routes'
RESOURCE_ATTRIBUTE_MAP = {
    ECMPROUTES: {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'is_filter': True,
               'is_sort_key': True,
               'primary_key': True},
        'tenant_id': {'allow_post': True, 'allow_put': False,
                      'required_by_policy': True,
                      'validate': {
                          'type:string': constants.PROJECT_ID_FIELD_SIZE},
                      'is_filter': True, 'is_sort_key': True,
                      'is_visible': True},
        'vip': {'allow_post': True, 'allow_put': False,
                      'validate': {'type:ip_address_or_none': None},
                      'is_visible': True},
        'router_id': {'allow_post': True, 'allow_put': False,
                      'validate': {'type:uuid_or_none': None},
                      'is_filter': True, 'is_sort_key': True,
                      'is_visible': True},
        'next_hops': {'allow_post': True, 'allow_put': True,
                      'is_visible': True}
    }
}

# The subresource attribute map for the extension.  This extension has only
# top level resources, not child resources, so this is set to an empty dict.
SUB_RESOURCE_ATTRIBUTE_MAP = {
}

# The action map.
ACTION_MAP = {
}

# The action status.
ACTION_STATUS = {
}

# The list of required extensions.
REQUIRED_EXTENSIONS = [
]

# The list of optional extensions.
OPTIONAL_EXTENSIONS = [
]

