
import time
#~ import WB_IO.GPIO as _GPIO

from gpio import GPIO
import WB_IO.SPI as spidev

from registers import *

import threading
#~ class _GPIOWrap(object):
	#~ IN = _GPIO.IN
	#~ OUT = _GPIO.OUT
	#~ RISING = _GPIO.RISING
	#~ RISING = _GPIO.RISING
	#~ def __init__(self):
		#~ self.lock = threading.Lock()
	#~ def _proxy(self, method, *args, **kwargs):
		#~ with self.lock:
			#~ # print "proxy ", method, args, kwargs
			#~ return getattr(_GPIO, method)(*args, **kwargs)
#~
	#~ def setup(self, *args, **kwargs):
		#~ return self._proxy("setup", *args, **kwargs)
	#~ def input(self, *args, **kwargs):
		#~ return self._proxy("input", *args, **kwargs)
#~
	#~ def add_event_detect(self, *args, **kwargs):
		#~ return self._proxy("add_event_detect", *args, **kwargs)
	#~ def wait_for_edge(self, *args, **kwargs):
		#~ return self._proxy("wait_for_edge", *args, **kwargs)
	#~ def remove_event_detect(self, *args, **kwargs):
		#~ return self._proxy("remove_event_detect", *args, **kwargs)


class DummyLock(object):
    def __init__(self):
        pass
    def __enter__(self):
        print "enter"
    def __exit__(self, type, value, traceback):
        print "exit"

#~ GPIO = _GPIOWrap()

CSMA_LIMIT          = -90 # upper RX signal sensitivity threshold in dBm for carrier sense access
RF69_MODE_SLEEP     =  0# XTAL OFF
RF69_MODE_STANDBY  =   1 # XTAL ON
RF69_MODE_SYNTH	  =    2 # PLL ON
RF69_MODE_RX     =     3 # RX MODE
RF69_MODE_TX	=	      4 # TX MODE


COURSE_TEMP_COEF = 165 # puts the temperature reading in the ballpark, user can fine tune the returned value

from threading import Event

class RFM69(object):
	#~ _powerLevel = 31
	#~ _powerLevel = 60
	_powerLevel = 31

	def __init__(self, spi_major = 0, spi_minor = 5, spi_speed = 500000, irq_gpio = 36):
		self._mode = None

		self.__payloadlen = 0


		self.spi = spidev.SPI()
		self.spi.open(spi_major, spi_minor)
		self.spi.msh = spi_speed

		self.irq_gpio = irq_gpio
		GPIO.setup(self.irq_gpio, GPIO.IN)

		self.data_event = Event()

		self.lock = threading.RLock()



		#~ self.lock = DummyLock()

	def setStandby(self):
		self.setMode(RF69_MODE_STANDBY);
		while ((self.readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_MODEREADY) == 0x00):
			pass # Wait for ModeReady


	def start(self):
		with self.lock:
			for i in xrange(100):
				self.writeReg(REG_SYNCVALUE1, 0xaa)
				val = self.readReg(REG_SYNCVALUE1)
				if val == 0xaa:
					break
				time.sleep(0.02)
			else:
				raise RuntimeError("RFM69 does not respond")

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

	def setHighPowerRegs(self, onOff):
		self.writeReg(REG_TESTPA1, 0x5D if onOff  else  0x55)
		self.writeReg(REG_TESTPA2, 0x7C if onOff else 0x70)


	def setMode(self, newMode):
		with self.lock:
			#~ if (newMode == _mode) return; //TODO: can remove this?

			if newMode == RF69_MODE_TX:
				self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_TRANSMITTER)
				if self._isRFM69HW:
					self.setHighPowerRegs(True)
			elif newMode == RF69_MODE_RX:
				self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_RECEIVER);
				if self._isRFM69HW:
					 self.setHighPowerRegs(False)
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
		#~ except:
			#~ import traceback; traceback.print_exc()
			#~ raise


	def readRSSI(self, forceTrigger=False):
		with self.lock:
			rssi = 0
			if (forceTrigger):
				#RSSI trigger not needed if DAGC is in continuous mode
				self.writeReg(REG_RSSICONFIG, RF_RSSI_START)
				while ((self.readReg(REG_RSSICONFIG) & RF_RSSI_DONE) == 0x00):
					pass # Wait for RSSI_Ready


			rssi = -self.readReg(REG_RSSIVALUE)
			rssi >>= 1
			#~ print "rssi: ", rssi


			#~ print "gain: " ,self.readReg(REG_LNA) & RF_LNA_CURRENTGAIN

			return rssi


	def is_noise(self, data):
		rolling_counter = 0
		for c in data:
			if c == 0xFF:
				rolling_counter = 0
			else:
				rolling_counter += 1

			if rolling_counter >= 20:
				return False

		return True



	def interruptHandler(self, x):
			#~ return
		#~ try:
			print ("interrupt!");
			if (self._mode == RF69_MODE_RX and (self.readReg(REG_IRQFLAGS2) & RF_IRQFLAGS2_PAYLOADREADY)):
				self.setMode(RF69_MODE_STANDBY);
				self._data = self.spi.write_then_read([REG_FIFO & 0x7f], self.payload_length);
				self._datalen = self.payload_length;
				self.__payloadlen = self.payload_length;


				if not self.is_noise(self._data):
						self.data_event.set()

				self.setMode(RF69_MODE_RX)

				#~ print self._data


			self._rssi = self.readRSSI()
			#~ print self._rssi
		#~ except:
			#~ import traceback
			#~ traceback.print_exc()
			#~ raise



	def setBitrate(self, bitrate):
		self.bitrate = bitrate
		reg_val = int(32000000. / bitrate)
		self.writeReg( REG_BITRATEMSB, reg_val >> 8)
		self.writeReg( REG_BITRATELSB, reg_val & 0xff)

	def setPayloadLength(self, length):
		self.payload_length = length
		self.writeReg( REG_PAYLOADLENGTH, length ) #in variable length mode: the max frame size, not used in TX

	def receiveBegin(self):
		#~ print "receive begin"
		with self.lock:
			#~ print "receive begin inside lock"
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
		with self.lock:
		  #~ noInterrupts(); //re-enabled in unselect() via setMode()
			if (self._mode == RF69_MODE_RX and self.__payloadlen > 0):
				self.setMode(RF69_MODE_STANDBY)
				return self._data

			self.receiveBegin()
			return None


	def send(self, payload):
		with self.lock:
			self.writeReg(REG_PACKETCONFIG2, (self.readReg(REG_PACKETCONFIG2) & 0xFB) | RF_PACKET2_RXRESTART) #; // avoid RX deadlocks
			while (not self.canSend()):
				self.receiveDone()

			self.sendFrame(payload)

	def sendFrame(self, payload):
		with self.lock:
			self.unsetInterruptHandler()

			self.setMode(RF69_MODE_STANDBY)#; //turn off receiver to prevent reception while filling fifo
			while ((self.readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_MODEREADY) == 0x00):
				print "not ready"
				pass # // Wait for ModeReady
			self.writeReg(REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_00) #; // DIO0 is "Packet Sent"

			#~ bufferSize = len(payload)
			self.spi.write_then_read([REG_FIFO | 0x80, len(payload)] + payload, 0);


		#	/* no need to wait for transmit mode to be ready since its handled by the radio */
			self.setMode(RF69_MODE_TX);

			#~ print "sendFrame: waiting for irq"
			status = GPIO.wait_for_edge(self.irq_gpio, GPIO.RISING, timeout = 0.6)
			if status:
				#~ print "sendFrame: got irq RISING edge"
				pass
			else:
				print "error: no irq detected. going back to standby mode"

			self.setStandby()

	def canSend(self):
		return True
		print self.readRSSI(), CSMA_LIMIT
		if (self._mode == RF69_MODE_RX and self.__payloadlen == 0 and self.readRSSI() < CSMA_LIMIT):# //if signal stronger than -100dBm is detected assume channel activity
			self.setMode(RF69_MODE_STANDBY)
			return True

		return False

	def setInterruptHandler(self):
		#~ return
		with self.lock:
			self.unsetInterruptHandler()
			GPIO.add_event_detect(self.irq_gpio, GPIO.RISING, callback=self.interruptHandler)

	def unsetInterruptHandler(self):
		#~ return
		with self.lock:
			GPIO.remove_event_detect(self.irq_gpio)

	def setHighPower(self, onOff):
		self._isRFM69HW = onOff
		self.writeReg(REG_OCP, RF_OCP_OFF if self._isRFM69HW else RF_OCP_ON)
		#~ self.writeReg(REG_OCP, RF_OCP_ON | RF_OCP_TRIM_50)
		if (self._isRFM69HW):
			# //turning ON
			self.writeReg(REG_PALEVEL, (self.readReg(REG_PALEVEL) & 0x1F) | RF_PALEVEL_PA1_ON | RF_PALEVEL_PA2_ON) # ; //enable P1 & P2 amplifier stages
		else:
			#~ self.writeReg(REG_PALEVEL, RF_PALEVEL_PA0_ON | RF_PALEVEL_PA1_OFF | RF_PALEVEL_PA2_OFF | self._powerLevel)#; //enable P0 only
			self.writeReg(REG_PALEVEL, RF_PALEVEL_PA0_ON | RF_PALEVEL_PA1_ON | RF_PALEVEL_PA2_ON | self._powerLevel)#; //enable P0 only


	def setPowerLevel(self, powerLevel):
		self._powerLevel = powerLevel
		self.writeReg(REG_PALEVEL, (self.readReg(REG_PALEVEL) & 0xE0) | (31 if self._powerLevel > 31 else  self._powerLevel))


	def setCarrier(self, freq):
		frf = int(freq / (32./2**19))
		frf_msb = frf >> 16
		frf_mid = (frf >> 8) & 0x00ff
		frf_lsb = frf & 0x00ff

		print hex(frf_msb)
		print hex(frf_mid)
		print hex(frf_lsb)

		self.writeReg( REG_FRFMSB, frf_msb)
		self.writeReg( REG_FRFMID, frf_mid)
		self.writeReg( REG_FRFLSB, frf_lsb)

		self.carrier = freq


	def setRSSIThreshold(self, threshold_dbm):
		""" must be set to dBm = (-Sensitivity / 2) - default is 0xE4=228 so -114dBm """
		sensitivity = -threshold_dbm * 2
		assert 0 <= sensitivity <= 0xFF
		self.writeReg( REG_RSSITHRESH, sensitivity)


	def readTemperature(self, cal_factor):
		"""returns centigrade"""

		self.setMode(RF69_MODE_STANDBY)
		self.writeReg(REG_TEMP1, RF_TEMP1_MEAS_START);
		while ((self.readReg(REG_TEMP1) & RF_TEMP1_MEAS_RUNNING)):
			print '*'

		return ~self.readReg(REG_TEMP2) + COURSE_TEMP_COEF + cal_factor # 'complement'corrects the slope, rising temp = rising val
		#COURSE_TEMP_COEF puts reading in the ballpark, user can add additional correction

	def setDataMode(self, packet=True, bitsync=True):
		if packet:
			datamode = RF_DATAMODUL_DATAMODE_PACKET
		else:
			if bitsync:
				datamode = RF_DATAMODUL_DATAMODE_CONTINUOUS
			else:
				datamode = RF_DATAMODUL_DATAMODE_CONTINUOUSNOBSYNC


		self.writeReg( REG_DATAMODUL, datamode | RF_DATAMODUL_MODULATIONTYPE_OOK | RF_DATAMODUL_MODULATIONSHAPING_00 ) #no shaping

	def setNoiseThreshold(self, threshold):
		""" set noise threshold floor (in dBm) """
		if not (0 <= threshold <= 0xFF):
			raise RuntimeError("wrong threshold value %s", threshold)

		self.writeReg(REG_OOKFIX, 20)



	def config(self):
		self.writeReg( REG_OPMODE, RF_OPMODE_SEQUENCER_ON | RF_OPMODE_LISTEN_OFF | RF_OPMODE_STANDBY )

		self.setDataMode(packet=True)

		self.writeReg( REG_FDEVMSB, RF_FDEVMSB_5000) #default:5khz, (FDEV + BitRate/2 <= 500Khz)
		self.writeReg( REG_FDEVLSB, RF_FDEVLSB_5000)

		self.setCarrier(433.92)

		#~ self.writeReg( REG_RXBW, RF_RXBW_DCCFREQ_001 | RF_RXBW_MANT_16 | RF_RXBW_EXP_0 ) #(BitRate < 2 * RxBw)
		self.writeReg( REG_RXBW, RF_RXBW_DCCFREQ_100 | RF_RXBW_MANT_16 | RF_RXBW_EXP_0 ) #(BitRate < 2 * RxBw)

		#~ self.writeReg( REG_LNA, RF_LNA_GAINSELECT_MAXMINUS6)

		self.writeReg( REG_OOKPEAK, RF_OOKPEAK_THRESHTYPE_PEAK)

		self.writeReg( REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_01 | RF_DIOMAPPING1_DIO2_01 ) #DIO0 is the only IRQ we're using
		self.writeReg( REG_DIOMAPPING2, RF_DIOMAPPING2_DIO5_01 | RF_DIOMAPPING2_DIO4_10)

		self.setRSSIThreshold(-85)


		self.writeReg( REG_PREAMBLELSB, 5 ) # default 3 preamble bytes 0xAAAAAA
		#~ self.writeReg( REG_SYNCCONFIG, RF_SYNC_ON | RF_SYNC_SIZE_1 | RF_SYNC_TOL_7 )
		self.writeReg( REG_SYNCCONFIG, RF_SYNC_ON | RF_SYNC_SIZE_2 | RF_SYNC_TOL_5 )

		self.writeReg( REG_SYNCVALUE1, 0xaa )
		self.writeReg( REG_SYNCVALUE2, 0x66 )
#~
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




