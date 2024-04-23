from globals import Globals


class TCPFlags:
    """
        Class for managing TCP flags
    """

    def __init__(self, *flags):
        """
            Add flags to the container

            `flags`: (*string) flags to add (declared in globals.Globals)
        """

        # 8-bit container for flags
        # in python cannot explicitly declare 8-bit variable
        self.flag_bits = 0

        for flag in flags:
            self.flag_bits |= Globals.kTCPFlagBits[flag]

    @classmethod
    def fromInt(cls, flag_bits):
        """
            Construct a container from flags

            `flag_bits`: (int) already encoded flags

            `return`: (TCPFlags) container
        """

        new_flags = cls()
        new_flags.flag_bits = flag_bits
        return new_flags

    def getFlags(self):
        """
            Get the flags from the container

            `return`: (int) flags
        """

        return self.flag_bits

    def decodeFlags(self):
        """
            Decode flags

            `return`: (list[string]) flags
        """

        # list of flags
        flags = []

        # do not need MSG here, but x & 0 == 0. Perfect
        for repr, flag in Globals.kTCPFlagBits.items():
            if (self.flag_bits & flag) != 0:
                flags.append(repr)

        if len(flags) == 0:
            flags.append("MSG")

        return flags


class Batch:
    """
        Class for batching data
    """

    # constants (!DO NOT MODIFY!)
    kCharsForType = 1
    kCharsForSeqNum = (Globals.kHeaderSize - kCharsForType) // 2
    kCharsForAckNum = (Globals.kHeaderSize - kCharsForType) // 2

    def __init__(self, seq_num, ack_num, data, *flags):
        """
            Construct a batch

            `seq_num`: (int) sequence number of the batch
            `ack_num`: (int) acknowledgement number of the batch
            `data`: (bytes) data to be sent
            `flags`: (*string) flags of the batch
        """

        self.flags = TCPFlags(*flags)
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.data = data

    @classmethod
    def decode(cls, data, byteorder="big"):
        """
            Decode the batch from bytes. Uses big endian by default.

            `data`: (bytes) data, containing batch information
            `byteorder`: (str) byte order to use ("big" or "little" for big or little endian)

            `return`: (Batch) decoded batch
        """

        flags = TCPFlags.fromInt(int.from_bytes(data[:cls.kCharsForType], byteorder))

        from_idx = cls.kCharsForType
        to_idx = from_idx + cls.kCharsForSeqNum

        seq_num = int.from_bytes(data[from_idx:to_idx], byteorder)

        from_idx = to_idx
        to_idx = from_idx + cls.kCharsForAckNum

        ack_num = int.from_bytes(data[from_idx:to_idx], byteorder)

        new_batch = cls(seq_num, ack_num, data[to_idx:])
        new_batch.flags = flags

        return new_batch

    def encode(self, byteorder="big"):
        """
            Encode the batch into bytes. Uses big endian by default.

            `byteorder`: (str) byte order to use ("big" or "little" for big or little endian)

            `return`: (bytes) encoded batch
        """

        return self.flags.getFlags().to_bytes(self.kCharsForType, byteorder) + \
            self.seq_num.to_bytes(self.kCharsForSeqNum, byteorder) + \
            self.ack_num.to_bytes(self.kCharsForAckNum, byteorder) + \
            self.data

    def getFlags(self):
        """
            Get the flags from the container

            `return`: (list[string]) flags
        """

        return self.flags.decodeFlags()

    def __lt__(self, other):
        """
            Compare two batches

            `other`: (Batch) batch to compare

            `return`: (bool) True if self sequence number is less than other sequence number
        """

        return self.seq_num < other.seq_num

    def __repr__(self):
        """
            Get string representation of batch
        """

        result = " | ".join(self.flags.decodeFlags())
        result += f": {self.seq_num} : {self.ack_num}; {str(self.data)}"

        return result