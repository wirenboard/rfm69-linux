#!/usr/bin/python
import sys
import time
import socket
import threading
import Queue
import os

from collections import deque
from weakref import WeakValueDictionary
import binascii

import mosquitto

import rfm69
import random

radio_send_queue = Queue.Queue()
clients_send_queue = Queue.Queue()

client_handlers = WeakValueDictionary()



radio = None



from protocols import RawProtocolHandler
from noolite import NooliteProtocolHandler
from oregon import OregonV2ProtocolHandler

protocol_handlers = [RawProtocolHandler(), NooliteProtocolHandler(), OregonV2ProtocolHandler()]



def radio_sender():
    while True:
        data = radio_send_queue.get()

        try:
            #~ print "actual send"
            radio.send(data)
            #~ print "rec begin"
            radio.receiveBegin()
        except:
            import traceback;
            traceback.print_exc()
            raise


def radio_send(data):
    print "radio send"
    radio_send_queue.put(data)



def process_recv_radio_data(data, counter):
    time_str = str(time.time())
    for protocol in protocol_handlers:
        #~ print protocol
        decoded = protocol.tryDecode(data)
        if decoded:
            mqtt_handler.handle_recv_data(protocol, decoded)






mqtt_handler = None

from collections import defaultdict





def get_serial():
    path = '/var/lib/wirenboard/serial.conf'
    if os.path.exists(path):
        return open(path).read().strip()
    else:
        return ":".join(hex(random.randint(0,255))[2:].zfill(2) for _ in xrange(6))


import mqtt_devices
class MQTTHandler(object):
    def __init__(self):
        self.client = None
        self.mqtt_device_id = "wb-homa-rcd"
        self.counters = defaultdict(int)

        self.serial = get_serial()
        serial_parts = [int(x,16) for x in self.serial.split(':')[-2:]]
        serial_num = serial_parts[0]*16+ serial_parts[1]
        self.noolite_start_addr = serial_num % 8192

        self.settings = {}

        self.devices = []
        self.rx_devices = []


        self.rx_handlers = {}
        for handler_class in mqtt_devices.rx_handler_classes:
            handler = handler_class()
            self.rx_handlers[handler.name] = handler



    def start(self):
        self.client = mosquitto.Mosquitto(self.mqtt_device_id)
        rc = self.client.connect("127.0.0.1")
        self.client.on_message = self.on_mqtt_message

        self.client.publish("/devices/%s/meta/name" % self.mqtt_device_id, "ISM Radio", 0, True)

        # subscribe to 'meta' settings
        self.client.subscribe("/devices/%s/meta/+" % self.mqtt_device_id)


        # hack to get retained settings first:
        rand_str = str(time.time()) + str(random.randint(0,100000))
        self.random_topic = "/tmp/%s/%s" % ( self.mqtt_device_id, rand_str)
        self.client.subscribe(self.random_topic)
        self.client.publish(self.random_topic, '1')

        #~ self.client.publish("/devices/%s/controls/status" % self.mqtt_device_id, "OK", 0, True)
        #~ self.client.publish("/devices/%s/controls/status/meta/type" % self.mqtt_device_id, "text", 0, True)
        #~ self.client.will_set("/devices/%s/controls/status" % self.mqtt_device_id, "Daemon is not running", 0, True)

        self.client.loop_start()

    def on_config_received(self):
        # check meta settings correctness and set default values
        if not self.settings.get('room'):
            self.settings['room'] = 'System'
        try:
            val = self.settings.get('noolite_remotes')
            self.noolite_remotes = int(val)
        except (TypeError, ValueError):
            self.noolite_remotes = 4
            self.settings['noolite_remotes'] = str(self.noolite_remotes)

        # publish current settings
        for name, value in self.settings.iteritems():
            self.client.publish("/devices/%s/meta/%s" % (self.mqtt_device_id, name), value, 0, True)


        for i in xrange(self.noolite_remotes):
            addr = self.noolite_start_addr + i
            self.devices.append(mqtt_devices.NooliteTxDevice(addr, radio_send))



        for device in self.devices:
            self.publish_device(device)


    def publish_device(self, device):
        self.client.publish("/devices/%s/meta/name" % device.device_id, device.device_name, 0, True)
        if device.device_room:
            self.client.publish("/devices/%s/meta/room" % device.device_id, device.device_room, 0, True)
        controls = device.get_controls()

        for control, desc in controls.iteritems():
            control_prefix = "/devices/%s/controls/%s" % (device.device_id, control)
            self.client.publish(control_prefix, desc['value'], 0, True)

            for meta_key, meta_val in desc['meta'].iteritems():
                self.client.publish(control_prefix + "/meta/%s" % meta_key, meta_val, 0, True)

            if not desc.get('readonly', False):
                self.client.subscribe(control_prefix + '/on')
            #~ print "subscribed to " , control_prefix + '/on'


    def stop(self):
        self.client.loop_stop()


    def handle_recv_data(self, protocol_handler, data):
        topic = "/events/%s/protocols/%s" % (self.mqtt_device_id, protocol_handler.name)
        data_arr = ("%s=%s" % (key, value) for key, value in data.iteritems())
        msg = "\t".join(data_arr)
        self.client.publish(topic, msg, 0, False)

        # counters
        topic = "/devices/%s/controls/rx %s" % (self.mqtt_device_id, protocol_handler.name)
        if protocol_handler not in self.counters:
            self.client.publish(topic + '/meta/type', 'text', 0, True)

        self.counters[protocol_handler] += 1
        self.client.publish(topic, str(self.counters[protocol_handler]))

        # blah

        rx_handler = self.rx_handlers.get(protocol_handler.name)
        if rx_handler is not None:
            rx_device = rx_handler.get_device(data)
            if rx_device is not None:
                if rx_device not in self.rx_devices:
                    self.rx_devices.append(rx_device)
                    self.publish_device(rx_device)


                control_values = rx_device.handle_data(data)
                if control_values:

                    for control, value in control_values.iteritems():
                        control_topic = "/devices/%s/controls/%s" % (rx_device.device_id, control)
                        self.client.publish(control_topic, value, 0, True)




    def on_mqtt_message(self, mosq, obj, msg):
        #~ print "on_mqtt_message " , msg.topic
        parts = msg.topic.split('/')

        if mosquitto.topic_matches_sub('/devices/%s/meta/+' % self.mqtt_device_id, msg.topic):
            name = parts[4]
            self.settings[name] = msg.payload
        elif msg.topic == self.random_topic:
            self.on_config_received()
        elif mosquitto.topic_matches_sub('/devices/+/controls/+/on' , msg.topic):

            device_id = parts[2]
            control = parts[4]

            for device in self.devices:
                if device.device_id == device_id:
                    ret = device.update_control(control, msg.payload)
                    if ret is not None:
                        self.client.publish("/devices/%s/controls/%s" % (device_id, control), ret, 0, True)


                    break
            else:
                print "unknown device id ", device_id








if __name__ == "__main__":


    radio_sender_thread = threading.Thread(target=radio_sender)
    radio_sender_thread.daemon = True
    radio_sender_thread.start()


    if len(sys.argv) > 2:
        spi_minor = int(sys.argv[1])
        irq_gpio = int(sys.argv[2])
        # 7 55
    else:
        spi_minor = 5
        irq_gpio = 36

    radio = rfm69.RFM69(spi_minor=spi_minor,irq_gpio=irq_gpio)

    radio.setPowerLevel(31)
    #~ radio.setHighPower(True)
    radio.setHighPower(False)

    radio.start()

    radio.receiveBegin()

    mqtt_handler = MQTTHandler()
    mqtt_handler.start()
    #~ print "after handler"

    counter = 0
    while 1:
        data = radio.getDataBlocking()
        if not data:
            time.sleep(0.1)
            continue
#~ #~
        print "got data", data
#~ #~
        counter += 1
        process_recv_radio_data(data, counter)
    time.sleep(100)


    #~ print#~ print "before stop"
    mqtt_handler.stop()



    #~ server.shutdown()
