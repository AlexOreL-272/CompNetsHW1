from batcher import Batch
from globals import Globals
from logger import Logger
from sortedcontainers import SortedList
import time
import threading
import queue

import socket


class UDPBasedProtocol:
    def __init__(self, *, local_addr, remote_addr):
        self.udp_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.remote_addr = remote_addr
        self.udp_socket.bind(local_addr)

    def sendto(self, data):
        return self.udp_socket.sendto(data, self.remote_addr)

    def recvfrom(self, n):
        msg, addr = self.udp_socket.recvfrom(n)
        return msg

    def close(self):
        self.udp_socket.close()


class MyTCPProtocol(UDPBasedProtocol):
    def __init__(self, *args, **kwargs):
        """
            Constructor
        """

        super().__init__(*args, **kwargs)
        self.udp_socket.settimeout(0.001)
        self.seq_num = 0
        self.ack_num = 0

        self.ack_queue = queue.PriorityQueue()
        
        # self.recv_batches = set()
        self.recv_batches = SortedList()
        # self.recv_batches = queue.PriorityQueue()

        self.logger = Logger("log.txt")

        self.ack_thread = threading.Thread(target=self.__handle_acks)
        self.ack_thread.daemon = True
        self.ack_thread.start()

    def __split(self, data):
        """
            Split data into batches

            `data`: (bytes) data to split

            `return`: (list[Batch]) list of batches
        """

        kInputSize = len(data)
        processed_size = 0

        batches = []

        while processed_size < len(data):
            kEndIdx = min(processed_size + Globals.kDataSize, kInputSize)
            kBatchSize = kEndIdx - processed_size

            batch = Batch(self.seq_num, self.seq_num + kBatchSize,
                          data[processed_size:kEndIdx], "MSG")
            batches.append(batch)

            self.seq_num += kBatchSize
            processed_size += kBatchSize

        return batches

    def __send_batch(self, batch):
        """
            Send a batch

            `batch`: (Batch) batch to send

            `return`: (int) number of bytes sent
        """

        bytes_sent = self.sendto(batch.encode())

        if Globals.log:
            self.logger.log(
                f"SEND: Sent {bytes_sent} bytes from batch ({batch})")

        return bytes_sent

    def __send_ack(self, seq_num=0):
        """
            Send acknowledgement batch
        """

        ack_batch = Batch(seq_num, seq_num, b"", "ACK")

        if Globals.log:
            self.logger.log(f"SEND: Sending ACK batch ({ack_batch})")

        self.__send_batch(ack_batch)

    def __handle_acks(self):
        """
            Handle acknowledgements
        """

        while True:
            time.sleep(0)

            try:
                response = Batch.decode(self.recvfrom(Globals.kHeaderSize))
                flags = response.getFlags()

                if "ACK" not in flags:
                    continue

                while not self.ack_queue.empty() and response.ack_num >= self.ack_queue.queue[0].ack_num:
                    self.ack_queue.get()

            except TimeoutError:
                for batch in self.ack_queue.queue:
                    if Globals.log:
                        self.logger.log(f"HANDLE: Resending batch ({batch})")

                    try:
                        self.__send_batch(batch)
                    except Exception:
                        pass

            except:
                pass

    def send(self, data: bytes):
        if Globals.log:
            self.logger.log(f"SEND: Sending {data}")

        batches = self.__split(data)

        for batch in batches:
            # send the batch
            self.__send_batch(batch)
            self.ack_queue.put(batch)

        return len(data)

    def recv(self, n: int):
        if Globals.log:
            self.logger.log(f"RECV: Receiving {n} bytes")

        received = b""
        need_to_stop = False

        while len(received) < n:
            time.sleep(0)

            try:
                response = Batch.decode(self.recvfrom(Globals.kBatchSize))
                flags = response.getFlags()

                if "MSG" not in flags:
                    continue

                self.recv_batches.add(response)
                # self.recv_batches.append(response)
            except TimeoutError:
                continue
                # self.__send_ack(self.ack_num)
            except Exception as e:
                raise e

            # self.recv_batches.sort()
            while len(self.recv_batches) > 0:
                front = self.recv_batches[0]

                if self.ack_num >= front.seq_num:
                    if self.ack_num == front.seq_num:
                        self.ack_num = front.ack_num
                        received += front.data

                    self.recv_batches.pop(0)

                    if len(received) == n:
                        need_to_stop = True
                        break
                else:
                    break

            self.__send_ack(self.ack_num)

            if need_to_stop:
                break

        return received

    def close(self):
        # need to send FIN?
        super().close()
