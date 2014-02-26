
import time

from registers import *
import rfm69


radio = rfm69.RFM69()
radio.start()


#~ radio.setHighPower(True)
radio.setHighPower(False)
radio.receiveBegin()

#~
#~ while 1:
	#~ data = radio.receiveDone()
	#~

while 1:
	raw_input(">>")
	#~ send([170, 170, 170, 170, 170, 170, 170, 133, 154, 105, 150, 166, 169, 170, 170, 90, 102, 11, 52, 211, 45, 77, 83, 85, 84, 180, 204, 0, 0, 0, 0, 0, 0, 63, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255])

	#~ setMode(RF69_MODE_STANDBY)
	time.sleep(0.1)


	radio.send([134, 170, 105, 150, 166, 169, 170, 170, 85, 90, 13, 84, 211, 45, 77, 83, 85, 84, 170, 180, 0, 0, 0, 0, 0, 0, 7,])
	radio.receiveBegin()

	#~ while 1:
		#~ receiveDone(
