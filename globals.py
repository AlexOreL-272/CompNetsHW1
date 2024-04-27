from datetime import timedelta


class Globals:
    """
        Class for global variables
    """

    # stores packet type, seq_num and ack_num (char + 2 * unsigned long long)
    kHeaderSize = 1 + 8 + 8
    # max amount of bytes that fit into channel
    kBatchSize = 2 ** 16

    # max TCP header size
    kMaxTCPHeaderSize = 60
    # max amount of data bytes that can be sent in one batch
    kDataSize = kBatchSize - kHeaderSize - kMaxTCPHeaderSize

    # time to wait for send/receive operations
    kTimeout = timedelta(milliseconds=10)

    # TCP flag bits (!DO NOT MODIFY!)
    kTCPFlagBits = {
        "MSG": 0,   # There is no MSG flag in TCP, but it is for better understanding and logging
        "URG": 1,   # NOT IMPLEMENTED
        "ACK": 2,
        "PSH": 4,   # NOT IMPLEMENTED
        "RST": 8,   # NOT IMPLEMENTED
        "SYN": 16,  # NOT IMPLEMENTED
        "FIN": 32   # NOT IMPLEMENTED
    }

    kLogMaxSize = 10
    log = False
