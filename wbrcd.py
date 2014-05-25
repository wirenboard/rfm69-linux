import sys
import time
import socket
import threading
import SocketServer
import Queue

from collections import deque
from weakref import WeakValueDictionary
import binascii

import rfm69

radio_send_queue = Queue.Queue()
clients_send_queue = Queue.Queue()

client_handlers = WeakValueDictionary()

class ThreadedTCPRequestHandler(SocketServer.StreamRequestHandler):

    def handle(self):
        client_id = self.client_address
        client_handlers[client_id] = self
        while True:
            line = self.rfile.readline()
            if line:
                print "put line", line
                radio_send_queue.put(line)
            else:
                break

        del client_handlers[client_id]

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True
    pass

def client(ip, port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    try:
        sock.sendall(message)
        response = sock.recv(1024)
        print "Received: {}".format(response)
    finally:
        sock.close()


def feed_clients():
    while True:
        line = clients_send_queue.get()
        print "Feed clients with ", line
        for handler in client_handlers.values():
            handler.wfile.write(line)
            handler.wfile.write("\n")
            handler.wfile.flush()


radio = None

from protocols import RawProtocolHandler
from noolite import NooliteProtocolHandler
from oregon import OregonV2ProtocolHandler

protocol_handlers = [RawProtocolHandler(), NooliteProtocolHandler(), OregonV2ProtocolHandler()]



def radio_send():
    while True:
        line = radio_send_queue.get()
        #~ print "got line", line

        parts = line.split()
        protocol_name = parts[0]

        kw = {}
        for part in parts[1:]:
            k, v = part.split('=', 1)
            kw[k] = v

        for protocol_handler in protocol_handlers:
            if protocol_handler.name == protocol_name:
                data = protocol_handler.tryEncode(kw)
                if data:
                    radio.send(data)
                    radio.receiveBegin()







def process_recv_radio_data(data, counter):
    time_str = str(time.time())
    for protocol in protocol_handlers:
        #~ print protocol
        decoded = protocol.tryDecode(data)
        if decoded:
            kw = decoded

            data_arr = [ str(counter), time_str, str(protocol.name)]

            for key, value in kw.iteritems():
                data_arr.append("%s=%s" % (key, value))

            clients_send_queue.put("\t".join(data_arr))





if __name__ == "__main__":

    # Port 0 means to select an arbitrary unused port
    HOST, PORT = "localhost", 58149
    #~ HOST, PORT = "localhost", 0

    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    server.daemon_threads = True
    ip, port = server.server_address

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()

    print "Server loop running in thread:", server_thread.name

    feeder_thread = threading.Thread(target=feed_clients)
    feeder_thread.daemon = True
    feeder_thread.start()

    radio_sender_thread = threading.Thread(target=radio_send)
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
    radio.start()

    radio.setPowerLevel(31)
    #~ radio.setHighPower(True)
    radio.setHighPower(False)
    radio.receiveBegin()



    counter = 0
    while 1:
        data = radio.getDataBlocking()
        if not data:
            time.sleep(0.1)
            continue

        #~ print "got data", data

        counter += 1
        process_recv_radio_data(data, counter)








    #~ server.shutdown()
