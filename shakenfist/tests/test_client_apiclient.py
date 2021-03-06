import datetime
import json
import mock
import testtools


from shakenfist.client import apiclient


class ApiClientTestCase(testtools.TestCase):
    def setUp(self):
        super(ApiClientTestCase, self).setUp()

        self.request_url = mock.patch(
            'shakenfist.client.apiclient._request_url')
        self.mock_request = self.request_url.start()

    def test_get_instances(self):
        client = apiclient.Client()
        list(client.get_instances())

        self.mock_request.assert_called_with(
            'GET', 'http://localhost:13000/instances')

    def test_get_instance(self):
        client = apiclient.Client()
        client.get_instance('notreallyauuid')

        self.mock_request.assert_called_with(
            'GET', 'http://localhost:13000/instances/notreallyauuid')

    def test_get_instance_interfaces(self):
        client = apiclient.Client()
        client.get_instance_interfaces('notreallyauuid')

        self.mock_request.assert_called_with(
            'GET', 'http://localhost:13000/instances/notreallyauuid/interfaces')

    def test_create_instance(self):
        client = apiclient.Client()
        client.create_instance('foo', 1, 2, ['netuuid1'], ['8@cirros'],
                               'sshkey', None)

        self.mock_request.assert_called_with(
            'POST', 'http://localhost:13000/instances',
            data={
                'name': 'foo',
                'cpus': 1,
                'memory': 2,
                'network': ['netuuid1'],
                'disk': ['8@cirros'],
                'ssh_key': 'sshkey',
                'user_data': None
            })

    def test_create_instance_user_data(self):
        client = apiclient.Client()
        client.create_instance('foo', 1, 2, ['netuuid1'], ['8@cirros'],
                               'sshkey', 'userdatabeforebase64')

        self.mock_request.assert_called_with(
            'POST', 'http://localhost:13000/instances',
            data={
                'name': 'foo',
                'cpus': 1,
                'memory': 2,
                'network': ['netuuid1'],
                'disk': ['8@cirros'],
                'ssh_key': 'sshkey',
                'user_data': "userdatabeforebase64"
            })

    def test_snapshot_instance(self):
        client = apiclient.Client()
        client.snapshot_instance('notreallyauuid', all=True)

        self.mock_request.assert_called_with(
            'POST', 'http://localhost:13000/instances/notreallyauuid/snapshot',
            data={'all': True})

    def test_soft_reboot_instance(self):
        client = apiclient.Client()
        client.reboot_instance('notreallyauuid')

        self.mock_request.assert_called_with(
            'POST', 'http://localhost:13000/instances/notreallyauuid/rebootsoft')

    def test_hard_reboot_instance(self):
        client = apiclient.Client()
        client.reboot_instance('notreallyauuid', hard=True)

        self.mock_request.assert_called_with(
            'POST', 'http://localhost:13000/instances/notreallyauuid/reboothard')

    def test_power_off_instance(self):
        client = apiclient.Client()
        client.power_off_instance('notreallyauuid')

        self.mock_request.assert_called_with(
            'POST', 'http://localhost:13000/instances/notreallyauuid/poweroff')

    def test_power_on_instance(self):
        client = apiclient.Client()
        client.power_on_instance('notreallyauuid')

        self.mock_request.assert_called_with(
            'POST', 'http://localhost:13000/instances/notreallyauuid/poweron')

    def test_pause_instance(self):
        client = apiclient.Client()
        client.pause_instance('notreallyauuid')

        self.mock_request.assert_called_with(
            'POST', 'http://localhost:13000/instances/notreallyauuid/pause')

    def test_unpause_instance(self):
        client = apiclient.Client()
        client.unpause_instance('notreallyauuid')

        self.mock_request.assert_called_with(
            'POST', 'http://localhost:13000/instances/notreallyauuid/unpause')

    def test_delete_instance(self):
        client = apiclient.Client()
        client.delete_instance('notreallyauuid')

        self.mock_request.assert_called_with(
            'DELETE', 'http://localhost:13000/instances/notreallyauuid')

    def test_cache_image(self):
        client = apiclient.Client()
        client.cache_image('imageurl')

        self.mock_request.assert_called_with(
            'POST', 'http://localhost:13000/images',
            data={'url': 'imageurl'})

    def test_get_networks(self):
        client = apiclient.Client()
        client.get_networks()

        self.mock_request.assert_called_with(
            'GET', 'http://localhost:13000/networks')

    def test_get_network(self):
        client = apiclient.Client()
        client.get_network('notreallyauuid')

        self.mock_request.assert_called_with(
            'GET', 'http://localhost:13000/networks/notreallyauuid')

    def test_delete_network(self):
        client = apiclient.Client()
        client.delete_network('notreallyauuid')

        self.mock_request.assert_called_with(
            'DELETE', 'http://localhost:13000/networks/notreallyauuid')

    def test_allocate_network(self):
        client = apiclient.Client()
        client.allocate_network('192.168.1.0/24', True, True, 'gerkin')

        self.mock_request.assert_called_with(
            'POST', 'http://localhost:13000/networks',
            data={
                'netblock': '192.168.1.0/24',
                'provide_dhcp': True,
                'provide_nat': True,
                'name': 'gerkin'
            })


class GetNodesMock():
    def json(self):
        return json.loads("""[
{
    "name": "sf-1.c.mikal-269605.internal",
    "ip": "10.128.15.213",
    "lastseen": "Mon, 13 Apr 2020 03:00:22 -0000"
},
{
    "name": "sf-2.c.mikal-269605.internal",
    "ip": "10.128.15.210",
    "lastseen": "Mon, 13 Apr 2020 03:04:17 -0000"
}
]
""")


class ApiClientGetNodesTestCase(testtools.TestCase):
    @mock.patch('shakenfist.client.apiclient._request_url',
                return_value=GetNodesMock())
    def test_get_nodes(self, mock_request):
        client = apiclient.Client()
        out = list(client.get_nodes())

        mock_request.assert_called_with(
            'GET', 'http://localhost:13000/nodes')
        assert(type(out[0]['lastseen']) == datetime.datetime)
