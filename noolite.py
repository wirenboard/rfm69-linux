#coding: utf-8
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


class NooliteCommands(object):
    # todo py3.4 enums

    SetLevel = 6
    On = 2
    Off = 0
    Switch = 4
    Bind = 15
    Unbind = 9
    LoadPreset = 7
    SavePreset = 8
    StopReg = 10
    RollColor = 16
    SwitchColor = 17
    SwitchMode = 18
    SwitchSpeed = 19
    SetColor = 6
    SlowDown = 1
    SlowUp = 3
    SlowSwitch = 5
    SlowStop = 10









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
        #~ print "calcChecksum"
        #~ print "flip_bit=", flip_bit
        #~ print "cmd=", cmd
        #~ print "addr=", addr
        #~ print "fmt=", fmt
        #~ print "args=", args

        addr_hi = addr >> 8
        addr_lo = addr & 0x00ff

        if cmd < 16:
            data = chr(((cmd << 1) | flip_bit) << 3)
        else:
            data = chr(flip_bit << 7) + chr(cmd)

        #~ if fmt == 1:
        for arg in args:
            data += chr(arg)


        data+=  chr(addr_lo) + chr(addr_hi) +chr(fmt)
        #~ print "data=", binascii.hexlify(data)
        return crc8_maxim(data)

    def parsePacket(self, packet):
        #~ print len(packet)
        if len(packet) < 38:
            return
        remainder =  (len(packet) - 6 ) % 4
        if remainder != 0:
            packet += '0'*(4-remainder)



        crc = int(packet[-8:][::-1], 2)
        fmt = int(packet[-16:-8][::-1], 2)
        addr_lo = int(packet[-32:-24][::-1], 2)
        addr_hi = int(packet[-24:-16][::-1], 2)
        addr = (addr_hi << 8)  + addr_lo


        if fmt < 4:
            sextet_1 = packet[:6]
            flip_bit = int(sextet_1[1], 2)
            cmd = int(sextet_1[2:][::-1], 2)
            args_data = packet[6:-32]
        else:
            dectet_1 = packet[:10]
            flip_bit = int(dectet_1[1], 2)
            cmd = int(dectet_1[2:][::-1], 2)

            args_data = packet[10:-32]


        #~ print "fmt=", fmt, len(args_data)
        #~ print args_data
        if fmt == 0:
            if len(args_data) != 0:
               return
        elif fmt == 1:
            if len(args_data) != 8:
               return
        elif fmt == 3:
            if len(args_data) != 32:
               return
        elif fmt == 4:
            if len(args_data) != 0:
               return
        elif fmt == 7:
            if len(args_data) != 32:
               return
        else:
            return

        if args_data:
            args = [int(x[::-1], 2) for x in utils.batch_gen(args_data, 8, align_right=True)]
        else:
            args = []

        return flip_bit, cmd, addr, fmt, crc, args

    def tryDecode(self, data):
        bitstream = utils.get_bits(data)
        #~ print bitstream, len(bitstream)
        bitstream = utils.strip_preamble(bitstream, ignore_bits=30)


        bitstream = utils.strip_to_pause(bitstream, zero_bits = 8 * 3)

        #~ print bitstream, len(bitstream)

        #~ print "bitstream=",  bitstream, len(bitstream)
        #~ if '000' in bitstream[2:]:
                #~ print utils.manchester_decode(bitstream[2:][:bitstream[2:].index('000')])




        parts = bitstream.rsplit('000')
        if parts[0] == '':
            parts = parts[1:]
        #~ if len(parts) != 2:
            #~ return

        for part in parts:
            first_copy = part
            #~ print "first_copy=", first_copy
            #~ second_copy = ss[81:]

            packet = utils.manchester_decode('0' + first_copy)

            #~ if packet.startswith('00'):
                #~ packet = packet[2:]

            #~ print len(packet), packet


            parsed_packet = self.parsePacket(packet)
            if parsed_packet is None:
                continue

            flip_bit, cmd, addr, fmt, crc, args = parsed_packet
            #~ print "args=", args
            crc_expected = self.calcChecksum(flip_bit, cmd, addr, fmt, args)
            #~ print crc, crc_expected
            if crc != crc_expected:
                continue


            raw = packet
            kw = {}
            kw['flip'] = str(flip_bit)
            kw['cmd'] = str(cmd)
            kw['fmt'] = hex(fmt)[2:]
            kw['addr'] = hex(addr)[2:]
            kw['raw'] = raw

            if (fmt == 7) and (cmd == 21):
                temp = ((args[1] & 0x0F) << 8) + args[0]
                if temp > 0x7ff:
                    temp = temp - 0x1000
                temp = temp * 0.1

                rel_humidity = args[2]

                lowbat = 1 if (args[1] & 0b10000000) else 0



                kw['temp'] = "%.1f" % temp
                kw['humidity'] =str(rel_humidity)
                kw['lowbat'] = str(lowbat)

            elif cmd == 6:
                kw['level'] = str(args[0])


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

#ch:2 r:1 g:1 b:1        110110          10000000 10000000 10000000 00000000 10011111 10100100 11000000 11001011  fmt=3
#ch:2 r:1 g:1 b:2        100110          10000000 10000000 01000000 00000000 10011111 10100100 11000000 11101101  fmt=3
#ch:2 r:255 g:255 b:255  110110          11111111 11111111 11111111 00000000 10011111 10100100 11000000 10110001  fmt=3
#ch:14 r:1 g:1 b:2       110110          10000000 10000000 01000000 00000000 11111111 10100100 11000000 00110010  fmt=3
#ch:14 r:1 g:1 b:2       100110          10000000 10000000 01000000 00000000 11111111 10100100 11000000 01100110  fmt=3
#ch:15 r:1 g:1 b:2       110110          10000000 10000000 01000000 00000000 11111111 10100100 11000000 00110010  fmt=3
#ch:2 switch mode        11     01001000                                     10011111 10100100 00100000 00010101  fmt=4, cmd=18
#ch:2 switch color       11     10001000                                     10011111 10100100 00100000 00000100  fmt=4, cmd=17
#ch:2 lvl=46             110110                                     01110100 10011111 10100100 10000000 10010100  fmt=1
#ch:2 cmd=10             110101                                              10011111 10100100 00000000 00010001  fmt=0
#ch:2 off_ch             110000                                              10011111 10100100 00000000 10000100  fmt=0

#
# temp/hum:
#     flip, 2 bit -->    10     10101000 11100000 10000101 00100110 11111111 11111001 00101000 11100000 00111000
#     cmd 8 bit              ---^    |           | ^ ^    ^        ^     addr_lo  addr_hi    fmt      crc
#     temperature, signed, 0.1C  --> |-- 12 bit -| | |    |        |
#     unknown, 3bit, 0b010  ------->---------------- |    |        |
#     bat low, 1bit   ------------->------------------    |        |
#     humidity, 8 bit ------------->-----------------------        |
#     unknown, 8 bit, always 0xFF so far -------->------------------



