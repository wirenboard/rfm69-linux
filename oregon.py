#coding: utf-8
import binascii

import protocols
import utils
import os, os.path, sys

# (c1) - Oregon Scientific RF Protocol Description pdf
# (c2) http://jeelabs.net/projects/cafe/wiki/Decoding_the_Oregon_Scientific_V2_protocol
# (c3) https://www.domotiga.nl/projects/domotiga/repository/revisions/master/entry/DomotiGa3/.src/CRFXComRX.class

def oregon_crc8(data):
    if not hasattr(oregon_crc8, "table"):
        oregon_crc8.table = [0, 169, 185, 16, 153, 48, 32, 137, 217, 112, 96, 201, 64, 233, 249, 80, 89, 240, 224, 73, 192, 105, 121, 208, 128, 41, 57, 144, 25, 176, 160, 9, 178, 27, 11, 162, 43, 130, 146, 59, 107, 194, 210, 123, 242, 91, 75, 226, 235, 66, 82, 251, 114, 219, 203, 98, 50, 155, 139, 34, 171, 2, 18, 187, 143, 38, 54, 159, 22, 191, 175, 6, 86, 255, 239, 70, 207, 102, 118, 223, 214, 127, 111, 198, 79, 230, 246, 95, 15, 166, 182, 31, 150, 63, 47, 134, 61, 148, 132, 45, 164, 13, 29, 180, 228, 77, 93, 244, 125, 212, 196, 109, 100, 205, 221, 116, 253, 84, 68, 237, 189, 20, 4, 173, 36, 141, 157, 52, 245, 92, 76, 229, 108, 197, 213, 124, 44, 133, 149, 60, 181, 28, 12, 165, 172, 5, 21, 188, 53, 156, 140, 37, 117, 220, 204, 101, 236, 69, 85, 252, 71, 238, 254, 87, 222, 119, 103, 206, 158, 55, 39, 142, 7, 174, 190, 23, 30, 183, 167, 14, 135, 46, 62, 151, 199, 110, 126, 215, 94, 247, 231, 78, 122, 211, 195, 106, 227, 74, 90, 243, 163, 10, 26, 179, 58, 147, 131, 42, 35, 138, 154, 51, 186, 19, 3, 170, 250, 83, 67, 234, 99, 202, 218, 115, 200, 97, 113, 216, 81, 248, 232, 65, 17, 184, 168, 1, 136, 33, 49, 152, 145, 56, 40, 129, 8, 161, 177, 24, 72, 225, 241, 88, 209, 120, 104, 193]

    crc = 0x80
    for item in data:
        crc = oregon_crc8.table[item ^ crc];
    return crc




class OregonV2V3ProtocolDecoder(object):
    FORMAT_TEMP_1 = 1
    FORMAT_HUM_1 = 2
    FORMAT_PRESSURE_1 = 3

    SENSOR_CLASS_TEMP_ONLY  = (FORMAT_TEMP_1,)
    SENSOR_CLASS_TEMP_HYGRO = (FORMAT_TEMP_1, FORMAT_HUM_1)
    SENSOR_CLASS_TEMP_HYGRO_BARO  = (FORMAT_TEMP_1, FORMAT_HUM_1, FORMAT_PRESSURE_1)

    SENSOR_IDS = {
        # temp/hum from (c1)
        0x1D20 : SENSOR_CLASS_TEMP_HYGRO,
        0xF824 : SENSOR_CLASS_TEMP_HYGRO,
        0xF8B4 : SENSOR_CLASS_TEMP_HYGRO,

        # temp only from (c1)
        0xEC40 : SENSOR_CLASS_TEMP_ONLY,
        0xC844 : SENSOR_CLASS_TEMP_ONLY,
        # Temp/RH plus Barometer from (c1)
        0x5D60 : SENSOR_CLASS_TEMP_HYGRO_BARO,

        # Inside Temp-Hygro (c2), THGN122N,THGR122NX,THGR228N,THGR268
        0x1A2D : SENSOR_CLASS_TEMP_HYGRO,

        # Outside/Water Temp (c2),(c3)  THRN132N,THWR288,AW131; inside temp: THN132N
        0xEA4C : SENSOR_CLASS_TEMP_ONLY,

        # THR128,THx138 (c3)
        0x0A4D : SENSOR_CLASS_TEMP_ONLY,
        #  THWR800 (c3)
        0xCA48 : SENSOR_CLASS_TEMP_ONLY,


        0xFA28 : SENSOR_CLASS_TEMP_HYGRO_BARO, # THGR810 (c3), THGR800 (http://contactless.ru/forums/topic/%D0%BF%D0%BE%D0%B4%D0%B4%D0%B5%D1%80%D0%B6%D0%BA%D0%B0-%D0%B4%D0%B0%D1%82%D1%87%D0%B8%D0%BA%D0%BE%D0%B2-oregon-scientific-v3-0/)

        0xCA2C: SENSOR_CLASS_TEMP_HYGRO, #THGR328 (c3)
        0xFAB8: SENSOR_CLASS_TEMP_HYGRO, # outside temp/hygro WTGR800 (c3)
        0x1A3D: SENSOR_CLASS_TEMP_HYGRO, # Outside Temp-Hygro THGR918, Oregon-THGRN228NX, Oregon-THGN500 (c2, c3)

        0x5A5D: SENSOR_CLASS_TEMP_HYGRO_BARO, # Inside Temp-Hygro-Baro BTHR918 (c2,c3)

        0x5A6D: SENSOR_CLASS_TEMP_HYGRO_BARO , # BTHR918N,BTHR968 (c3)
    }

    for i in xrange(0x0, 0xF + 1):
        # 0x?ADC, #RTHN318   (c3)
        SENSOR_IDS[(i << 12) + 0xADC] = SENSOR_CLASS_TEMP_ONLY

        # 0x?ACC, # RTGR328N (c3)
        SENSOR_IDS[(i << 12) + 0xACC] = SENSOR_CLASS_TEMP_HYGRO


    def decode_packet(self, packet):
        #~ print "decode_packet: ", packet
        if  (len(packet) < 56) or (len(packet) > 89):
            return


        nibbles = [int(utils.invert(s[::-1]),2) for s in utils.batch_gen(packet,4)]

        #~ print nibbles, len(nibbles)
        #~ print [hex(x)[2:] for x in nibbles]
        #~ print [hex(x)[2:] for x in utils.get_bytes(packet)]
        #~ print "".join([hex(x)[2:] for x in nibbles])

        if (len(nibbles) < 14) or (len(nibbles) > 21):
            return

        sensor_type = ((nibbles[1] << 12)+(nibbles[0] << 8)+(nibbles[3] << 4) + nibbles[2])
        channel = nibbles[5]
        rolling_code = (nibbles[7] << 4) + nibbles[6]

        expected_checksum = sum(nibbles[:-4]) - 0xA
        checksum = nibbles[-3] * 16 + nibbles[-4]

        #~ print checksum, expected_checksum
        if checksum != expected_checksum:
            return


        #~ crc_buffer = [((h<<4) + l)  for (l, h) in utils.batch_gen(nibbles[:-4], 2)]
        #~ expected_crc = oregon_crc8(crc_buffer)
        #~ crc = nibbles[-1] * 16 + nibbles[-2]
        #~ print [hex(x) for x in crc_buffer]#~
        #~ print hex(expected_crc), hex(crc)



        raw = packet
        kw = {}
        kw['raw'] = raw
        kw['channel'] = str(channel)
        kw['type'] = hex(sensor_type)[2:]
        kw['code'] = hex(rolling_code)[2:]


        capabilities = self.SENSOR_IDS.get(sensor_type, ())

        if self.FORMAT_TEMP_1 in capabilities:
            if len(nibbles) - 4 > 12:
                temp = nibbles[11] * 10 + nibbles[10] + nibbles[9] * 0.1
                if nibbles[12] != 0:
                    temp = -1.0 * temp
                kw['temp'] = str(temp)

        if self.FORMAT_HUM_1 in capabilities:
            if len(nibbles) - 4 > 14:
                humidity = nibbles[14] * 10 + nibbles[13]
                kw['humidity'] = str(humidity)

        #~ print nibbles[17], nibbles[-3]



        return kw



class OregonV2ProtocolHandler(OregonV2V3ProtocolDecoder, protocols.BaseRCProtocolHandler):
    name = "oregon"

    def tryDecode(self, data):
        """ Oregon v2 protocol
        """

        bitstream = utils.get_bits(data)
        #~ print "before strip tail", bitstream
        bitstream = utils.strip_tail(bitstream, ignore_bits=3)
        #~ print "aft strip tail", bitstream
        slips, bitsream_dec_1 = utils.manchester_decode_ext(bitstream)
        #~ print bitsream_dec_1

        # remove trailing '1's
        while bitsream_dec_1.startswith('1'):
            bitsream_dec_1 = bitsream_dec_1[1:]


        slips, packet = utils.manchester_decode_ext(bitsream_dec_1)
        #~ print slips
        if len(slips) > 4:
            return
        # remove trailing '1's
        while packet.startswith('1'):
            packet = packet[1:]

        return self.decode_packet(packet[1:])


class OregonV3ProtocolHandler(OregonV2V3ProtocolDecoder, protocols.BaseRCProtocolHandler):
    """ Oregon V3 protocol handler"""

    name = "oregon3"

    def tryDecode(self, data):
        bitstream = utils.get_bits(data)
        #~ print "before strip tail", bitstream
        bitstream = utils.strip_tail(bitstream, ignore_bits=3)
        bitstream = utils.strip_preamble(bitstream)

        slips, packet = utils.manchester_decode_ext(bitstream)
        #~ print "slips, packet:", slips, packet

        return self.decode_packet(packet)




