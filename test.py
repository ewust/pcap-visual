#!/usr/bin/python

import sys
import pygame
import math
import struct
import dpkt
import socket
pygame.init()

def flags_to_str(flags):
    flag_str = ["FIN", "SYN", "RST", "PSH", "ACK", "URG", "ECE", "CWR"]
    out = ""
    for i in range(len(flag_str)):
        if (flags & (2**i)):
            out += flag_str[i] + ","
    return out[:-1]


class PcapPacket(dpkt.ethernet.Ethernet):
    def __init__(self, ts, caplen, actual_len, data):
        self.ts = ts
        self.caplen = caplen
        self.actual_len = actual_len
        super(PcapPacket, self).__init__(data)

class PcapReader(object):
    def __init__(self, f=sys.stdin):
        self.f = f
        # read header
        (self.magic, self.version_major, self.version_minor, self.tz, \
            self.sigfigs, self.snaplen, self.linktype) = \
            struct.unpack('<LHHLLLL', self.f.read(struct.calcsize('<LHHLLLL')))

    def next_packet(self):
        dat = self.f.read(struct.calcsize('<LLLL'))
        if len(dat) == 0:
            print 'outta data!'
            return None
        (ts_sec, ts_usec, caplen, actual_len) = struct.unpack('<LLLL', dat)
        pkt = self.f.read(caplen)
        return PcapPacket(ts_sec*1000000+ts_usec, caplen, actual_len, pkt)
        #yield ({'ts':(ts_sec*1000000 + ts_usec), 'ts_sec':ts_sec, 'ts_usec':ts_usec, 'caplen':caplen, 'actual_len':actual_len}, pkt)

    def packets(self):
        while True:
            pkt = self.next_packet()
            if pkt == None:
                break
            yield pkt


class Arrow(object):
    color = [255, 255, 255]
    def __init__(self, direction, start_time, end_time, above_text=None, start_text=None, end_text=None, below_text=None):
        self.direction = direction
        self.start = start_time
        self.end = end_time
        self.start_text = start_text
        self.end_text = end_text
        self.above_text = above_text
        self.below_text = below_text

    def draw_line(self, display, px_per_time, time_offset):
        start = [100 if self.direction else display.w - 100, (self.start - time_offset) * px_per_time + 100]
        end = [display.w - 100 if self.direction else 100, (self.end - time_offset) * px_per_time + 100]
        pygame.draw.aaline(display.window, Arrow.color, start, end, True)

        return (start, end)

    def draw_endcap(self, display, start, end):
        rise, run = get_norm_slope(start, end)

        x = end[0]
        y = end[1]
        rise *= 10
        run *= 10
        endcap_pts = [[x+rise, y-run], [x-rise, y+run], [x+2*run, y+2*rise]]

        pygame.draw.aalines(display.window, Arrow.color, True, endcap_pts, True)


    def draw_text_along_line(self, display, text, line, above=True):
        start, end = line
        rise, run = get_norm_slope(start, end)

        font = pygame.font.Font(None, 24)
        text_img = font.render(text, 1, (255, 0, 0))
        if run == 0:
            text_img = pygame.transform.rotate(text_img, 90)
        elif self.direction:
            text_img = pygame.transform.rotate(text_img, -(180.0/math.pi)*math.atan2(rise,run))
        else:
            text_img = pygame.transform.rotate(text_img, (180.0/math.pi)*math.atan2(rise,-run))

        # start at midpoint
        x = (start[0] + end[0])/ 2.0
        y = (start[1] + end[1])/ 2.0
        # center the text
        #shift_w = (display.w - 200.0 - font.size(text)[0]) / 2.0

        if not(self.direction):
            # subtract off the lip if we rotated text to the left (upper left corner is not upper left corner of text)
            y -= (text_img.get_height() - font.size(text)[1])

        # center the text
        x -= (font.size(text)[0]/2.0)
        y -= (font.size(text)[0]/2.0)*rise*run

        # shift above line if we are above text
        if above:
            shift_x = font.size(text)[1]*rise
            shift_y = font.size(text)[1]*run
            if not(self.direction):
                shift_y = -shift_y
                shift_x = -shift_x

            x += shift_x
            y -= shift_y

        display.window.blit(text_img, [x, y])

    def draw(self, display, px_per_time, start_time):
        # line and endcap
        start, end = self.draw_line(display, px_per_time, start_time)
        self.draw_endcap(display, start, end)

        # render above text
        self.draw_text_along_line(display, self.above_text, (start, end), True)

def get_norm_slope(start, end):
    rise = float(end[1]-start[1])
    run = float(end[0]-start[0])
    #print '%f - %f = rise: %f, run: %f' % (start[1], end[1], rise, run)
    if run != 0:
        rise_n = (rise/abs(run)) #if run < 0 else (rise/run)
        run_n = run/abs(run) #-1 if (run < 0 and rise > 0) else 1
    else:
        # TODO:
        rise_n = -1 if rise < 0 else 1
        run_n = 0
    return (rise_n, run_n)


class Display(object):
    def __init__(self, w=1024, h=740, max_time=1.000):
        self.w = w
        self.h = h
        self.max_time = max_time
        self.offset_time = 0
        self.window = pygame.display.set_mode((self.w, self.h))
        self.arrows = []

    def add_arrow(self, arrow):
        self.arrows.append(arrow)


    def px_to_time(self, px):
        return float((px) * self.max_time) / (self.h)

    def adjust_max_time(self, zoom_in=True, center_on=None):
        if center_on == None:
            center_on = (self.h - 100) / 2


        px_per_time = (self.h - 100.0) / self.max_time
        center_time = (center_on - 100.0) / px_per_time + self.offset_time
        print 'px_per_time: %f, max_time: %f sec' % (px_per_time, self.max_time)
        if zoom_in:
            self.max_time /= 1.1
        else:
           self.max_time *= 1.1



        # need to recenter; center_on px should map to the same time (center_time)
        # (center_on - 100) / new_px_per_time == (center_on - 100) / px_per_time + offset_time
        px_per_time = (self.h - 100.0) / self.max_time
        #offset_px = (center_time * px_per_time) #- center_on
        self.offset_time = center_time - ((center_on - 100.0) / px_per_time) #- center_time #offset_px / px_per_time
        print "center px: %d, center time: %f, max_time: %f, (%d - %d) => %f sec" % \
                (center_on, center_time, self.max_time, center_time*px_per_time, center_on, self.offset_time)

    def render(self):
        # our playing field is going to be W-200, H-100
        # so time*(H-100)/max_time gives px height for each arrow
        self.window.fill([0, 0, 0])

        px_per_time = (self.h - 100) / self.max_time
        #px_offset = self.offset * px_per_time
        for arrow in self.arrows:

            arrow.draw(self, px_per_time, self.offset_time)

        pygame.display.flip()



#d = Display(max_time=10.0)
#a = Arrow(1, 0.000, 0.080)
#d.add_arrow(Arrow(1, 0.000, 0.080, "SYN"))
#d.add_arrow(Arrow(0, 0.100, 0.185, "SYN+ACK"))
#d.add_arrow(Arrow(0, 0.4, 0.8, "Moooo"))
#d.add_arrow(Arrow(1, 0.210, 0.275, "ACK"))
#d.add_arrow(Arrow(1, 0.3, 0.8, "Wooooooooooooooooooooo"))
#
#d.add_arrow(Arrow(0, 0.9, 0.9, "Hi"))
#d.add_arrow(Arrow(1, 0.95, 0.95, "Hello"))
#d.render()

d = Display(max_time=1.0)

def tcp_opts(opts):
    i = 0
    while i < len(opts):
        kind, opt_len = struct.unpack('>BB', opts[i:i+2])
        opt_data = ''

        if kind == 0x01:
            # NOP has no opt len
            opt_len = 1

        if opt_len > 2:
            opt_data = opts[i+2:i+opt_len]

        i += opt_len
        yield (kind, opt_data)


def get_tcp_ts(opts):
    for (opt_kind, opt_data) in tcp_opts(opts):
        if opt_kind == 0x08:
            # TCP timestamps
            value, echo = struct.unpack('>LL', opt_data)
            return (value, echo)
    return (None, None)

def rtt_add_seq(rtt_seqs, pkt):
    tcp = pkt.data.data
    data_len = len(tcp.data)
    if (tcp.flags & (dpkt.tcp.TH_SYN | dpkt.tcp.TH_FIN)):
        data_len += 1
    if data_len > 0:
        rtt_seqs[tcp.seq + data_len] = pkt.ts

def rtt_check_ack(rtt_seqs, pkt, cur_rtt):
    tcp = pkt.data.data
    if tcp.ack in rtt_seqs:
        rtt = (pkt.ts - rtt_seqs[tcp.ack]) / 1000000.0
        if cur_rtt is None or rtt < cur_rtt:
            cur_rtt = rtt
    return cur_rtt




# first pass:
# 1) get first packet time
# 2) get client (whoever sends SYN? whoever sends first?)
# 3) estimate RTT t(SYN-ACK) - t(SYN)
# 4) get starting TCP timestamps (in SYN and SYN-ACK)
# 5) get last TCP timestamp from each, and calculate TCP-timestamp slope
# 6) TODO: get better RTT estimate (minimum!!)
# 7) ???
# 8) Profit
pcap = PcapReader(open(sys.argv[1], 'r'))
first_pkt = True
latest_syn = None
client_ip = None
server_ip = None
client_first_tcp_ts = None
server_first_tcp_ts = None
latest_client_pkt = None
latest_server_pkt = None
client_rtt_seqs = {}
server_rtt_seqs = {}
rtt = 0.0
client_rtt = None
server_rtt = None
for pkt in pcap.packets():

    ip = pkt.data
    tcp = ip.data

    if first_pkt:
        first_pkt = False
        # 1) get first packet time
        start_time = pkt.ts
        # 2) get client (whoever sends first if no SYN)
        client_ip = ip.src
        client_port = tcp.sport
        server_ip = ip.dst
        server_port = tcp.dport

    if tcp.flags == dpkt.tcp.TH_SYN:
        # 2) get client (whoever sends SYN)
        client_ip = ip.src
        client_port = tcp.sport
        server_ip = ip.dst
        server_port = tcp.dport

        latest_syn = pkt

    elif tcp.flags == (dpkt.tcp.TH_SYN | dpkt.tcp.TH_ACK):
        # 3) estimate RTT t(SYN-ACK) - t(SYN)
        rtt = (pkt.ts - latest_syn.ts) / 1000000.0


    # 4) get starting TCP timestamps (in SYN and SYN-ACK)
    if ip.src == client_ip and tcp.sport == client_port:
        if client_first_tcp_ts == None:
            # first client tcp timestamp packet
            client_first_tcp_ts, echo_reply = get_tcp_ts(tcp.opts)
            client_first_real_ts = pkt.ts
        else:
            latest_client_pkt = pkt

        rtt_add_seq(client_rtt_seqs, pkt)
        client_rtt = rtt_check_ack(server_rtt_seqs, pkt, client_rtt)

    elif ip.dst == client_ip and tcp.dport == client_port:
        if server_first_tcp_ts == None:
            # first server tcp timestamp packet
            server_first_tcp_ts, echo_reply = get_tcp_ts(tcp.opts)
            server_first_real_ts = pkt.ts
        else:
            latest_server_pkt = pkt

        rtt_add_seq(server_rtt_seqs, pkt)
        last_rtt = server_rtt
        server_rtt = rtt_check_ack(client_rtt_seqs, pkt, server_rtt)

    # 6) TODO: get better RTT estimate (minimum!!)
    # when we get a packet that increases the sequence
    # number (SYN, FIN, or data) to a new max (TODO: wrap),
    # keep that time around. The first ACK for that is an RTT.
    #>0.000 [0-10]
    #>0.005 [10-20]
    #<0.0


# 5) get last TCP timestamp from each, and calculate TCP-timestamp slope
client_last_tcp_ts, echo_reply = get_tcp_ts(latest_client_pkt.data.data.opts)
client_last_real_ts = latest_client_pkt.ts

server_last_tcp_ts, echo_reply = get_tcp_ts(latest_server_pkt.data.data.opts)
server_last_real_ts = latest_server_pkt.ts

client_tcp_ts_per_sec = (client_last_tcp_ts - client_first_tcp_ts) / ((client_last_real_ts - client_first_real_ts)/1000000.0)
server_tcp_ts_per_sec = (server_last_tcp_ts - server_first_tcp_ts) / ((server_last_real_ts - server_first_real_ts)/1000000.0)

# we really only care about the server I guess...
# given a tcp_ts, we want server_first_tcp_ts to map to (server_first_real_ts - rtt/2),
# then use a slope of server_tcp_ts_per_sec thereafter
# e.g. ((tcp_ts - server_first_tcp_ts) / server_tcp_ts_per_sec) - rtt/2



#rtt = 0.0252
rtt = min(max(client_rtt, server_rtt), rtt)
print 'Calculated client: %s:%d, RTT: %f seconds (client: %f s, server: %f s), client: %f tcp_ts/sec server: %f tcp_ts/sec' % \
    (socket.inet_ntoa(client_ip), client_port, rtt, client_rtt, server_rtt, client_tcp_ts_per_sec, server_tcp_ts_per_sec)

pcap = PcapReader(open(sys.argv[1], 'r'))
for pkt in pcap.packets():
    recv_ts = (pkt.ts - start_time) / 1000000.0
    ip = pkt.data
    tcp = ip.data
    direction = (ip.src == client_ip and tcp.sport == client_port)

    send_time = recv_ts
    recv_time = recv_ts
    if direction:
        # client; shift end time + rtt
        recv_time += rtt/2.0
        #print 'Send %f - %f' % (send_time, recv_time)
    else:
        # server; set start time based off tcp timestamp
        value, echo = get_tcp_ts(tcp.opts)
        if value == None:
            send_time -= rtt/2.0
        else:
            # e.g. ((tcp_ts - server_first_tcp_ts) / server_tcp_ts_per_sec) - rtt/2
            diff = ((value - server_first_tcp_ts) / server_tcp_ts_per_sec) + (server_first_real_ts - start_time)/1000000.0 - rtt/2.0
            send_time = diff
            #print 'Adjusting from %f sec to %f sec' % (recv_time, send_time)
            #start_time = 0
    #print 'recvd at %f, tcp ts %d, determined %f -> %f  --- %s' % (recv_ts, server_first_tcp_ts, send_time, recv_time, pkt.__repr__())

    d.add_arrow(Arrow(direction, send_time, recv_time, flags_to_str(pkt.data.data.flags)))

d.render()

clock = pygame.time.Clock()

drag_start = None
drag_start_time = None

#input handling (somewhat boilerplate code):
while True:
    clock.tick(10)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit(0)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 5:
                # scroll down/out
                y = event.pos[1]
                d.adjust_max_time(False, y)
                d.render()
            elif event.button == 4:
                # scroll up/in
                y = event.pos[1]
                d.adjust_max_time(True, y)
                d.render()
            elif event.button == 1:
                drag_start = event.pos[1]
                drag_start_time = d.offset_time
        elif drag_start != None and event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            drag_start = None
            drag_start_time = None
        elif drag_start != None and event.type == pygame.MOUSEMOTION:
            offset_px = drag_start - event.pos[1]
            d.offset_time = drag_start_time + d.px_to_time(offset_px)
            d.render()
