import sys
import time

from registers import *
import rfm69

from functools import wraps
import errno
import os
import signal
import ctypes



if len(sys.argv) > 2:
    spi_minor = int(sys.argv[1])
    irq_gpio = int(sys.argv[2])
        # 7 55
else:
    spi_minor = 5
    irq_gpio = 36

radio = rfm69.RFM69(spi_minor=spi_minor,irq_gpio=irq_gpio)

radio.setMode(rfm69.RF69_MODE_STANDBY)

radio.writeReg( REG_OPMODE, RF_OPMODE_SEQUENCER_ON | RF_OPMODE_LISTEN_OFF | RF_OPMODE_STANDBY )
radio.writeReg( REG_DATAMODUL, RF_DATAMODUL_DATAMODE_CONTINUOUSNOBSYNC | RF_DATAMODUL_MODULATIONTYPE_OOK | RF_DATAMODUL_MODULATIONSHAPING_00 ) #no shaping
#~ radio.writeReg( REG_DATAMODUL, RF_DATAMODUL_DATAMODE_CONTINUOUS | RF_DATAMODUL_MODULATIONTYPE_OOK | RF_DATAMODUL_MODULATIONSHAPING_00 ) #no shaping



radio.writeReg( REG_FDEVMSB, RF_FDEVMSB_5000) #default:5khz, (FDEV + BitRate/2 <= 500Khz)
radio.writeReg( REG_FDEVLSB, RF_FDEVLSB_5000)

radio.setCarrier(433.92)
#~ radio.setCarrier(433.0)
#~ radio.setCarrier(315)

#~ radio.writeReg( REG_RXBW, RF_RXBW_DCCFREQ_001 | RF_RXBW_MANT_16 | RF_RXBW_EXP_0 ) #(BitRate < 2 * RxBw)
radio.writeReg( REG_RXBW, RF_RXBW_DCCFREQ_100 | RF_RXBW_MANT_16 | RF_RXBW_EXP_0 ) #(BitRate < 2 * RxBw)

#~ radio.writeReg( REG_LNA, RF_LNA_GAINSELECT_MAXMINUS6)

radio.writeReg( REG_OOKPEAK, RF_OOKPEAK_THRESHTYPE_PEAK)




radio.writeReg( REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_01 | RF_DIOMAPPING1_DIO2_01 ) #DIO0 is the only IRQ we're using
radio.writeReg( REG_DIOMAPPING2, RF_DIOMAPPING2_DIO5_01 | RF_DIOMAPPING2_DIO4_10)


radio.writeReg( REG_PREAMBLELSB, 5 ) # default 3 preamble bytes 0xAAAAAA
#~ radio.writeReg( REG_SYNCCONFIG, RF_SYNC_ON | RF_SYNC_SIZE_1 | RF_SYNC_TOL_7 )
radio.writeReg( REG_SYNCCONFIG, RF_SYNC_OFF)

radio.writeReg( REG_SYNCVALUE1, 0xaa )
radio.writeReg( REG_SYNCVALUE2, 0x66 )
#~
#~  0x2f  radio.writeReg( REG_SYNCVALUE1, 0xaa )      #attempt to make this compatible with sync1 byte of RFM12B lib
#~  0x2f  radio.writeReg( REG_SYNCVALUE2, 0xaa )
#~  0x2f  radio.writeReg( REG_SYNCVALUE3, 0xaa )
#~  0x2f  radio.writeReg( REG_SYNCVALUE4, 0xaa )
#~  0x2f  radio.writeReg( REG_SYNCVALUE5, 0xaa )
#~  0x2f  radio.writeReg( REG_SYNCVALUE6, 0xaa )
#~  0x2f  radio.writeReg( REG_SYNCVALUE7, 0xaa )
#~  0x2f  radio.writeReg( REG_SYNCVALUE8, 0xaa )
radio.writeReg( REG_PACKETCONFIG1, RF_PACKET1_FORMAT_FIXED | RF_PACKET1_DCFREE_OFF | RF_PACKET1_CRC_OFF | RF_PACKET1_CRCAUTOCLEAR_ON | RF_PACKET1_ADRSFILTERING_OFF )
radio.writeReg( REG_FIFOTHRESH, RF_FIFOTHRESH_TXSTART_FIFONOTEMPTY | RF_FIFOTHRESH_VALUE ) #TX on FIFO not empty
radio.writeReg( REG_PACKETCONFIG2, RF_PACKET2_RXRESTARTDELAY_NONE | RF_PACKET2_AUTORXRESTART_ON | RF_PACKET2_AES_OFF ) #RXRESTARTDELAY must match transmitter PA ramp-down time (bitrate dependent)
radio.writeReg( REG_TESTDAGC, RF_DAGC_IMPROVED_LOWBETA0 ) # # TODO: Should use LOWBETA_ON, but having trouble getting it working
radio.writeReg( REG_TESTAFC, 0 ) # AFC Offset for low mod index systems


radio.writeReg( REG_OOKFIX, 20)


radio.setPayloadLength(60)
radio.setBitrate(2000)
radio.setHighPower(0)
radio.setRSSIThreshold(-70)
radio.setMode(rfm69.RF69_MODE_RX)
print "opmode=", radio.readReg(REG_OPMODE)


from lirc_mode2 import LIRCMode2
import noolite, utils, oregon
lirc = LIRCMode2('/dev/lirc0')
width = 500

while True:
    radio.setMode(rfm69.RF69_MODE_RX)
    packet = lirc.read_packet()
    print "Rssi=", radio.readRSSI()
    #~ radio.setMode(rfm69.RF69_MODE_STANDBY)
    #~ print "packet=", len(packet), packet

    bitstream = []
    for duration, is_pulse in packet:
        bits = int(round(duration * 1.0 / width))
        bit = '0' if not is_pulse else '1'
        for _ in xrange(bits):
            bitstream.append(bit)

    bitstream = "".join(bitstream)
    #~ print "".join(bitstream)
    #~ print bitstream

    print noolite.NooliteProtocolHandler().tryDecode(utils.get_bytes(bitstream))
    print noolite.NooliteProtocolHandler().tryDecode(utils.get_bytes(utils.invert(bitstream)))
    #~ print oregon.OregonV2ProtocolHandler().tryDecode(utils.get_bytes(bitstream))

    time.sleep(0.01)
