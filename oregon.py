import binascii

import protocols
import utils
import os, os.path, sys


class OregonV2ProtocolHandler(protocols.BaseRCProtocolHandler):
    name = "oregon"

    def tryDecode(self, data):
        bitstream = utils.get_bits(data)
        bitstream = utils.strip_tail(bitstream, ignore_bits=3)
        #~ print bitstream
        slips, bitsream_dec_1 = utils.manchester_decode_ext(bitstream)
        #~ print bitsream_dec_1

        #~ # remove trailing '1's
        while bitsream_dec_1.startswith('1'):
            bitsream_dec_1 = bitsream_dec_1[1:]
        #~ print bitsream_dec_1


        slips, packet = utils.manchester_decode_ext(bitsream_dec_1)
        #~ print slips
        if len(slips) > 4:
            return
        #~ # remove trailing '1's
        while packet.startswith('1'):
            packet = packet[1:]
        #~ print packet
        print len(packet)
        #~ print "AS"
        if len(packet) not in  (80, 81):
            return

        nibbles = [int(utils.invert(s[::-1]),2) for s in utils.batch_gen(packet[1:],4)]


        temp = nibbles[11] * 10 + nibbles[10] + nibbles[9] * 0.1
        if nibbles[12] != 0:
            temp = -1.0 * temp

        humidity = nibbles[14] * 10 + nibbles[13]
        channel = nibbles[5]

        sensor_type = ((nibbles[1] << 12)+(nibbles[0] << 8)+(nibbles[3] << 4) + nibbles[2])
        rolling_code = (nibbles[7] << 4) + nibbles[6]

        raw = packet
        kw = {}
        kw['raw'] = raw
        kw['temp'] = str(temp)
        kw['humidity'] = str(humidity)
        kw['channel'] = str(channel)
        kw['type'] = hex(sensor_type)[2:]
        kw['code'] = hex(rolling_code)[2:]

        return kw
