import time
import socket
import threading
import SocketServer
import Queue

from collections import deque
from weakref import WeakValueDictionary

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

        for handler in client_handlers.values():
            handler.wfile.write(line)
            handler.wfile.flush()

def radio_send():
    while True:
        line = radio_send_queue.get()
        print "got line", line

        clients_send_queue.put("blah===" + line)


radio = None

if __name__ == "__main__":
    # Port 0 means to select an arbitrary unused port
    HOST, PORT = "localhost", 58149

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


    radio = rfm69.RFM69()
    radio.start()


#~ radio.setHighPower(True)
    radio.setHighPower(False)
    radio.receiveBegin()

    while 1:
        data = radio.getDataBlocking()
        if not data:
            time.sleep(0.1)
            continue

        print "got data", data




    #~ server.shutdown()
