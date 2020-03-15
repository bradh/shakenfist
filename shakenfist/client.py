# Copyright 2020 Michael Still

import click
import datetime
import logging
import os
from prettytable import PrettyTable
import sys
import time
import uuid

from shakenfist import config
from shakenfist.db import impl as db
from shakenfist import images
from shakenfist.net import impl as net
from shakenfist import util
from shakenfist import virt


logging.basicConfig(level=logging.DEBUG)

LOG = logging.getLogger(__file__)
LOG.setLevel(logging.DEBUG)


status = {}


def _status_callback(d):
    global status

    event = d.get('event')
    op = d.get('operation')

    if event == 'start':
        status[op] = time.time()
    elif event == 'finish':
        print('... %s took %0.2f seconds' % (op, time.time() - status[op]))
    elif event == 'heartbeat':
        print('    %s heartbeat "%s"' % (op, d.get('status')))


@click.group()
@click.option('--pretty/--no-pretty', default=True)
@click.pass_context
def cli(ctx, pretty):
    if not ctx.obj:
        ctx.obj = {}
    ctx.obj['PRETTY'] = pretty


@click.group(help='Network commands')
def network():
    pass


def _get_networks(ctx, args, incomplete):
    for n in db.get_networks():
        yield n['uuid']


@network.command(name='list', help='List networks')
@click.pass_context
def network_list(ctx):
    nets = db.get_networks()

    if ctx.obj['PRETTY']:
        x = PrettyTable()
        x.field_names = ['uuid', 'owner', 'netblock']
        for n in nets:
            x.add_row([n['uuid'], n['owner'], n['netblock']])
        print(x)

    else:
        print('uuid,owner,netblock')
        for n in nets:
            print('%s,%s,%s' % (n['uuid'], n['owner'], n['netblock']))


def _show_network(n):
    if not n:
        print('Network not found')
        sys.exit(1)

    print('%-12s: %s' % ('uuid', n['uuid']))
    print('%-12s: %s' % ('vxlan id', n['vxid']))
    print('%-12s: %s' % ('netblock', n['netblock']))
    print('%-12s: %s' % ('provide dhcp', n['provide_dhcp']))
    print('%-12s: %s' % ('provide nat', n['provide_nat']))
    print('%-12s: %s' % ('owner', n['owner']))


@network.command(name='show', help='Show a network')
@click.argument('uuid', type=click.STRING, autocompletion=_get_networks)
@click.pass_context
def network_show(ctx, uuid=None):
    _show_network(db.get_network(uuid))


@network.command(name='create',
                 help=('Create a network.\n\n'
                       'NETBLOCK:         The IP address block to use, as a CIDR\n'
                       '                  range -- for example 192.168.200.1/24\n'
                       '--dhcp/--no-dhcp: Should this network have DCHP?\n'
                       '--nat/--no-nat:   Should this network be able to access'
                       '                  the Internet via NAT?'))
@click.argument('netblock', type=click.STRING)
@click.option('--dhcp/--no-dhcp', default=True)
@click.option('--nat/--no-nat', default=True)
@click.pass_context
def network_create(ctx, netblock=None, dhcp=None, nat=None):
    _show_network(db.allocate_network(netblock, dhcp, nat))


@network.command(name='delete', help='Delete a network')
@click.argument('uuid', type=click.STRING, autocompletion=_get_networks)
@click.pass_context
def network_delete(ctx, uuid=None):
    n = net.from_db(uuid)
    if not n:
        print('Network not found')
        sys.exit(1)

    n.remove_dhcp()
    db.delete_network(uuid)


cli.add_command(network)


@click.group(help='Instance commands')
def instance():
    pass


def _get_instances(ctx, args, incomplete):
    for i in db.get_instances():
        yield i['uuid']


@instance.command(name='list', help='List instances')
@click.pass_context
def instance_list(ctx):
    insts = db.get_instances()

    if ctx.obj['PRETTY']:
        x = PrettyTable()
        x.field_names = ['uuid', 'name', 'cpus', 'memory']
        for i in insts:
            x.add_row([i['uuid'], i['name'], i['cpus'], i['memory']])
        print(x)

    else:
        print('uuid,name,cpus,memory')
        for i in insts:
            print('%s,%s,%s,%s' %
                  (i['uuid'], i['name'], i['cpus'], i['memory']))


def _show_instance(i):
    if not i:
        print('Instance not found')
        sys.exit(1)

    print('%-12s: %s' % ('uuid', i['uuid']))
    print('%-12s: %s' % ('net uuid', i['network_uuid']))
    print('%-12s: %s' % ('name', i['name']))
    print('%-12s: %s' % ('cpus', i['cpus']))
    print('%-12s: %s' % ('memory', i['memory']))
    print('%-12s: %s' % ('disk spec', i['disk_spec']))
    print('%-12s: %s' % ('ssh key', i['ssh_key']))

    print()
    print('Interfaces:')
    for interface in db.get_instance_interfaces(i['uuid']):
        print()
        print('    %-8s: %s' % ('uuid', interface['uuid']))
        print('    %-8s: %s' % ('macaddr', interface['macaddr']))
        print('    %-8s: %s' % ('ipv4', interface['ipv4']))


@instance.command(name='show', help='Show an instance')
@click.argument('uuid', type=click.STRING, autocompletion=_get_instances)
@click.pass_context
def instance_show(ctx, uuid=None):
    _show_instance(db.get_instance(uuid))


@instance.command(name='create',
                  help=('Create an instance.\n\n'
                        'NETWORK: The uuid of the network to attach the instance to.\n'
                        'NAME: The name of the instance.\n'
                        'CPUS: The number of vCPUs for the instance.\n'
                        'MEMORY: The amount RAM for the instance in GB.\n'
                        'DISK: The disks attached to the instance, in this format: \n'
                        '          size@image_url where size is in GB and @image_url\n'
                        '          is optional.\n'))
@click.argument('network', type=click.STRING, autocompletion=_get_networks)
@click.argument('name', type=click.STRING)
@click.argument('cpus', type=click.INT)
@click.argument('memory', type=click.INT)
@click.argument('disk', type=click.STRING, nargs=-1)
@click.pass_context
def instance_create(ctx, network=None, name=None, cpus=None, memory=None, disk=None):
    n = net.from_db(network)
    if not n:
        print('Network not found')
        sys.exit(1)
    n.create()

    newid = str(uuid.uuid4())
    instance = virt.from_definition(
        uuid=newid,
        name=name,
        disks=' '.join(disk),
        memory_mb=memory * 1024,
        vcpus=cpus,
        ssh_key='ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC2Pas6zLLgzXsUSZzt8E8fX7tzpwmNlrsbAeH9YoI2snfo+cKfO1BZVQgJnJVz+hGhnC1mzsMZMtdW2NRonRgeeQIPTUFXJI+3dyGzmiNrmtH8QQz++7zsmdwngeXKDrYhD6JGnPTkKcjShYcbvB/L3IDDJvepLxVOGRJBVHXJzqHgA62AtVsoiECKxFSn8MOuRfPHj5KInLxOEX9i/TfYKawSiId5xEkWWtcrp4QhjuoLv4UHL2aKs85ppVZFTmDHHcx3Au7pZ7/T9NOcUrvnwmQDVIBeU0LEELzuQZWLkFYvStAeCF7mYra+EJVXjiCQ9ZBw0vXGqJR1SU+W6dh9 mikal@kolla-m1'
    )

    with util.RecordedOperation('allocate ip address', instance) as _:
        n.allocate_ip_to_instance(instance)
        (mac, ip) = instance.get_network_details()
        db.create_network_interface(str(uuid.uuid4()), n.uuid, newid,
                                    mac, ip)
        n.update_dhcp()

    with util.RecordedOperation('instance creation', instance) as _:
        instance.create(_status_callback)


@instance.command(name='delete', help='Delete an instance')
@click.argument('uuid', type=click.STRING, autocompletion=_get_networks)
@click.pass_context
def instance_delete(ctx, uuid=None):
    i = virt.from_db(uuid)
    n = net.from_db(i.get_network_uuid())
    i.delete(_status_callback)
    if n:
        with util.RecordedOperation('deallocate ip address', instance) as _:
            n.update_dhcp()


@instance.command(name='snapshot', help='Snapshot instance')
@click.argument('uuid', type=click.STRING, autocompletion=_get_instances)
@click.argument('all', type=click.BOOL, default=False)
@click.pass_context
def instance_snapshot(ctx, uuid=None, all=False):
    i = virt.from_db(uuid)
    print('Created snapshot %s' % i.snapshot(all=all))


cli.add_command(instance)


@click.group(help='Image commands')
def image():
    pass


@image.command(name='cache',
               help=('Cache an image.\n\n'
                     'IMAGE_URL: The URL of the image to cache'))
@click.argument('image_url', type=click.STRING)
@click.pass_context
def image_cache(ctx, image_url=None):
    with util.RecordedOperation('cache image', image_url, _status_callback) as ro:
        images.fetch_image(image_url, recorded=ro)


cli.add_command(image)
