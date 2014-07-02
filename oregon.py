import binascii

import protocols
import utils
import os, os.path, sys

# (c1) - Oregon Scientific RF Protocol Description pdf
# (c2) http://jeelabs.net/projects/cafe/wiki/Decoding_the_Oregon_Scientific_V2_protocol
# (c3) https://www.domotiga.nl/projects/domotiga/repository/revisions/master/entry/DomotiGa3/.src/CRFXComRX.class


class OregonV2ProtocolHandler(protocols.BaseRCProtocolHandler):
    name = "oregon"

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

        # 0x?ADC, #RTHN318   (c3)

        0xFA28 : SENSOR_CLASS_TEMP_HYGRO_BARO, # THGR810 (c3)
        # 0x?ACC, # RTGR328N (c3)

        0xCA2C: SENSOR_CLASS_TEMP_HYGRO, #THGR328 (c3)
        0xFAB8: SENSOR_CLASS_TEMP_HYGRO, # outside temp/hygro WTGR800 (c3)
        0x1A3D: SENSOR_CLASS_TEMP_HYGRO, # Outside Temp-Hygro THGR918, Oregon-THGRN228NX, Oregon-THGN500 (c2, c3)

        0x5A5D: SENSOR_CLASS_TEMP_HYGRO_BARO, # Inside Temp-Hygro-Baro BTHR918 (c2,c3)

        0x5A6D: SENSOR_CLASS_TEMP_HYGRO_BARO , # BTHR918N,BTHR968 (c3)
    }





    def tryDecode(self, data):
        """ Oregon v2 protocol


        """
        bitstream = utils.get_bits(data)
        #~ print "before strip tail", bitstream
        bitstream = utils.strip_tail(bitstream, ignore_bits=3)
        #~ print "aft strip tail", bitstream
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
        #~ print len(packet)
        #~ print "AS"
        #~ if len(packet) not in  (80, 81):
            #~ return

        if  (len(packet) < 56) or (len(packet) > 89):
            return

        nibbles = [int(utils.invert(s[::-1]),2) for s in utils.batch_gen(packet[1:],4)]

        #~ print nibbles, len(nibbles)
        #~ print [hex(x)[2:] for x in nibbles]


        if (len(nibbles) < 14) or (len(nibbles) > 21):
            return

        sensor_type = ((nibbles[1] << 12)+(nibbles[0] << 8)+(nibbles[3] << 4) + nibbles[2])
        channel = nibbles[5]
        rolling_code = (nibbles[7] << 4) + nibbles[6]

        #~ print "sensor_type=",hex(sensor_type)

        expected_checksum = sum(nibbles[:-4]) - 0xA
        checksum = nibbles[-3] * 16 + nibbles[-4]

        if checksum != expected_checksum:
            return

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
                print "temp=", temp
                kw['temp'] = str(temp)

        if self.FORMAT_HUM_1 in capabilities:
            if len(nibbles) - 4 > 14:
                humidity = nibbles[14] * 10 + nibbles[13]
                kw['humidity'] = str(humidity)

        #~ print nibbles[17], nibbles[-3]



        return kw
