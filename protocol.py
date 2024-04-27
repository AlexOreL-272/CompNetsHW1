from batcher import Batch
from globals import Globals
from logger import Logger
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
        self.udp_socket.settimeout(Globals.kTimeout.total_seconds())
        
        # seq_num of next batch to send
        self.seq_num = 0
        # ack_num of latest batch aknowledged
        self.ack_num = 0
        # amount of bytes received
        self.received_bytes_amt = 0

        # acknoledgement queue
        self.ack_queue = queue.PriorityQueue()
        # queue for received batches
        self.recv_queue = queue.PriorityQueue()
        
        # buffer for received data
        self.recv_buffer = b""

        self.logger = Logger("log.txt")

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

            batch = Batch(processed_size, processed_size + kBatchSize,
                          data[processed_size:kEndIdx], "MSG")
            
            batches.append(batch)
            processed_size += kBatchSize

        return batches

    def __recv_front(self):
        """
            Get front batch from the receive queue

            `return`: (Batch) front batch
        """

        return self.recv_queue.queue[0] if not self.recv_queue.empty() else None

    def __ack_front(self):
        """
            Get front batch from the acknoledgement queue

            `return`: (Batch) front batch
        """

        return self.ack_queue.queue[0] if not self.ack_queue.empty() else None

    def __send_batch(self, batch):
        """
            Send a batch

            `batch`: (Batch) batch to send

            `return`: (int) number of bytes sent
        """

        try:
            bytes_sent = self.sendto(batch.encode()) - Globals.kHeaderSize
        except TimeoutError:
            bytes_sent = 0
        except Exception as e:
            raise e

        if Globals.log:
            self.logger.log(
                f"SEND: Sent {bytes_sent} bytes from batch ({batch})")

        if batch.seq_num == self.seq_num:
            self.seq_num += bytes_sent

        flags = batch.getFlags()

        # no need to receive ACK on ACK
        if "ACK" not in flags:
            batch.prepareForResend()
            self.ack_queue.put(batch, block=False)

        return bytes_sent

    def __send_ack(self, seq_num, ack_num):
        """
            Send acknowledgement batch
        """

        ack_batch = Batch(seq_num, ack_num, b"", "ACK")

        if Globals.log:
            self.logger.log(f"SEND: Sending ACK batch ({ack_batch})")

        try:
            # not to be zero, include header
            bytes_sent = self.__send_batch(ack_batch) + Globals.kHeaderSize
            bytes_sent = self.__send_batch(ack_batch) + Globals.kHeaderSize
        except Exception as e:
            raise e

        return bytes_sent

    def __wait_for_batch(self):
        try:
            response = Batch.decode(self.recvfrom(Globals.kBatchSize))
        except TimeoutError:
            return
        except Exception as e:
            raise e

        flags = response.getFlags()

        # if it is a message
        if "MSG" in flags:
            # add received batch to the queue
            self.recv_queue.put(response, block=False)

            # while there are received batches and
            # front batch's seq_num corresponds to order
            while not self.recv_queue.empty() and \
                self.received_bytes_amt >= self.__recv_front().seq_num:
                # if it is greater, it is most likely a duplicate 
                
                # pop front batch
                front = self.recv_queue.get(block=False)
                # mark as acknowledged
                front.acked = True

                # if front batch is the next in the order
                # update recieved data
                if front.seq_num == self.received_bytes_amt:
                    self.recv_buffer += front.data
                    self.received_bytes_amt += len(front.data)

            # try to send ACK on received batch
            try:
                self.__send_ack(self.seq_num, self.received_bytes_amt)
            except Exception as e:
                raise e

        # if we got response batch with greater ack_num
        # update last acknowledged number
        if response.ack_num > self.ack_num:
            self.ack_num = response.ack_num
            
            # pop all acknowledged batches
            while not self.ack_queue.empty() and self.__ack_front().seq_num < self.ack_num:
                self.ack_queue.get(block=False)

    def __resend_first(self):
        """
            Resend the first batch in the acknoledgement queue
        """

        # if there is no batches to resend or
        # first batch not ready to be resend
        if self.ack_queue.empty() or \
            not self.__ack_front().needsToBeResent():
            return

        try:
            self.__send_batch(self.ack_queue.get(block=False))
        except Exception as e:
            raise e

    def send(self, data: bytes):
        if Globals.log:
            self.logger.log(f"SEND: Sending {data[:Globals.kLogMaxSize]}")

        kInputSize = len(data)
        bytes_sent = 0

        # while we have not sent all batches or
        # there are sent and not acknowledged batches
        while bytes_sent != kInputSize or self.ack_num < self.seq_num:
            # if we have not sent all batches
            if bytes_sent < kInputSize:
                # make batch to send
                kEndIdx = min(bytes_sent + Globals.kDataSize, kInputSize)
                kBatchToSend = Batch(self.seq_num, self.received_bytes_amt, data[bytes_sent:kEndIdx], "MSG")

                # send the batch
                bytes_sent += self.__send_batch(kBatchToSend)

            try:
                # try to receive an ACK (or message)
                self.__wait_for_batch()
                # try to resend first unacked batch
                self.__resend_first()
            except Exception as e:
                raise e

        return bytes_sent

    def recv(self, n: int):
        if Globals.log:
            self.logger.log(f"RECV: Receiving {n} bytes")

        # get data from receive buffer
        end_idx = min(n, len(self.recv_buffer))
        received = self.recv_buffer[:end_idx]
        self.recv_buffer = self.recv_buffer[end_idx:]

        while len(received) < n:
            try:
                self.__wait_for_batch()
            except Exception as e:
                raise e

            # get data from receive buffer
            end_idx = min(n, len(self.recv_buffer))
            received += self.recv_buffer[:end_idx]
            self.recv_buffer = self.recv_buffer[end_idx:]

        return received

    def close(self):
        # need to send FIN?
        super().close()
