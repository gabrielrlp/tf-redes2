import socket, time

from ethernet_header import EthernetHeader
from ip_header import IPHeader
from tcp_header import TCPHeader
from utils import sendeth, checksum, bcolors

from struct import *

class TCPFin:
    """
    TCP Fin
    - An FIN message is sent to a port
    - If the port is close, an RST will be received; else the port is open
    """
    def __init__(self, src_mac, dst_mac, src_ip, dst_ip, interface, src_port, dst_port):
        self.src_mac = src_mac
        self.dst_mac = dst_mac
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.interface = interface
        self.src_port = src_port
        self.dst_port = dst_port
        self.timeout = 5 # seconds

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
            fin = 1, syn = 0, rst = 0, psh = 0, ack = 0, urg = 0,
            window = 5840,
            checksum = 0,
            urg_ptr = 0
        )
        self.tcp_packet = self.tcp_header.assembly()

    def start(self):
        listen = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
        listen.setblocking(0)
        # send syn
        sendeth(self.__packet(), self.interface)

        flags = 0
        timeout_start = time.time()
        while time.time() < timeout_start + self.timeout:
            # Receive packet
            try:
                raw_packet = listen.recvfrom(128)
                packet = raw_packet[0]
                
                # Get ethernet header
                eth_header = packet[0:14]

                # Get protocol type; 0x86dd for IPv6
                protocol_type = unpack('!6B6BH', eth_header)[12]
            
                # Check for IPv6 only
                if (protocol_type == int(0x86dd)):
                    # Get TCP header
                    tcp_header = unpack('!HHLLBBHHH', packet[54:74])
                    # Get the TCP destionation and source ports
                    tcp_src_port = tcp_header[0]
                    tcp_dst_port = tcp_header[1]

                    if tcp_dst_port == self.src_port and tcp_src_port == self.dst_port:
                        # Return the received flags
                        flags = int(tcp_header[5])
                        break
            except:
                pass
        
        # if closed, flags = rst & ack
        if flags == 20: # 0b010100 
            print('[INFO] Port [:{}] is '.format(self.dst_port) + \
                  bcolors.FAIL + 'CLOSE' + bcolors.ENDC)
        else:
            # the port is open
            print('[INFO] Port [:{}] is '.format(self.dst_port) + \
                  bcolors.OKGREEN + 'OPEN' + bcolors.ENDC)

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