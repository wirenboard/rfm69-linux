import binascii

import protocols
import utils
import os, os.path, sys

crc8_table = [
    0x00,0x5E,0xBC,0xE2,0x61,0x3F,0xDD,0x83,
    0xC2,0x9C,0x7E,0x20,0xA3,0xFD,0x1F,0x41,
    0x9D,0xC3,0x21,0x7F,0xFC,0xA2,0x40,0x1E,
    0x5F,0x01,0xE3,0xBD,0x3E,0x60,0x82,0xDC,
    0x23,0x7D,0x9F,0xC1,0x42,0x1C,0xFE,0xA0,
    0xE1,0xBF,0x5D,0x03,0x80,0xDE,0x3C,0x62,
    0xBE,0xE0,0x02,0x5C,0xDF,0x81,0x63,0x3D,
    0x7C,0x22,0xC0,0x9E,0x1D,0x43,0xA1,0xFF,
    0x46,0x18,0xFA,0xA4,0x27,0x79,0x9B,0xC5,
    0x84,0xDA,0x38,0x66,0xE5,0xBB,0x59,0x07,
    0xDB,0x85,0x67,0x39,0xBA,0xE4,0x06,0x58,
    0x19,0x47,0xA5,0xFB,0x78,0x26,0xC4,0x9A,
    0x65,0x3B,0xD9,0x87,0x04,0x5A,0xB8,0xE6,
    0xA7,0xF9,0x1B,0x45,0xC6,0x98,0x7A,0x24,
    0xF8,0xA6,0x44,0x1A,0x99,0xC7,0x25,0x7B,
    0x3A,0x64,0x86,0xD8,0x5B,0x05,0xE7,0xB9,
    0x8C,0xD2,0x30,0x6E,0xED,0xB3,0x51,0x0F,
    0x4E,0x10,0xF2,0xAC,0x2F,0x71,0x93,0xCD,
    0x11,0x4F,0xAD,0xF3,0x70,0x2E,0xCC,0x92,
    0xD3,0x8D,0x6F,0x31,0xB2,0xEC,0x0E,0x50,
    0xAF,0xF1,0x13,0x4D,0xCE,0x90,0x72,0x2C,
    0x6D,0x33,0xD1,0x8F,0x0C,0x52,0xB0,0xEE,
    0x32,0x6C,0x8E,0xD0,0x53,0x0D,0xEF,0xB1,
    0xF0,0xAE,0x4C,0x12,0x91,0xCF,0x2D,0x73,
    0xCA,0x94,0x76,0x28,0xAB,0xF5,0x17,0x49,
    0x08,0x56,0xB4,0xEA,0x69,0x37,0xD5,0x8B,
    0x57,0x09,0xEB,0xB5,0x36,0x68,0x8A,0xD4,
    0x95,0xCB,0x29,0x77,0xF4,0xAA,0x48,0x16,
    0xE9,0xB7,0x55,0x0B,0x88,0xD6,0x34,0x6A,
    0x2B,0x75,0x97,0xC9,0x4A,0x14,0xF6,0xA8,
    0x74,0x2A,0xC8,0x96,0x15,0x4B,0xA9,0xF7,
    0xB6,0xE8,0x0A,0x54,0xD7,0x89,0x6B,0x35,
    ]

def crc8_maxim(data):
    crc = 0
    for i, ch in enumerate(data):
        crc = crc8_table[ord(ch) ^ crc]
    return crc



class NooliteProtocolHandler(protocols.BaseRCProtocolHandler):
    name = "noo"
    def __init__(self):
        self.addr = None
        self.flip = 0
        self.getAddress()

    def getAddress(self):
        if self.addr is None:
            # read mac
            for iface in ('eth0', 'wlan0'):
                mac_path = '/sys/class/net/%s/address' % iface
                if os.path.exists(mac_path):
                    try:
                        parts = open(mac_path).read().strip().split(':')
                        self.addr = (int(parts[-2], 16) << 8) + int(parts[-1], 16)
                        print self.addr
                        break
                    except:
                        pass


        return self.addr


    def calcChecksum(self, flip_bit, cmd, addr, fmt = 0,  args=[]):
        addr_hi = addr >> 8
        addr_lo = addr & 0x00ff

        data = chr(((cmd << 1) | flip_bit) << 3)
        if fmt == 1:
            data += chr(args[0])
        data+=  chr(addr_lo) + chr(addr_hi) +chr(fmt)
        return crc8_maxim(data)

    def parsePacket(self, packet):
        sextet_1 = packet[:6]
        flip_bit = int(sextet_1[1], 2)
        cmd = int(sextet_1[2:][::-1], 2)


        addr_lo = int(packet[6:14][::-1], 2)
        addr_hi = int(packet[14:22][::-1], 2)
        addr = (addr_hi << 8)  + addr_lo

        fmt = int(packet[22:30][::-1], 2)

        crc = int(packet[30:38][::-1], 2)

        return flip_bit, cmd, addr, fmt, crc

    def tryDecode(self, data):
        bitstream = utils.get_bits(data)
        #~ print bitstream, len(bitstream)
        bitstream = utils.strip_preamble(bitstream)
        bitstream = utils.strip_tail(bitstream, ignore_bits=4)

        #~ print bitstream, len(bitstream)
        if '000' in bitstream[2:]:
                print utils.manchester_decode(bitstream[2:][:bitstream[2:].index('000')])


        if len(bitstream) not in (156, 157, 327, 315):
            return

        first_copy = bitstream[2:79]
        #~ second_copy = ss[81:]

        packet = utils.manchester_decode(first_copy)
        if len(packet) != 38:
            return
        flip_bit, cmd, addr, fmt, crc = self.parsePacket(packet)
        crc_expected = self.calcChecksum(flip_bit, cmd, addr, fmt)

        if crc != crc_expected:
            return




        raw = packet
        kw = {}
        kw['flip'] = str(flip_bit)
        kw['cmd'] = str(cmd)
        kw['fmt'] = hex(fmt)[2:]
        kw['addr'] = hex(addr)[2:]
        kw['raw'] = raw
        #~ kw['crc'] = hex(crc)[2:]
        #~ kw['crc_e'] = hex(crc_expected)[2:]


        return kw

    def tryEncode(self, kw):
        if 'raw' in kw:
            packet = kw['raw']
        else:
            if 'flip' in kw:
                self.flip = int(kw['flip'])
            else:
                self.flip = 0 if self.flip else 1

            if 'addr' in kw:
                addr = int(kw['addr'], 16)
            else:
                addr = self.addr

            fmt = 0
            args = []

            cmd = int(kw['cmd'])

            if cmd == 6:
                fmt = 1
                args = [ int(kw['arg']) ]

            if 'crc' in kw:
                crc = int(kw['crc'])
            else:
                crc = self.calcChecksum(self.flip, cmd, addr, fmt, args)

            addr_hi = addr >> 8
            addr_lo = addr & 0x00ff

            args_data = ''
            if fmt == 1:
                args_data = bin(args[0])[2:].zfill(8)[::-1]
            elif fmt == 4:
                args_data = bin(args[0])[2:].zfill(4)[::-1],
            elif fmt == 3:
                assert len(args) == 4
                args_data = "".join(bin(args[i])[2:].zfill(9)[::-1] for i in xrange(4))

            packet = "".join(( '1',
                                str(self.flip),
                                bin(cmd)[2:].zfill(4)[::-1],
                                args_data,
                                bin(addr_lo)[2:].zfill(8)[::-1],
                                bin(addr_hi)[2:].zfill(8)[::-1],
                                bin(fmt)[2:].zfill(8)[::-1],
                                bin(crc)[2:].zfill(8)[::-1] ))

        #~ print "packet: ", packet




        enc_packet = utils.manchester_encode(packet)
        bitstream = "".join((utils.manchester_encode('0'*41),
                            '00',
                             enc_packet,
                             '000',
                             enc_packet))



        data = utils.get_bytes(bitstream)
        #~ print data
        return data

#ch:2 r:1 g:1 b:1        110110 10000000 10000000 10000000 00000000 10011111 10100100 11000000 11001011  fmt=3
#ch:2 r:1 g:1 b:2        100110 10000000 10000000 01000000 00000000 10011111 10100100 11000000 11101101  fmt=3
#ch:2 r:255 g:255 b:255  110110 11111111 11111111 11111111 00000000 10011111 10100100 11000000 10110001  fmt=3
#ch:14 r:1 g:1 b:2       110110 10000000 10000000 01000000 00000000 11111111 10100100 11000000 00110010  fmt=3
#ch:14 r:1 g:1 b:2       100110 10000000 10000000 01000000 00000000 11111111 10100100 11000000 01100110  fmt=3
#ch:15 r:1 g:1 b:2       110110 10000000 10000000 01000000 00000000 11111111 10100100 11000000 00110010  fmt=3
#ch:2 switch mode        110100                                1000 10011111 10100100 00100000 00010101  fmt=4
#ch:2 switch mode        110100                                1000 10011111 10100100 00100000 00010101  fmt=4
#ch:2 switch color       111000                                1000 10011111 10100100 00100000 00000100  fmt=4
#ch:2 lvl=46             110110                            01110100 10011111 10100100 10000000 10010100  fmt=1
#ch:2 cmd=10             110101                                     10011111 10100100 00000000 00010001  fmt=0
#ch:2 off_ch             110000                                     10011111 10100100 00000000 10000100  fmt=0
