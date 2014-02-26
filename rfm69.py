
import time
import WB_IO.GPIO as GPIO
import WB_IO.SPI as spidev

from registers import *


CSMA_LIMIT          = -90 # upper RX signal sensitivity threshold in dBm for carrier sense access
RF69_MODE_SLEEP     =  0# XTAL OFF
RF69_MODE_STANDBY  =   1 # XTAL ON
RF69_MODE_SYNTH	  =    2 # PLL ON
RF69_MODE_RX     =     3 # RX MODE
RF69_MODE_TX	=	      4 # TX MODE


from threading import Event

class RFM69(object):
	#~ _powerLevel = 31
	#~ _powerLevel = 60
	_powerLevel = 32

	def __init__(self, spi_major = 0, spi_minor = 5, spi_speed = 200000, irq_gpio = 36):
		self._mode = None

		self.__payloadlen = 0


		self.spi = spidev.SPI()
		self.spi.open(spi_major, spi_minor)
		self.spi.msh = spi_speed

		self.irq_gpio = irq_gpio
		GPIO.setup(self.irq_gpio, GPIO.IN)

		self.data_event = Event()

	def setStandby(self):
		self.setMode(RF69_MODE_STANDBY);
		while ((self.readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_MODEREADY) == 0x00):
			pass # Wait for ModeReady


	def start(self):
		while 1:
			self.writeReg(REG_SYNCVALUE1, 0xaa)
			val = self.readReg(REG_SYNCVALUE1)
			if val == 0xaa:
				break

		self.config()
		self.setStandby()
		print "ModeReady"

		self.setInterruptHandler()


	def readReg(self, addr):
		return self.spi.write_then_read([addr & 0x7F], 1)[0] #	# send address + r/w bit


	def writeReg(self, addr, value):
		self.spi.write_then_read([addr | 0x80, value], 0)


	def readAllRegs(self):
		for regAddr in xrange(1, 0x4F + 1):
			regVal = self.readReg(regAddr)

			print "reg 0x%x = 0x%x = %s" % (regAddr, regVal, regVal)

	def setMode(self, newMode):
		#~ if (newMode == _mode) return; //TODO: can remove this?

		if newMode == RF69_MODE_TX:
			self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_TRANSMITTER)
			#~ if (_isRFM69HW) setHighPowerRegs(true);
		elif newMode == RF69_MODE_RX:
			self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_RECEIVER);
			#~ if (_isRFM69HW) setHighPowerRegs(false);
		elif newMode == RF69_MODE_SYNTH:
			self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_SYNTHESIZER)
		elif newMode == RF69_MODE_STANDBY:
			self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_STANDBY)
		elif newMode == RF69_MODE_SLEEP:
			self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_SLEEP)

		# // we are using packet mode, so this check is not really needed
	  #// but waiting for mode ready is necessary when going from sleep because the FIFO may not be immediately available from previous mode
		while ((self._mode == RF69_MODE_SLEEP) and (self.readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_MODEREADY) == 0x00):
			pass  # // Wait for ModeReady

		self._mode = newMode


	def readRSSI(self, forceTrigger=False):
	  rssi = 0
	  if (forceTrigger):
		#RSSI trigger not needed if DAGC is in continuous mode
	    self.writeReg(REG_RSSICONFIG, RF_RSSI_START)
	    while ((self.readReg(REG_RSSICONFIG) & RF_RSSI_DONE) == 0x00):
			pass # Wait for RSSI_Ready


	  rssi = -self.readReg(REG_RSSIVALUE)
	  rssi >>= 1
	  return rssi

	def interruptHandler(self, x):
		if (self._mode == RF69_MODE_RX and (self.readReg(REG_IRQFLAGS2) & RF_IRQFLAGS2_PAYLOADREADY)):
			self.setMode(RF69_MODE_STANDBY);
			self._data = self.spi.write_then_read([REG_FIFO & 0x7f], self.payload_length);
			self._datalen = self.payload_length;
			self.__payloadlen = self.payload_length;

			self.data_event.set()

			self.setMode(RF69_MODE_RX)

			#~ print self._data


		self._rssi = self.readRSSI()
		#~ print self._rssi
		#~ print ("interrupt!");



	def setBitrate(self, bitrate):
		self.bitrate = bitrate
		reg_val = int(32000000. / bitrate)
		self.writeReg( REG_BITRATEMSB, reg_val >> 8)
		self.writeReg( REG_BITRATELSB, reg_val & 0xff)

	def setPayloadLength(self, length):
		self.payload_length = length
		self.writeReg( REG_PAYLOADLENGTH, length ) #in variable length mode: the max frame size, not used in TX

	def receiveBegin(self):
		self.__payloadlen = 0


		RSSI = 0;
		if (self.readReg(REG_IRQFLAGS2) & RF_IRQFLAGS2_PAYLOADREADY):
			self.writeReg(REG_PACKETCONFIG2, (self.readReg(REG_PACKETCONFIG2) & 0xFB) | RF_PACKET2_RXRESTART)#; // avoid RX deadlocks
		self.writeReg(REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_01) # ; //set DIO0 to "PAYLOADREADY" in receive mode
		self.setMode(RF69_MODE_RX);
		self.setInterruptHandler()


	def getDataBlocking(self, timeout=None):
		self.data_event.clear()
		self.receiveBegin()

		if timeout is None:
			timeout = 1E100
		self.data_event.wait(timeout)
		data = self.receiveDone()
		return data




	def receiveDone(self):
	  #~ noInterrupts(); //re-enabled in unselect() via setMode()
		if (self._mode == RF69_MODE_RX and self.__payloadlen > 0):
			self.setMode(RF69_MODE_STANDBY)
			return self._data

		self.receiveBegin()
		return None


	def send(self, payload):
		self.writeReg(REG_PACKETCONFIG2, (self.readReg(REG_PACKETCONFIG2) & 0xFB) | RF_PACKET2_RXRESTART) #; // avoid RX deadlocks
		while (not self.canSend()):
			self.receiveDone()

		self.sendFrame(payload)

	def sendFrame(self, payload):
		self.unsetInterruptHandler()

		self.setMode(RF69_MODE_STANDBY)#; //turn off receiver to prevent reception while filling fifo
		while ((self.readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_MODEREADY) == 0x00):
			pass # // Wait for ModeReady
		self.writeReg(REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_00) #; // DIO0 is "Packet Sent"

		#~ bufferSize = len(payload)
		self.spi.write_then_read([REG_FIFO | 0x80, len(payload)] + payload, 0);


	#	/* no need to wait for transmit mode to be ready since its handled by the radio */
		self.setMode(RF69_MODE_TX);


		GPIO.wait_for_edge(self.irq_gpio, GPIO.RISING)
		print GPIO.input(self.irq_gpio)

		self.setStandby()

	def canSend(self):
		return True
		print self.readRSSI(), CSMA_LIMIT
		if (self._mode == RF69_MODE_RX and self.__payloadlen == 0 and self.readRSSI() < CSMA_LIMIT):# //if signal stronger than -100dBm is detected assume channel activity
			self.setMode(RF69_MODE_STANDBY)
			return True

		return False

	def setInterruptHandler(self):
		self.unsetInterruptHandler()
		GPIO.add_event_detect(self.irq_gpio, GPIO.RISING, callback=self.interruptHandler)

	def unsetInterruptHandler(self):
		GPIO.remove_event_detect(self.irq_gpio)

	def setHighPower(self, onOff):
		self._isRFM69HW = onOff;
		#~ writeReg(REG_OCP, RF_OCP_OFF if _isRFM69HW else RF_OCP_ON)
		self.writeReg(REG_OCP, RF_OCP_ON | RF_OCP_TRIM_50)
		if (self._isRFM69HW):
			# //turning ON
			self.writeReg(REG_PALEVEL, (self.readReg(REG_PALEVEL) & 0x1F) | RF_PALEVEL_PA1_ON | RF_PALEVEL_PA2_ON) # ; //enable P1 & P2 amplifier stages
		else:
			self.writeReg(REG_PALEVEL, RF_PALEVEL_PA0_ON | RF_PALEVEL_PA1_OFF | RF_PALEVEL_PA2_OFF | self._powerLevel)#; //enable P0 only


	def config(self):
		self.writeReg( REG_OPMODE, RF_OPMODE_SEQUENCER_ON | RF_OPMODE_LISTEN_OFF | RF_OPMODE_STANDBY )
		self.writeReg( REG_DATAMODUL, RF_DATAMODUL_DATAMODE_PACKET | RF_DATAMODUL_MODULATIONTYPE_OOK | RF_DATAMODUL_MODULATIONSHAPING_00 ) #no shaping

		self.writeReg( REG_FDEVMSB, RF_FDEVMSB_5000) #default:5khz, (FDEV + BitRate/2 <= 500Khz)
		self.writeReg( REG_FDEVLSB, RF_FDEVLSB_5000)
		self.writeReg( REG_FRFMSB, 0x6c)
		self.writeReg( REG_FRFMID, 0x7a)
		self.writeReg( REG_FRFLSB, 0xe1)
		self.writeReg( REG_RXBW, RF_RXBW_DCCFREQ_111 | RF_RXBW_MANT_16 | RF_RXBW_EXP_0 ) #(BitRate < 2 * RxBw)
		self.writeReg( REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_01 | RF_DIOMAPPING1_DIO2_01 ) #DIO0 is the only IRQ we're using
		self.writeReg( REG_DIOMAPPING2, RF_DIOMAPPING2_DIO5_01 | RF_DIOMAPPING2_DIO4_10)
		self.writeReg( REG_RSSITHRESH, 140 ) #must be set to dBm = (-Sensitivity / 2) - default is 0xE4=228 so -114dBm
		#~ self.writeReg( REG_RSSITHRESH, 220 ) #must be set to dBm = (-Sensitivity / 2) - default is 0xE4=228 so -114dBm


		self.writeReg( REG_PREAMBLELSB, 5 ) # default 3 preamble bytes 0xAAAAAA
		self.writeReg( REG_SYNCCONFIG, RF_SYNC_ON | RF_SYNC_SIZE_1 | RF_SYNC_TOL_7 )

		self.writeReg( REG_SYNCVALUE1, 0xaa )      #attempt to make this compatible with sync1 byte of RFM12B lib

		#~  0x2f  self.writeReg( REG_SYNCVALUE1, 0xaa )      #attempt to make this compatible with sync1 byte of RFM12B lib
		#~  0x2f  self.writeReg( REG_SYNCVALUE2, 0xaa )
		#~  0x2f  self.writeReg( REG_SYNCVALUE3, 0xaa )
		#~  0x2f  self.writeReg( REG_SYNCVALUE4, 0xaa )
		#~  0x2f  self.writeReg( REG_SYNCVALUE5, 0xaa )
		#~  0x2f  self.writeReg( REG_SYNCVALUE6, 0xaa )
		#~  0x2f  self.writeReg( REG_SYNCVALUE7, 0xaa )
		#~  0x2f  self.writeReg( REG_SYNCVALUE8, 0xaa )
		self.writeReg( REG_PACKETCONFIG1, RF_PACKET1_FORMAT_FIXED | RF_PACKET1_DCFREE_OFF | RF_PACKET1_CRC_OFF | RF_PACKET1_CRCAUTOCLEAR_ON | RF_PACKET1_ADRSFILTERING_OFF )
		self.writeReg( REG_FIFOTHRESH, RF_FIFOTHRESH_TXSTART_FIFONOTEMPTY | RF_FIFOTHRESH_VALUE ) #TX on FIFO not empty
		self.writeReg( REG_PACKETCONFIG2, RF_PACKET2_RXRESTARTDELAY_NONE | RF_PACKET2_AUTORXRESTART_ON | RF_PACKET2_AES_OFF ) #RXRESTARTDELAY must match transmitter PA ramp-down time (bitrate dependent)
		self.writeReg( REG_TESTDAGC, RF_DAGC_IMPROVED_LOWBETA0 ) # # TODO: Should use LOWBETA_ON, but having trouble getting it working
		self.writeReg( REG_TESTAFC, 0 ) # AFC Offset for low mod index systems


		self.setPayloadLength(60)
		self.setBitrate(2000)




