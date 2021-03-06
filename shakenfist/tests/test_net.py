import mock
import testtools


from shakenfist import net


class NetTestCase(testtools.TestCase):
    def setUp(self):
        super(NetTestCase, self).setUp()

        self.ipmanager_persist = mock.patch(
            'shakenfist.db.persist_ipmanager')
        self.mock_ipmanager_persist = self.ipmanager_persist.start()

    def test_init(self):
        net.Network(uuid='notauuid', vxlan_id=42, provide_dhcp=True,
                    provide_nat=True, physical_nic='eth0',
                    ipblock='192.168.1.0/24')

    def test_str(self):
        n = net.Network(uuid='notauuid', vxlan_id=42, provide_dhcp=True,
                        provide_nat=True, physical_nic='eth0',
                        ipblock='192.168.1.0/24')
        self.assertEqual('network(notauuid, vxid 42)', str(n))
