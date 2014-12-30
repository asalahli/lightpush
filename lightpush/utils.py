def create_packet(message):
    packet = bytearray(message)
    packet.insert(0, len(packet))
    packet.insert(0, 129)
    return packet
