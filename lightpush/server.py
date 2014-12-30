import select

from lightpush.workers import Listener
from lightpush.utils import create_packet


class Server(object):
    general_mask = select.POLLERR | select.POLLHUP
    reader_mask = select.POLLIN | select.POLLPRI
    writer_mask = select.POLLOUT

    def __init__(self, host, port):
        self.poller = select.poll()
        self.workers = {}
        self.clients = []

        self.listener = Listener(self, host, port)
        self.add(self.listener)

    def add(self, worker):
        event_mask = self.general_mask
        
        if worker.is_reader:
            event_mask = event_mask | self.reader_mask
        
        if worker.is_writer:
            event_mask = event_mask | self.writer_mask

        self.poller.register(worker, event_mask)
        self.workers[worker.fileno()] = worker

        if worker.is_client:
            self.clients.append(worker)

    def remove(self, worker):
        self.poller.unregister(worker)
        self.workers.pop(worker.fileno())

        if worker.is_client:
            self.clients.remove(worker)

    def broadcast(self, message):
        print("Broadcasting: %s" % message)
        packet = create_packet(message)

        for client in self.clients:
            client.enqueue(packet)

    def main(self):
        while True:
            events = self.poller.poll()
            for fd, event in events:
                worker = self.workers[fd]

                if event & select.POLLHUP:
                    worker.close()

                if event & select.POLLERR:
                    worker.error()

                if event & (select.POLLIN | select.POLLPRI):
                    worker.read()

                if event & select.POLLOUT:
                    worker.write()

