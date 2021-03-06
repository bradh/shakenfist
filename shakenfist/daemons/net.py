import copy
import logging
import re
import setproctitle
import time

from oslo_concurrency import processutils

from shakenfist import config
from shakenfist import db
from shakenfist import net
from shakenfist import util


logging.basicConfig(level=logging.DEBUG)

LOG = logging.getLogger(__file__)
LOG.setLevel(logging.DEBUG)


VXLAN_RE = re.compile('[0-9]+: vxlan-([0-9]+).*')


def _get_deployed_vxlans():
    stdout, _ = processutils.execute('ip link', shell=True)
    for line in stdout.split('\n'):
        m = VXLAN_RE.match(line)
        if m:
            yield int(m.group(1))


class monitor(object):
    def __init__(self):
        setproctitle.setproctitle('sf net')

    def run(self):
        while True:
            time.sleep(30)

            # We do not reap unused networks from the network node, as they might be
            # in use for instances on other hypervisor nodes.
            if config.parsed.get('NODE_IP') != config.parsed.get('NETWORK_NODE_IP'):
                host_networks = []
                for inst in list(db.get_instances(local_only=True)):
                    for iface in db.get_instance_interfaces(inst['uuid']):
                        if not iface['network_uuid'] in host_networks:
                            host_networks.append(iface['network_uuid'])

                for network in host_networks:
                    n = net.from_db(network)
                    n.ensure_mesh()

                # TODO(mikal): remove stray networks
