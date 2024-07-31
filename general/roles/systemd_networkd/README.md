systemd-networkd
=========

Configure the linux network using systemd-networkd.

## [systemd.link](https://www.freedesktop.org/software/systemd/man/systemd.link.html)
systemd.link allows for the configuration of network device properties,<br>like MAC address or MTU settings, and can be used to create persistent network device names.<br> This helps in managing and configuring network interfaces consistently across reboots.<br> If using networkd_link a reboot is needed to reload the interface configuration.

## [systemd.netdev](https://www.freedesktop.org/software/systemd/man/systemd.netdev.html)
systemd.netdev is used for configuring network devices at a lower level, <br>defining properties like the type of device (e.g., Ethernet, VLAN), MAC address, and MTU settings.

## [systemd.network](https://www.freedesktop.org/software/systemd/man/systemd.network.html)
systemd.network is used to define and configure network settings for specific network interfaces, like IP address, gateway, DNS servers, and more.


Known Issues
------------
- On the first rollout on a new system there is a chance that the role gets stuck on reloading the network kernel modules. Somehow the routes are not always updated, despite reloading the network stack. In that case reboot the OS.

Requirements
------------
- RedHat 8 or later<br>
- EPEL-Repo

IMPORTANT
---------
#### Names
link, netdev and network names must not:
- Begin with a number
- End with a dash/underscore and a number (eg. ifname-70.link, ifname_70.link)
- [Exceed 15 bytes](https://elixir.bootlin.com/linux/v5.6/source/include/uapi/linux/if.h#L33)

#### VLANs
When renaming the underlying interface of an VLAN connection,<br>
make sure to set `type: "!vlan"` in the networkd_link configuration.
```yaml
networkd_link:
  - link_name: eth1
    mac_address: 00:50:56:98:60:68
    type: "!vlan"
```

Additional Info
---------------
## firewalld
As systemd-networkd is not a supported network solution of firewalld, zones have to be assigned to interfaces via firewalld.
```yaml
firewalld_zones:
  - zone: ans_public  # Zones have to be listed twice (once for creation, once for setting the target)
  - zone: ans_public
    target: DROP

  - zone: ans_mgmt  # Zones have to be listed twice (once for creation, once for setting the target)
  - zone: ans_mgmt
    target: ACCEPT

firewalld_rules:
  - zone: ans_public
    interface: public-if

  - zone: ans_mgmt
    interface: mgmt-if
```

## systemd.link
If you rename interfaces via systemd.link files, the role will reload the networking kernel modules to apply the changes without rebooting the system.<br>
Even though this works well enough, it is generally recommended setting the MACAddress via the `mac_address` key whenever possible.<br>
Matching the MAC instead of a name is generally more robust as this address is unlikely to change.<br>

Excerpt from the template:
```
[Match]
{% if item.mac_address is defined %}
#Name={{ item.name }}
MACAddress={{ item.mac_address }}
{% elif item.name is defined %}
Name={{ item.name }}
{% endif %}
```

## systemd-resolved
systemd-resolved works with DNS routing domains and DNS search domains.<br>
A DNS routing domain determines which DNS server your DNS query goes to.<br>
When you query a name that is only a single label (a domain without any dots) a DNS search domain gets appended to your query.<br><br>
In systemd-resolved, each DNS routing domain may or may not be used as a search domain.<br>
By default, systemd-resolved will add search domains for every configured routing domain that is not prefixed by a tilde.<br>
For example, ~example.com is a routing domain only, while example.com is both a routing domain and a search domain.<br>
There is also a global routing domain,  "~."<br><br>
systemd-resolved first decides which network interface is most appropriate for your DNS query based on the domain name you are querying, then sends your query to the DNS server associated with that interface.

### Full description of DNS configuration:
- [Domains](https://www.freedesktop.org/software/systemd/man/systemd.network.html#Domains=)
- [DNSDefaultRoute](https://www.freedesktop.org/software/systemd/man/systemd.network.html#DNSDefaultRoute=)


Examples
----------------
#### Network configuration with interfaces named after their respective vlans
```yaml
networkd_link:
  - link_name: test_srv0057
    mac_address: "42:6C:67:58:EB:92"

  - link_name: jump_srv0113
    mac_address: "CC:6D:8F:64:3D:80"

networkd_network:
  - name: test_srv0057
    mac_address: "42:6C:67:58:EB:92"
    address:
      - 172.X.X.X/24
      - 172.X.X.X/24
    gateway: 172.X.X.X
    dns:
      - 8.8.8.8
      - 9.9.9.9
    domains:
      - localdom
    routes:
      - dest: 172.X.X.X/24
        gw: 10.X.X.X
      - dest: 172.X.X.X/17
        gw: 10.X.X.X

  - name: jump_srv0113
    address: 10.X.X.X/24
    mac_address: "CC:6D:8F:64:3D:80"
```

#### Create a dummy interface
```yaml
networkd_netdev:
  - name: dummy-if
    kind: dummy
    mac_address: "F5:2F:C6:6E:CE:A1"  # This is optional

networkd_network:
  - name: dummy-if
    address: 192.X.X.X/24
```

#### VLAN Configuration
```yaml
networkd_network:
  - name: ens192
    link_local_addressing: "no" # Disable ipv(4/6) link local addressing | Not required
    vlan: ens192.57

  - name: ens192.57
    address: 172.X.X.X/24
    gateway: 172.X.X.X
    link_local_addressing: "no" # Disable ipv(4/6) link local addressing | Not required
    dns:
      - 8.8.8.8
      - 9.9.9.9
    domains:
      - localdom

networkd_netdev:
  - name: ens192.57
    kind: vlan
    vlan_id: 57
    vlan_protocol: 802.1q
```

## Variables
- [networkd_link](#networkd_link)
- [networkd_network](#networkd_network)
- [networkd_netdev](#networkd_netdev)

Role Variables
--------------
| variable                             | type | default | required | description                                                                |
|--------------------------------------|------|---------|----------|----------------------------------------------------------------------------|
| `networkd_keep_existing_definitions` | bool | false   | no       | If set to true prevent removal of configurations not managed by this role. |

## networkd_link
| variable                                                     | type \| d(String) | default \| d(None) | required \| d(no) | description   |
|--------------------------------------------------------------|-------------------|--------------------|-------------------|---------------|
| `networkd_link`                                              | List(Dict)        | []                 | no                | List of Links |
| `[Match]`                                                    |                   |                    |                   |               |
| &emsp;&emsp; `mac_address`                                   | String            | None               | yes               | MAC address   |
| &emsp;&emsp; `type`                                          | String            | None               | no                | Type          |
| &emsp;&emsp; `kind`                                          | String            | None               | no                | Kind          |
| `[Link]`                                                     |                   |                    |                   |               |
| &emsp;&emsp; `link_name`                                     | String            | None               | no                |               |
| &emsp;&emsp; `link_description`                              | String            | None               | no                |               |
| &emsp;&emsp; `link_alias`                                    | String            | None               | no                |               |
| &emsp;&emsp; `link_mac_address_policy`                       | String            | None               | no                |               |
| &emsp;&emsp; `link_mac_address`                              | String            | None               | no                |               |
| &emsp;&emsp; `link_name_policy`                              | String            | None               | no                |               |
| &emsp;&emsp; `link_alternative_names_policy`                 | String            | None               | no                |               |
| &emsp;&emsp; `link_alternative_name`                         | String            | None               | no                |               |
| &emsp;&emsp; `link_transmit_queues`                          | String            | None               | no                |               |
| &emsp;&emsp; `link_receive_queues`                           | String            | None               | no                |               |
| &emsp;&emsp; `link_transmit_queue_length`                    | String            | None               | no                |               |
| &emsp;&emsp; `link_mtu_bytes`                                | String            | None               | no                |               |
| &emsp;&emsp; `link_bits_per_second`                          | String            | None               | no                |               |
| &emsp;&emsp; `link_duplex`                                   | String            | None               | no                |               |
| &emsp;&emsp; `link_auto_negotiation`                         | String            | None               | no                |               |
| &emsp;&emsp; `link_wake_on_lan`                              | String            | None               | no                |               |
| &emsp;&emsp; `link_wake_on_lan_password`                     | String            | None               | no                |               |
| &emsp;&emsp; `link_port`                                     | String            | None               | no                |               |
| &emsp;&emsp; `link_advertise`                                | String            | None               | no                |               |
| &emsp;&emsp; `link_receive_checksum_offload`                 | String            | None               | no                |               |
| &emsp;&emsp; `link_transmit_checksum_offload`                | String            | None               | no                |               |
| &emsp;&emsp; `link_tcp_segmentation_offload`                 | String            | None               | no                |               |
| &emsp;&emsp; `link_segmentation_offload`                     | String            | None               | no                |               |
| &emsp;&emsp; `link_generic_segmentation_offload`             | String            | None               | no                |               |
| &emsp;&emsp; `link_generic_receive_offload`                  | String            | None               | no                |               |
| &emsp;&emsp; `link_generic_receive_offload_hardware`         | String            | None               | no                |               |
| &emsp;&emsp; `link_large_receive_offload`                    | String            | None               | no                |               |
| &emsp;&emsp; `link_receive_vlanctag_hardware_acceleration`   | String            | None               | no                |               |
| &emsp;&emsp; `link_transmit_vlanctag_hardware_acceleration`  | String            | None               | no                |               |
| &emsp;&emsp; `link_receive_vlanctag_filter`                  | String            | None               | no                |               |
| &emsp;&emsp; `link_transmit_vlanstag_hardware_acceleration`  | String            | None               | no                |               |
| &emsp;&emsp; `link_n_tuple_filter`                           | String            | None               | no                |               |
| &emsp;&emsp; `link_rx_channels`                              | String            | None               | no                |               |
| &emsp;&emsp; `link_rx_buffer_size`                           | String            | None               | no                |               |
| &emsp;&emsp; `link_rx_flow_control`                          | String            | None               | no                |               |
| &emsp;&emsp; `link_tx_flow_control`                          | String            | None               | no                |               |
| &emsp;&emsp; `link_auto_negotiation_flow_control`            | String            | None               | no                |               |
| &emsp;&emsp; `link_generic_segment_offload_max_bytes`        | String            | None               | no                |               |
| &emsp;&emsp; `link_generic_segment_offload_max_segments`     | String            | None               | no                |               |
| &emsp;&emsp; `link_use_adaptive_rx_coalesce`                 | String            | None               | no                |               |
| &emsp;&emsp; `link_rx_coalesce_sec`                          | String            | None               | no                |               |
| &emsp;&emsp; `link_rx_max_coalesced_frames`                  | String            | None               | no                |               |
| &emsp;&emsp; `link_coalesce_packet_rate_low`                 | String            | None               | no                |               |
| &emsp;&emsp; `link_coalesce_packet_rate_sample_interval_sec` | String            | None               | no                |               |
| &emsp;&emsp; `link_statistics_block_coalesce_sec`            | String            | None               | no                |               |
| &emsp;&emsp; `link_mdi`                                      | String            | None               | no                |               |
| &emsp;&emsp; `link_iov_virtual_functions`                    | String            | None               | no                |               |
| &emsp;&emsp; `link_virtual_function`                         | String            | None               | no                |               |

## networkd_network
| variable                                                    | type \| d(String)     | default \| d(None) | required \| d(no) | description                                                                                                                                                            |
|-------------------------------------------------------------|-----------------------|--------------------|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `networkd_network`                                          | List(Dict)            | []                 | no                | List of Networks                                                                                                                                                       |
| `[Match]`                                                   |                       |                    |                   |                                                                                                                                                                        |
| &emsp;&emsp; `name`                                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `mac_address`                                  | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `permanent_mac_address`                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `path`                                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `driver`                                       | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `type`                                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `kind`                                         | String                | None               | no                |                                                                                                                                                                        |
| `[Network]`                                                 |                       |                    |                   |                                                                                                                                                                        |
| &emsp;&emsp; `address`                                      | List(String) / String | None               | no                | IP Address with CIDR                                                                                                                                                   |
| &emsp;&emsp; `gateway`                                      | String                | None               | no                | IPv4 gateway address                                                                                                                                                   |
| &emsp;&emsp; `gateway6`                                     | String                | None               | no                | IPv6 gateway address                                                                                                                                                   |
| &emsp;&emsp; `dns`                                          | List(String)          | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `domains`                                      | List(String)          | None               | no                | A whitespace-separated list of domains which should be resolved using the DNS servers on this link. Prefix with "~" to switch from search domain to route only domain. |
| &emsp;&emsp; `dns_default_route`                            | String                | None               | no                | If false, this link's configured DNS servers are exclusively used for resolving names that match at least one of the domains configured on this link.                  |
| &emsp;&emsp; `description`                                  | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp`                                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server`                                  | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `link_local_addressing`                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `default_route_on_device`                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `llmnr`                                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `multicast_dns`                                | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dns_over_tls`                                 | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dnssec`                                       | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dnssec_negative_trust_anchors`                | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `lldp`                                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `emit_lldp`                                    | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `bind_carrier`                                 | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ntp`                                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ip_forward`                                   | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ip_masquerade`                                | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv4_ll_start_address`                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv4_ll_route`                                | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv4_accept_local`                            | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv4_route_localnet`                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv6_privacy_extensions`                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv6_accept_ra`                               | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv6_duplicate_address_detection`             | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv6_hop_limit`                               | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv6_link_local_address_generation_mode`      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv6_stable_secret_address`                   | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv4_proxy_arp`                               | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv6_proxy_ndp`                               | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv6_proxy_ndp_address`                       | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv6_send_ra`                                 | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipv6_mtu_bytes`                               | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_prefix_delegation`                       | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `keep_master`                                  | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `batman_advanced`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `bond`                                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `bridge`                                       | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `vrf`                                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ip_o_ib`                                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipvlan`                                       | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ipvtap`                                       | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `macsec`                                       | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `macvlan`                                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `macvtap`                                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `tunnel`                                       | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `vlan`                                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `vxlan`                                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `xfrm`                                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `active_slave`                                 | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `primary_slave`                                | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `configure_without_carrier`                    | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `ignore_carrier_loss`                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `keep_configuration`                           | String                | None               | no                |                                                                                                                                                                        |
| `[Route]`                                                   | List(Dict)            | None               | no                | Set additional routes for interface                                                                                                                                    |
| &emsp;&emsp; `routes.n.dest`                                | String                | None               | no                | Network to route with CIDR                                                                                                                                             |
| &emsp;&emsp; `routes.n.gw`                                  | String                | None               | no                | Next Hop                                                                                                                                                               |
| &emsp;&emsp; `routes.n.gateway_on_link`                     | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.source`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.metric`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.ip_v6_preference`                    | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.scope`                               | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.preferred_source`                    | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.table`                               | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.protocol`                            | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.type`                                | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.initial_congestion_window`           | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.initial_advertised_receive_window`   | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.quick_ack`                           | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.fast_open_no_cookie`                 | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.ttl_propagate`                       | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.mtu_bytes`                           | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.tcp_advertised_maximum_segment_size` | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.tcp_congestion_control_algorithm`    | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.multi_path_route`                    | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `routes.n.next_hop`                            | String                | None               | no                |                                                                                                                                                                        |
| `[DHCPv4]`                                                  |                       |                    |                   |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.send_hostname`                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.hostname`                             | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.client_identifier`                    | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.vendor_class_identifier`              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.user_class`                           | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.duid_type`                            | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.duid_raw_data`                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.iaid`                                 | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.anonymize`                            | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.request_options`                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.send_option`                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.send_vendor_option`                   | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.ip_service_type`                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.socket_priority`                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.label`                                | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.use_dns`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.routes_to_dns`                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.use_ntp`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.routes_to_ntp`                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.use_sip`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.use_captive_portal`                   | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.use_mtu`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.use_hostname`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.use_domains`                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.use_routes`                           | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.route_metric`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.route_table`                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.route_mtu_bytes`                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.quick_ack`                            | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.use_gateway`                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.use_timezone`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.use6_rd`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.fallback_lease_lifetime_sec`          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.request_broadcast`                    | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.max_attempts`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.listen_port`                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.deny_list`                            | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.allow_list`                           | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.send_release`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.send_decline`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v4.net_label`                            | String                | None               | no                |                                                                                                                                                                        |
| `[DHCPv6]`                                                  |                       |                    |                   |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.mudurl`                               | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.iaid`                                 | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.duid_type`                            | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.duid_raw_data`                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.request_options`                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.send_option`                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.send_vendor_option`                   | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.user_class`                           | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.vendor_class`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.prefix_delegation_hint`               | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.rapid_commit`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.use_address`                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.use_captive_portal`                   | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.use_delegated_prefix`                 | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.use_dns`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.use_ntp`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.use_hostname`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.use_domains`                          | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.net_label`                            | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.send_release`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_v6.without_ra`                           | String                | None               | no                |                                                                                                                                                                        |
| `[DHCPServer]`                                              |                       |                    |                   |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.server_address`                   | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.pool_offset`                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.pool_size`                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.default_lease_time_sec`           | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.max_lease_time_sec`               | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.uplink_interface`                 | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.emit_dns`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.dns`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.emit_ntp`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.ntp`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.emit_sip`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.sip`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.emit_pop3`                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.pop3`                             | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.emit_smtp`                        | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.smtp`                             | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.emit_lpr`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.lpr`                              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.emit_router`                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.router`                           | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.emit_timezone`                    | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.timezone`                         | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.boot_server_address`              | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.boot_server_name`                 | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.boot_filename`                    | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.send_option`                      | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.send_vendor_option`               | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.bind_to_interface`                | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.relay_target`                     | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.relay_agent_circuit_id`           | String                | None               | no                |                                                                                                                                                                        |
| &emsp;&emsp; `dhcp_server.relay_agent_remote_id`            | String                | None               | no                |                                                                                                                                                                        |

## networkd_netdev
| variable                                                       | type \| d(String) | default \| d(None) | required \| d(no) | description                                                                                      |
|----------------------------------------------------------------|-------------------|--------------------|-------------------|--------------------------------------------------------------------------------------------------|
| `networkd_netdev`                                              | List(Dict)        | []                 | no                | List of Netdevices                                                                               |
| `[NetDev]`                                                     |                   |                    |                   |                                                                                                  |
| &emsp;&emsp; `description`                                     | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `name`                                            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `kind`                                            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `mtu`                                             | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `mac_address`                                     | String            | None               | no                |                                                                                                  |
| `[Bridge]`                                                     |                   |                    |                   | If Kind=bridge                                                                                   |
| &emsp;&emsp; `br_hello_time_sec`                               | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_max_age_sec`                                  | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_forward_delay_sec`                            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_ageing_time_sec`                              | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_priority`                                     | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_group_forward_mask`                           | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_default_pvid`                                 | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_multicast_querier`                            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_multicast_snooping`                           | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_vlan_filtering`                               | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_vlan_protocol`                                | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_stp`                                          | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `br_multicast_igmp_version`                       | String            | None               | no                |                                                                                                  |
| `[Bond]`                                                       |                   |                    |                   | If Kind=bond                                                                                     |
| &emsp;&emsp; `bond_mode`                                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_transmit_hash_policy`                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_lacp_transmit_rate`                         | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_mii_monitor_sec`                            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_up_delay_sec`                               | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_down_delay_sec`                             | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_learn_packet_interval_sec`                  | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_ad_select`                                  | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_ad_actor_system_priority`                   | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_ad_user_port_key`                           | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_ad_actor_system`                            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_fail_over_mac_policy`                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_arp_validate`                               | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_arp_interval_sec`                           | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_arp_ip_targets`                             | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_arp_all_targets`                            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_primary_reselect_policy`                    | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_resend_igmp`                                | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_packets_per_slave`                          | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_gratuitous_arp`                             | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_all_slaves_active`                          | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_dynamic_transmit_load_balancing`            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `bond_min_links`                                  | String            | None               | no                |                                                                                                  |
| `[VLAN]`                                                       |                   |                    |                   | If Kind=vlan                                                                                     |
| &emsp;&emsp; `vlan_id`                                         | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vlan_protocol`                                   | String            | 802.1q             | no                |                                                                                                  |
| &emsp;&emsp; `vlan_gvrp`                                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vlan_mvrp`                                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vlan_loose_binding`                              | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vlan_reorder_header`                             | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vlan_egress_qos_maps`                            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vlan_ingress_qos_maps`                           | String            | None               | no                |                                                                                                  |
| `[MACVLAN]`                                                    |                   |                    |                   | If Kind=macvlan                                                                                  |
| &emsp;&emsp; `macvlan_mode`                                    | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `macvlan_source_mac_address`                      | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `macvlan_broadcast_multicast_queue_length`        | String            | None               | no                |                                                                                                  |
| `[VXLAN]`                                                      |                   |                    |                   | If Kind=vxlan                                                                                    |
| &emsp;&emsp; `vxlan_vni`                                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_remote`                                    | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_local`                                     | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_group`                                     | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_tos`                                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_ttl`                                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_mac_learning`                              | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_fdb_ageing_sec`                            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_maximum_fdb_entries`                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_reduce_arp_proxy`                          | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_l2_miss_notification`                      | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_l3_miss_notification`                      | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_route_short_circuit`                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_udp_checksum`                              | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_udp6_zero_checksum_tx`                     | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_udp6_zero_checksum_rx`                     | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_remote_checksum_tx`                        | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_remote_checksum_rx`                        | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_group_policy_extension`                    | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_generic_protocol_extension`                | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_destination_port`                          | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_port_range`                                | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_flow_label`                                | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_ip_do_not_fragment`                        | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `vxlan_independent`                               | String            | None               | no                |                                                                                                  |
| `[L2TP]`                                                       |                   |                    |                   | If Kind=l2tp                                                                                     |
| &emsp;&emsp; `l2tp_tunnel_id`                                  | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tp_peer_tunnel_id`                             | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tp_remote`                                     | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tp_local`                                      | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tp_encapsulation_type`                         | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tp_udp_source_port`                            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tp_udp_destination_port`                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tp_udp_checksum`                               | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tp_udp6_zero_checksum_tx`                      | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tp_udp6_zero_checksum_rx`                      | String            | None               | no                |                                                                                                  |
| `[L2TPSession]`                                                |                   |                    |                   | If Kind=l2tp                                                                                     |
| &emsp;&emsp; `l2tpsession_name`                                | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tpsession_session_id`                          | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tpsession_peer_session_id`                     | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `l2tpsession_layer2_specific_header`              | String            | None               | no                |                                                                                                  |
| `[Tunnel]`                                                     |                   |                    |                   | If kind 'ipip', 'sit', 'gre', 'gretap', 'ip6gre', 'ip6gretap', 'vti', 'vti6', 'ip6tnl', 'erspan' |
| &emsp;&emsp; `tunnel_external`                                 | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_local`                                    | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_remote`                                   | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_tos`                                      | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_ttl`                                      | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_discover_path_mtu`                        | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_ignore_dont_fragment`                     | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_ipv6_flow_label`                          | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_copy_dscp`                                | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_encapsulation_limit`                      | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_key`                                      | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_input_key`                                | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_output_key`                               | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_mode`                                     | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_independent`                              | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_assign_to_loopback`                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_allow_local_remote`                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_foo_over_udp`                             | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_fou_destination_port`                     | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_fou_source_port`                          | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_encapsulation`                            | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_ipv6_rapid_deployment_prefix`             | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_isatap`                                   | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_serialize_tunneled_packets`               | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_erspan_version`                           | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_erspan_index`                             | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_erspan_direction`                         | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tunnel_erspan_hardware_id`                       | String            | None               | no                |                                                                                                  |
| `[Tun]`                                                        |                   |                    |                   | If Kind=tun                                                                                      |
| &emsp;&emsp; `tun_multi_queue`                                 | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tun_packet_info`                                 | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tun_vnet_header`                                 | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tun_user`                                        | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tun_group`                                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tun_keep_carrier`                                | String            | None               | no                |                                                                                                  |
| `[Tap]`                                                        |                   |                    |                   | If Kind=tap                                                                                      |
| &emsp;&emsp; `tap_multi_queue`                                 | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tap_packet_info`                                 | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tap_vnet_header`                                 | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tap_user`                                        | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tap_group`                                       | String            | None               | no                |                                                                                                  |
| &emsp;&emsp; `tap_keep_carrier`                                | String            | None               | no                |                                                                                                  |

License
-------

GPL-2.0-or-later

Author Information
------------------

Betuxy <betuxy@disroot>
