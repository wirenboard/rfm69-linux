#coding: utf-8
import binascii

import protocols
import utils
import os, os.path, sys

# (c1) - Oregon Scientific RF Protocol Description pdf
# (c2) http://jeelabs.net/projects/cafe/wiki/Decoding_the_Oregon_Scientific_V2_protocol
# (c3) https://www.domotiga.nl/projects/domotiga/repository/revisions/master/entry/DomotiGa3/.src/CRFXComRX.class
# update v0.2 2014-11-28 by MaxWolf

def oregon_crc8(data):
    if not hasattr(oregon_crc8, "table"):
        oregon_crc8.table = [0, 169, 185, 16, 153, 48, 32, 137, 217, 112, 96, 201, 64, 233, 249, 80, 89, 240, 224, 73, 192, 105, 121, 208, 128, 41, 57, 144, 25, 176, 160, 9, 178, 27, 11, 162, 43, 130, 146, 59, 107, 194, 210, 123, 242, 91, 75, 226, 235, 66, 82, 251, 114, 219, 203, 98, 50, 155, 139, 34, 171, 2, 18, 187, 143, 38, 54, 159, 22, 191, 175, 6, 86, 255, 239, 70, 207, 102, 118, 223, 214, 127, 111, 198, 79, 230, 246, 95, 15, 166, 182, 31, 150, 63, 47, 134, 61, 148, 132, 45, 164, 13, 29, 180, 228, 77, 93, 244, 125, 212, 196, 109, 100, 205, 221, 116, 253, 84, 68, 237, 189, 20, 4, 173, 36, 141, 157, 52, 245, 92, 76, 229, 108, 197, 213, 124, 44, 133, 149, 60, 181, 28, 12, 165, 172, 5, 21, 188, 53, 156, 140, 37, 117, 220, 204, 101, 236, 69, 85, 252, 71, 238, 254, 87, 222, 119, 103, 206, 158, 55, 39, 142, 7, 174, 190, 23, 30, 183, 167, 14, 135, 46, 62, 151, 199, 110, 126, 215, 94, 247, 231, 78, 122, 211, 195, 106, 227, 74, 90, 243, 163, 10, 26, 179, 58, 147, 131, 42, 35, 138, 154, 51, 186, 19, 3, 170, 250, 83, 67, 234, 99, 202, 218, 115, 200, 97, 113, 216, 81, 248, 232, 65, 17, 184, 168, 1, 136, 33, 49, 152, 145, 56, 40, 129, 8, 161, 177, 24, 72, 225, 241, 88, 209, 120, 104, 193]

    crc = 0x80
    for item in data:
        crc = oregon_crc8.table[item ^ crc];
    return crc




class OregonV2V3ProtocolDecoder(object):

    BLOCKTYPE_UNKN = 0
    BLOCKTYPE_T = 1 # temp
    BLOCKTYPE_TH = 2 # temp + hygro
    BLOCKTYPE_UV = 3 # ultraviolet
    BLOCKTYPE_UV2 = 4 # yet another UV
    BLOCKTYPE_W = 5 # wind
    BLOCKTYPE_R = 6 # rain
    BLOCKTYPE_R2 = 7 # yet another rain
    BLOCKTYPE_THB = 8 # temp + hygro + baro

    BLOCK_LEN = {
        BLOCKTYPE_UNKN : 14, # some safe margin
        BLOCKTYPE_T : 14, # temp               a
        BLOCKTYPE_TH : 17, # temp + hygro
        BLOCKTYPE_UV : 14, # ultraviolet
        BLOCKTYPE_UV2 : 15, # yet another UV
        BLOCKTYPE_W : 19, # wind
        BLOCKTYPE_R : 20, # rain
        BLOCKTYPE_R2 : 18, # yet another rain
        BLOCKTYPE_THB : 21, # temp + hygro + baro
    }

    SENSOR_BLOCKTYPE = {

    	#####  devices listed in OregonScientific-RF-Protocols-II.pdf

        # temp only from
        0xEC40 : BLOCKTYPE_T,    # THN132N (?also THRN132N,THWR288,AW131) (THR228N but different message length 153bits vs 129 of THN132N
        0xC844 : BLOCKTYPE_T,    # THWR800

        # temp/hum
        0x1D20 : BLOCKTYPE_TH,   # THGR122NX (?also THGN122N,THGR228N,THGR268)
        0x1D30 : BLOCKTYPE_TH,   # THGR968 (from https://github.com/magellannh/rtl_433/blob/d021325cf1af2ff680ed549f5657ae80494a94f1/src/rtl_433.c)
                                 # THGRN228NX (from https://github.com/1000io/OregonPi/blob/master/Sensor.cpp)
        0xF824 : BLOCKTYPE_TH,   # THGN801 (?also THGR810, THGR800) (http://contactless.ru/forums/topic/%D0%BF%D0%BE%D0%B4%D0%B4%D0%B5%D1%80%D0%B6%D0%BA%D0%B0-%D0%B4%D0%B0%D1%82%D1%87%D0%B8%D0%BA%D0%BE%D0%B2-oregon-scientific-v3-0 )
        0xF8B4 : BLOCKTYPE_TH,   # THGR810 (orig with anemometer) (?also WTGR800)

        0xEC70 : BLOCKTYPE_UV,   # UVR128
        0xD874 : BLOCKTYPE_UV2,  # UVN800

        0x1994 : BLOCKTYPE_W,    # WGR800 (orig anemometer with T/H sensor)
        0x1984 : BLOCKTYPE_W,    # WGR800 (new anemometer w/o T/H sensor)

        0x2914 : BLOCKTYPE_R,    # PCR800
        0x2D10 : BLOCKTYPE_R2,   # RGR968 (also RGR918 https://github.com/1000io/OregonPi/blob/master/Sensor.cpp)

        0x5D60 : BLOCKTYPE_THB   # BTHR968 (?also BTHR918N) (also BTHG968 https://github.com/1000io/OregonPi/blob/master/Sensor.cpp)

        #0x3D00 :

        ##### non-confirmed devices (digits should be redecoded as 1 2(always syncro-'A') 3 4 -> 2(A) 1 4 3 X )

        # THR128,THx138 (c3) -> should be 0x0D4.
        #0x0A4D : SENSOR_CLASS_TEMP_ONLY,

        #0xCA2C: SENSOR_CLASS_TEMP_HYGRO, #THGR328 (c3) 0xCC2.
        #0x1A3D: SENSOR_CLASS_TEMP_HYGRO, # Outside Temp-Hygro THGR918, Oregon-THGRN228NX, Oregon-THGN500 (c2, c3) 0x1D3.

        #0x5A5D: SENSOR_CLASS_TEMP_HYGRO_BARO, # Inside Temp-Hygro-Baro BTHR918 (c2,c3) 0x5D5.

        #0x?CD? : SENSOR_CLASS_TEMP_ONLY # ?RTHN318
        #0x?CC? : SENSOR_CLASS_TEMP_HYGRO # ?RTGR328N
    }


    def decode_temp(self, nibbles, start, kw) :
        if len(nibbles) - start >= 4:
            temp = nibbles[start+2] * 10 + nibbles[start+1] + nibbles[start] * 0.1
            if nibbles[start+3] != 0:
                temp = -1.0 * temp
            kw['temp'] = str(temp) # temperature in C
        else:
            kw['error'].append("temp block too short! ")


    def decode_humidity(self, nibbles, start, kw) :
        if len(nibbles) - start >= 3:
            humidity = nibbles[start+1] * 10 + nibbles[start]
            kw['humidity'] = str(humidity) # humidity in %

            # also 9 for 20.7C 10%; 0xa for 20.5C 10%
            kw['comfort'] = "normal" if (nibbles[start+2] == 0) else ("comfortable" if (nibbles[start+2] == 4) else ("dry" if (nibbles[start+2] == 8) else "wet" if (nibbles[start+2] == 0xc) else hex(nibbles[start+2])))
#            kw['comfort'] = "normal" if (nibbles[start+1] == 0) else ("comfortable" if (nibbles[start+1] == 4) else "Unknown")
        else:
            kw['error'].append("humidity block too short! ");

    def decode_rain(self, nibbles, start, kw) :
        if len(nibbles) - start >= 10:
            rain_rate = (nibbles[start+3]*10 + nibbles[start+2] + nibbles[start+1]*0.1 + nibbles[start]*0.01) * 25.4 # convert from inch/hour
            rain_total = (nibbles[start+9]*1000 + nibbles[start+8]*100 + nibbles[start+7]*10 + nibbles[start+6] + nibbles[start+5]*0.1 + nibbles[start+4] * 0.01) * 25.4
            kw['rain_rate'] = str(rain_rate) # rainfall rate in mm/hour
            kw['rain_total'] = str(rain_total) # total rainfall in mm
        else:
            kw['error'].append("rain block too short! ");

    def decode_rain2(self, nibbles, start, kw) :
        if len(nibbles) - start >= 8:
            rain_rate = nibbles[start+2] * 10 + nibbles[start+1] + nibbles[start] * 0.1
            rain_total = nibbles[start+7] * 1000 + nibbles[start+6] * 100 + nibbles[start+5] * 10 + nibbles[start+4] + nibbles[start+3] * 0.1
            kw['rain_rate'] = str(rain_rate) # rain rate in mm/hour
            kw['rain_total'] = str(rain_total) # total rain in mm
        else:
            kw['error'].append("rain2 block too short! ");

    def decode_UV(self, nibbles, start, kw) :
        if len(nibbles) - start >= 2:
            uv = nibbles[start+1]*10 + nibbles[start]
            kw['uv'] = str(uv) # UV index
        else:
            kw['error'].append("UV block too short! ");

    def decode_wind(self, nibbles, start, kw) :
        if len(nibbles) - start >= 9:
            kw['wind_dir'] = str(nibbles[start]*22.5) # limited to 16 discrete values

            windSpeed = nibbles[start+5]*10 + nibbles[start+4] + nibbles[start+3]*0.1
            windAvgSpeed = nibbles[start+8]*10 + nibbles[start+7] + nibbles[start+6]*0.1
            kw['wind_speed'] = str(windSpeed) # wind speed in m/s
            kw['wind_avg_speed'] = str(windAvgSpeed) # average wind speed in m/s
        else:
            kw['error'].append("wind block too short! ");

    def decode_baro(self, nibbles, start, kw) :
        if len(nibbles) - start >= 4:
            pressure = nibbles[start+1] * 10 + nibbles[start]
            kw['pressure'] = str(pressure + 856) # atmospheric pressure in millibars
            kw['forecast'] = "cloudy" if (nibbles[start+2] == 2) else ("rainy" if (nibbles[start+2] == 3) else ("partly cloudy" if (nibbles[start+2] == 6) else "sunny" if (nibbles[start+2] == 0xc) else hex(nibbles[start+2])))
        else:
            kw['error'].append("baro block too short! ")

    ##################
    #
    #
    def decode_packet(self, packet):

        raw = packet
        kw = {}

#        print "decode_packet: ", packet
        if  (len(packet) < 56) or (len(packet) > 89):
            print "!invalid packet length: ", len(packet)
            #return


        nibbles = [int(utils.invert(s[::-1]),2) for s in utils.batch_gen(packet,4)]

        #~ print nibbles, len(nibbles)
        #~ print [hex(x)[2:] for x in nibbles]
        #~ print [hex(x)[2:] for x in utils.get_bytes(packet)]
        #~ print "".join([hex(x)[2:] for x in nibbles])

        if len(nibbles) < 14:
            # packet too short -> it's fatal
#            print "!invalid nibbles length: ", len(nibbles)
            return

        if len(nibbles) > 24:
            pass
#            print "!invalid nibbles length: ", len(nibbles)
            #return
        else:
            pass
#        	print "nibbles len=", len(nibbles)

        if nibbles[0] != 10:
#            print "!syncrobyte ", hex(nibbles[0]), " does not match 0xa"
            return

        sensor_type = ((nibbles[1] << 12)+(nibbles[2] << 8)+(nibbles[3] << 4) + nibbles[4])
        channel = nibbles[5]
        rolling_code = (nibbles[7] << 4) + nibbles[6]
        status = nibbles[8]

#        print "sensor type: ", hex(sensor_type)[2:], "code: ", hex(rolling_code)[2:], " channel: ", str(channel), "status: ", hex(status)[2:]

        if (sensor_type in self.SENSOR_BLOCKTYPE) :
            bt = self.SENSOR_BLOCKTYPE.get(sensor_type)
            bl = self.BLOCK_LEN.get(bt)
        else:
            bt = self.BLOCKTYPE_UNKN;
            bl = 0
            kw['error'] = "Unknown sensor type " + hex(sensor_type)[2:] + "! ";

        if (bl != 0) and (bl + 3 < len(nibbles)):
#            print "fix message len ", len(nibbles), " to ", bl
            del nibbles[bl + 3:]

        expected_checksum = sum(nibbles[:-4]) - 0xA
        checksum = nibbles[-3] * 16 + nibbles[-4]

        #~ print checksum, expected_checksum
        if checksum != expected_checksum:
		#   print "!invalid checksum: ", hex(checksum)[2:], " expected: ", hex(expected_checksum)[2:]
            return
        else:
#             print "checksum matched: ", hex(checksum)[2:]
            pass

        #~ crc_buffer = [((h<<4) + l)  for (l, h) in utils.batch_gen(nibbles[:-4], 2)]
        #~ expected_crc = oregon_crc8(crc_buffer)
        #~ crc = nibbles[-1] * 16 + nibbles[-2]
        #~ print [hex(x) for x in crc_buffer]#~
        #~ print hex(expected_crc), hex(crc)

        #
        #!!! if sensor_type == 1d20 or 1d30 => only 3 channels (bitcoded) change channel 4 to channel 3
        #


        kw['raw'] = raw
        kw['channel'] = str(channel)
        kw['type'] = hex(sensor_type)[2:]
        kw['code'] = hex(rolling_code)[2:]
        kw['lowbat'] = str(1 if (status & 0b0100) else 0)
        kw['forced'] = str(1 if (status & 0b1000) else 0)

        if bt == self.BLOCKTYPE_T:
            self.decode_temp(nibbles, 9, kw)
        elif bt == self.BLOCKTYPE_TH:
            self.decode_temp(nibbles, 9, kw)
            self.decode_humidity(nibbles, 13, kw)
        elif bt == self.BLOCKTYPE_UV:
            self.decode_UV(nibbles, 9, kw)
        elif bt == self.BLOCKTYPE_UV2:
            self.decode_UV(nibbles, 12, kw)
        elif bt == self.BLOCKTYPE_W:
            self.decode_wind(nibbles, 9, kw)
        elif bt == self.BLOCKTYPE_R:
            self.decode_rain(nibbles, 9, kw)
        elif bt == self.BLOCKTYPE_R2:
            self.decode_rain2(nibbles, 9, kw)
        elif bt == self.BLOCKTYPE_THB:
            self.decode_temp(nibbles, 9, kw)
            self.decode_humidity(nibbles, 13, kw)
        else:
             kw['UNKN'] = 'Ok'

        return kw



class OregonV2ProtocolHandler(OregonV2V3ProtocolDecoder, protocols.BaseRCProtocolHandler):
    name = "oregon"

    def tryDecode(self, data):
        """ Oregon v2 protocol
        """
#    	print "Oregon2 decoding:", data

        bitstream = utils.get_bits(data)
        #~ print "before strip tail", bitstream
        #~ bitstream = utils.strip_tail(bitstream, ignore_bits=3)
        bitstream = utils.strip_to_pause(bitstream, zero_bits = 8 * 3)

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
#    	print "Oregon3 decoding:", data
        bitstream = utils.get_bits(data)
        #~ print "before strip tail", bitstream
        bitstream = utils.strip_tail(bitstream, ignore_bits=3)
        bitstream = utils.strip_preamble(bitstream)

        slips, packet = utils.manchester_decode_ext(bitstream)
#        print "slips, packet:", slips, packet

        return self.decode_packet(packet)




