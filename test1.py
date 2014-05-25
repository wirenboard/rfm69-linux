import sys
import time

from registers import *
import rfm69

from functools import wraps
import errno
import os
import signal

class TimeoutError(Exception):
    pass

class Timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
    def __exit__(self, type, value, traceback):
        signal.alarm(0)


if len(sys.argv) > 2:
	spi_minor = int(sys.argv[1])
	irq_gpio = int(sys.argv[2])
	# 7 55
else:
	spi_minor = 5
	irq_gpio = 36


with Timeout(seconds=10):
	radio = rfm69.RFM69(spi_minor=spi_minor,irq_gpio=irq_gpio)

	radio.start()
	#~ radio.setHighPower(True)
	radio.setHighPower(False)
	radio.receiveBegin()

	sys.exit(0)
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
