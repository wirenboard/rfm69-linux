#coding: utf-8
# LIRC mode2 receiver
# use with lirc_rpi kernel module and 433MHz receiver/transmitter connected to it

import ctypes
import threading
import collections

import utils
import select

class LIRCMode2(object):
    def __init__(self, devname):
        self.max_packet_size = 500
        self.min_packet_size = 5
        self.max_bit_duration = 20000 # in usecs
        self.read_timeout = 0.5

        self.devname = devname
        self.fd = None
        self.open()


    def close(self):
        if self.fd:
            self.fd.close()

    def open(self):
        if self.fd is None:
            self.close()

        self.fd = open(self.devname, 'rw')


    def read_packet(self, *args, **kwargs):
        while True:
            packet = self._read_packet(*args, **kwargs)
            if len(packet) >= self.min_packet_size:
                return packet



    def _read_packet(self, timeout = None):
        if timeout is None:
            timeout = self.read_timeout

        raw_c = ctypes.c_int(0)
        last_type = None

        packet = []

        while True:
            if self.fd is None:
                break

            r, w, e = select.select([ self.fd ], [], [], timeout)
            if self.fd not in r:
                # timeout
                break

            nbytes = self.fd.readinto(raw_c)
            if not nbytes:
                break

            duration = raw_c.value & 0x00FFFFFF
            is_pulse = bool(raw_c.value & 0xFF000000)

            if last_type is not None:
                if last_type == is_pulse:
                    print "warning, two %s in row" % ('pulses' if is_pulse else 'pauses')

            chunk = (duration, is_pulse)

            last_type = is_pulse

            if duration <= self.max_bit_duration:
                packet.append(chunk)
            #~ else:
                #~ print "big bit: ", chunk

            if (len(packet) >= self.max_packet_size) or \
                (duration > self.max_bit_duration):


                if packet:
                    break


        return packet




    def on_packet_receive(self):
        print "received packet"


    def _fd_read_thread(self):
        pass
        #~ self._recv_packet_queue.put_discard(packet[:])
        #~ packet = []
        #~ self.on_packet_receive()


