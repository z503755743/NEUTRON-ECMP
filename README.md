# NEUTRON-ECMP



Currently, the directory `neutron-ecmp` contains an additional feature of neutron l3 in the form of an extra plug-in. 

This code implements the ability to add ECMP routes to the qrouter. 

This code can should run in a openstack environment of queens version, However, since it is separate from other projects, it is not yet guaranteed to work.

For now, it is just  a conceptual implementation for explain what am I want to do in:

https://review.opendev.org/#/c/729532/



## Updated in 7/15/2020:

upload file router_info.py

this file was in neutron/agent/l3/

I have modified it from line #184 to line #254

It implement the ECMP function just by change the logic in `routes_updated` method

