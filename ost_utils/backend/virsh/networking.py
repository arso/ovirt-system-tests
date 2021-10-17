#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#
import ipaddress
import xml.etree.ElementTree as ET

from ost_utils.shell import shell


class HostDhcps:
    def __init__(self, ip_node=ET.fromstring("<ip></ip>")):
        self._host_dhcps = {}
        self._parse(ip_node)

    def __repr__(self):
        return (
            f"< {self.__class__.__name__} | host_dhcps: {self._host_dhcps} >"
        )

    def _parse(self, ip_node):
        for host_dhcp in ip_node.findall("./dhcp/host"):
            entry = HostDhcp(host_dhcp)
            self._host_dhcps[entry.mac_or_id] = entry

    def get_dhcp_by_mac_or_id(self, mac_or_id):
        return self._host_dhcps.get(mac_or_id)

    def get_host_dhcp_by_mac_suffix(self, suffix):
        for mac_or_id in self._host_dhcps:
            if mac_or_id.endswith(suffix):
                return self._host_dhcps.get(mac_or_id)
        return None


class HostDhcp:
    def __init__(self, host_dhcp):
        self._hostname = host_dhcp.get("name")
        self._mac_or_id = host_dhcp.get("mac", host_dhcp.get("id"))
        self._ip = ipaddress.ip_address(host_dhcp.get("ip"))

    def __repr__(self):
        return (
            f"< {self.__class__.__name__} | "
            f"hostname: {self._hostname}, "
            f"mac_or_id: {self._mac_or_id}, "
            f"ip: {self._ip} >"
        )

    @property
    def ip(self):
        return self._ip

    @property
    def hostname(self):
        return self._hostname

    @property
    def mac_or_id(self):
        return self._mac_or_id


class VirshNetworks:
    def __init__(self, deployment_path):
        self._networks_by_ost_name = {}
        self._networks_by_libvirt_name = {}
        self._load(deployment_path)

    def __repr__(self):
        return (
            f"< {self.__class__.__name__} | "
            f"networks_by_ost_name: {self._networks_by_ost_name}, "
            f"networks_by_libvirt_name: {self._networks_by_libvirt_name} >"
        )

    def _load(self, deployment_path):
        libvirt_net_names = self._get_libvirt_names_for_ost_nets_on_machine()
        for name in libvirt_net_names:
            net = VirshNetwork(name)
            net.load_xml()
            if net.is_network_from_current_run(deployment_path):
                net.parse()
                self._push_item(net)

    def _push_item(self, net):
        self._networks_by_ost_name[net.ost_name] = net
        self._networks_by_libvirt_name[net.libvirt_name] = net

    def _get_libvirt_names_for_ost_nets_on_machine(self):
        libvirt_net_names = [
            name
            for name in shell("virsh net-list --name".split()).splitlines()
            if name.startswith("ost")
        ]
        return libvirt_net_names

    def get_network_for_ost_name(self, ost_net_name):
        return self._networks_by_ost_name[ost_net_name]

    def get_network_for_libvirt_name(self, libvirt_name):
        return self._networks_by_libvirt_name[libvirt_name]

    def find_host_dhcp_for_mac(self, mac):
        host_dhcp4 = self.find_host_dhcp4_for_mac(mac)
        host_dhcp6 = self.find_host_dhcp6_for_mac(mac)
        return host_dhcp4, host_dhcp6

    def find_host_dhcp4_for_mac(self, mac):
        for network in self._networks_by_ost_name.values():
            host_dhcp4 = network.get_dhcp4_entries_for_mac(mac)
            if host_dhcp4 is not None:
                return host_dhcp4
        return None

    def find_host_dhcp6_for_mac(self, mac):
        for network in self._networks_by_ost_name.values():
            host_dhcp6 = network.get_dhcp6_entries_for_mac(mac)
            if host_dhcp6 is not None:
                return host_dhcp6
        return None


class VirshNetwork:
    # pylint: disable=too-many-instance-attributes

    """
    Example of an ost network xml that this file processes:

    <network connections='3'>
      <name>ost15d9c3a0-200</name>
      <uuid>b15b4c4c-3c9d-4b39-9408-03282bea1a4b</uuid>
      <metadata>
        <ost:ost xmlns:ost="OST:metadata">
          <ost-network-type comment="storage"/>
          <ost-working-dir comment="/home/hbraha/testing/ovirt-system-tests/
          deployment"/>
        </ost:ost>
      </metadata>
      <forward mode='nat'>
        <nat ipv6='yes'>
          <port start='1024' end='65535'/>
        </nat>
      </forward>
      <bridge name='ost15d9c3a0-200' stp='on' delay='0'/>
      <mac address='52:54:00:d3:f3:40'/>
      <domain name='lago.local' localOnly='yes'/>
      <dns enable='no'/>
      <ip address='192.168.200.1' netmask='255.255.255.0'>
        <dhcp>
          <range start='192.168.200.100' end='192.168.200.254'/>
          <host mac='54:52:c0:a8:c8:02'
          name='ost-basic-suite-master-engine-storage' ip='192.168.200.2'/>
          <host mac='54:52:c0:a8:c8:03'
           name='ost-basic-suite-master-host-0-storage' ip='192.168.200.3'/>
          <host mac='54:52:c0:a8:c8:04'
          name='ost-basic-suite-master-host-1-storage' ip='192.168.200.4'/>
        </dhcp>
      </ip>
      <ip family='ipv6' address='fd8f:1391:3a82:200::1' prefix='64'>
        <dhcp>
          <range start='fd8f:1391:3a82:200::c0a8:c864'
          end='fd8f:1391:3a82:200::c0a8:c8fe'/>
          <host id='0:3:0:1:54:52:c0:a8:c8:02'
          name='ost-basic-suite-master-engine-storage'
          ip='fd8f:1391:3a82:200::c0a8:c802'/>
          <host id='0:3:0:1:54:52:c0:a8:c8:03'
          name='ost-basic-suite-master-host-0-storage'
          ip='fd8f:1391:3a82:200::c0a8:c803'/>
          <host id='0:3:0:1:54:52:c0:a8:c8:04'
          name='ost-basic-suite-master-host-1-storage'
          ip='fd8f:1391:3a82:200::c0a8:c804'/>
        </dhcp>
      </ip>
    </network>
    """

    def __init__(self, name):
        self._ip4_gw = None
        self._ip4_prefix = None
        self._host_dhcps4 = HostDhcps()
        self._ip6_gw = None
        self._ip6_prefix = None
        self._host_dhcps6 = HostDhcps()
        self._ost_name = None
        self._libvirt_name = name
        self._xml = None

    def __repr__(self):
        return (
            f"< {self.__class__.__name__} | "
            f"ip4_gw: {self._ip4_gw}, "
            f"ip4_prefix: {self._ip4_prefix}, "
            f"host_dhcps4: {self._host_dhcps4}, "
            f"ip6_gw: {self._ip6_gw}, "
            f"ip6_prefix: {self._ip6_prefix}, "
            f"host_dhcps6: {self._host_dhcps6}, "
            f"ost_name: {self._ost_name}, "
            f"libvirt_name: {self._libvirt_name}, "
            f"xml: {self._xml} >"
        )

    def parse(self):
        self._find_ost_name()
        for ip_node in self._xml.findall("./ip"):
            if ip_node.get("family", None) == "ipv6":
                self._ip6_gw = ipaddress.ip_address(ip_node.get("address"))
                self._ip6_prefix = int(ip_node.get("prefix"))
                self._host_dhcps6 = HostDhcps(ip_node)
            else:
                self._ip4_gw = ipaddress.ip_address(ip_node.get("address"))
                netmask = ip_node.get("netmask")
                self._ip4_prefix = ipaddress.IPv4Network(
                    f"0.0.0.0/{netmask}"
                ).prefixlen
                self._host_dhcps4 = HostDhcps(ip_node)

    def is_network_from_current_run(self, deployment_path):
        try:
            return deployment_path == self._find_working_dir()
        except AttributeError:
            return False

    def _find_ost_name(self):
        self._ost_name = self._xml.find(
            "./metadata/{OST:metadata}ost/ost-network-type[@comment]"
        ).get("comment")

    def _find_working_dir(self):
        return self._xml.find(
            "./metadata/{OST:metadata}ost/ost-working-dir[@comment]"
        ).get("comment")

    def load_xml(self):
        xml_str = shell(
            f"virsh net-dumpxml {self._libvirt_name}".split()
        ).strip()
        self._xml = ET.fromstring(xml_str)

    @property
    def ip4_prefix(self):
        return self._ip4_prefix

    @property
    def ip6_prefix(self):
        return self._ip6_prefix

    @property
    def ost_name(self):
        return self._ost_name

    @property
    def libvirt_name(self):
        return self._libvirt_name

    def get_dhcp4_entries_for_mac(self, mac):
        return self._host_dhcps4.get_dhcp_by_mac_or_id(mac)

    def get_dhcp6_entries_for_mac(self, mac):
        return self._host_dhcps6.get_host_dhcp_by_mac_suffix(mac)
