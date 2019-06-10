import socket, sys

from ethernet_header import EthernetHeader
from ip_header import IPHeader
from tcp_header import TCPHeader
from listener import Listener
from utils import sendeth, checksum, bcolors

from struct import *

class SYNACK:
    """
    SYN/ACK
    - An SYN message is sent to a port
    - If the port is open, an RST will be received; else the port is close
    """
    def __init__(self, src_mac, dst_mac, src_ip, dst_ip, interface, src_port, dst_port):
        self.src_mac = src_mac
        self.dst_mac = dst_mac
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.interface = interface
        self.src_port = src_port
        self.dst_port = dst_port

        # Construct the Ethernet header
        self.eth_header = EthernetHeader(
            dst_mac = dst_mac,
            src_mac = src_mac,
            type = 0x86dd
        )
        self.eth_packet = self.eth_header.assembly()

        # Construct the IPv6 header
        self.ip_header = IPHeader(
            version = 6,
            traffic_class = 0,
            flow_label = 1,
            payload_len = 20,
            next_header = socket.IPPROTO_TCP,
            hop_limit = 255,
            src_address = self.src_ip,
            dst_address = self.dst_ip
        )
        self.ip_packet = self.ip_header.assembly()

        # Construct the TCP header
        self.tcp_header = TCPHeader(
            src_port = self.src_port,
            dst_port = self.dst_port,
            seq_num = 0,
            ack_seq = 0,
            header_len = 5,
            fin = 0, syn = 1, rst = 0, psh = 0, ack = 1, urg = 0,
            window = 5840,
            checksum = 0,
            urg_ptr = 0
        )
        self.tcp_packet = self.tcp_header.assembly()

    def start(self):
        listen = Listener()
        response_flags = listen.request(packet=self.__packet(), 
                                        interface=self.interface,
                                        src_port=self.src_port,
                                        dst_port=self.dst_port)
        
        # if open, flags = rst
        if response_flags == 4: # 0b000100
            print('[INFO] Port [:{}] is '.format(self.dst_port) + \
                  bcolors.OKGREEN + 'OPEN' + bcolors.ENDC)

        # else close
        else:
            print('[INFO] Port [:{}] is '.format(self.dst_port) + \
                  bcolors.FAIL + 'CLOSE' + bcolors.ENDC)

    def __packet(self):
        # pseudo header fields
        placeholder = 0
        protocol = socket.IPPROTO_TCP
        tcp_length = len(self.tcp_packet)

        psh = self.ip_header.src_address_ipv6 + \
              self.ip_header.dst_address_ipv6 + \
              pack('!BBH', placeholder, protocol, tcp_length)
        psh = psh + self.tcp_packet
        # make the tcp header again and fill the correct checksum
        self.tcp_header.checksum = checksum(psh)
        self.tcp_packet = self.tcp_header.assembly()    
         
        # final full packet - syn packets dont have any data
        packet = self.eth_packet + self.ip_packet + self.tcp_packet
        return packet