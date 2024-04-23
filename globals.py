class Globals:
    """
        Class for global variables
    """

    # stores packet type, seq_num and ack_num (char + 2 * unsigned long long)
    kHeaderSize = 1 + 8 + 8
    # max amount of bytes that fit into channel
    kBatchSize = 2 ** 16

    kMaxTCPHeaderSize = 60
    kDataSize = kBatchSize - kHeaderSize - kMaxTCPHeaderSize

    # TCP flag bits (!DO NOT MODIFY!)
    kTCPFlagBits = {
        "MSG": 0,   # There is no MSG flag in TCP, but it is for better understanding
        "URG": 1,   # NOT IMPLEMENTED
        "ACK": 2,
        "PSH": 4,   # NOT IMPLEMENTED
        "RST": 8,   # NOT IMPLEMENTED
        "SYN": 16,  # NOT IMPLEMENTED
        "FIN": 32   # NOT IMPLEMENTED
    }

    log = False
