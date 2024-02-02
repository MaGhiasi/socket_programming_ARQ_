import socket
import math
import random
import time


def initial_data(is_exact, is_random):
    if is_exact == 'Y':
        return [[], [], []]
    if is_random == 'Y':
        crashed_frames = list(set(sorted([random.randint(0, 31) for _ in range(random.randint(2, 15))])))
        crashed_rr = list(set(sorted([random.randint(0, 31) for _ in range(random.randint(2, 15))])))
        crashed_rej = list(set(sorted([random.randint(0, 10) for _ in range(random.randint(2, 10))])))
        return [crashed_frames, crashed_rr, crashed_rej]

    return [[2, 8, 12, 15, 23, 27], [0, 2, 3, 7, 8, 12, 16, 19, 20, 24, 27, 28], [2, 5]]
    # [[2, 8, 22, 28], [9, 12, 13, 14, 19, 24, 25], [0, 2, 3]]
    # 2 (fr), 0 (rej) => damaged frame then damaged REJ then frame-time out
    # 8 (fr) => damaged frame
    # 9 (rr) => damaged RR (no problem due to next RR)
    # 12, 13, 14 => consecutive damaged RRs then frame-time out
    # 22 (fr) , 2 (rej) , 19 (rr) => no response to first Pbit=1
    #                 but response to second Pbit=1 and continue
    # 28 (fr) , 3 (rej) , 24, 25 (rr) => no response to 2 Pbit=1 in a row and END connection


class Receiver:

    def __init__(self, w, k, crashed_fr_rr_rej):
        self.frame_buffer = []
        self.w = w
        self.k = k
        self.last_ack = 0
        self.frame_counter = 0
        self.has_rejected = False
        self.counter_fr_rr_rej = [0, 0, 0]
        self.crashed_fr_rr_rej = crashed_fr_rr_rej
        # socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = None

    def initiate_channel(self):
        self.sock.bind(('127.0.0.1', 8080))
        self.sock.listen()
        print('listening')
        self.conn, addr = self.sock.accept()
        self.conn.sendall(str(self.k).encode())
        time.sleep(0.5)
        self.conn.sendall(str(self.w).encode())
        self.receive()

    def receive(self):
        print('\u001b[31m ============= receiver =============\u001b[0m', end='')
        data = ''
        while data != 'DISC':
            data = self.conn.recv(1024).decode()
            self.detect_message(data)

    def detect_message(self, data):
        if 'RR' in data:    # if packet is RR(pbit=1)
            print('\n\u001b[31m >>>\u001b[0m received message:' + data)
            self.send_RR(self.counter_fr_rr_rej[1] in self.crashed_fr_rr_rej[1])

        elif 'DISC' in data:    # if packet is a frame (data)
            print('\n\u001b[31m >>>\u001b[0m received message:' + '\u001b[34m DISC\u001b[0m')
        else:
            # Does not receive some specific packets
            if self.counter_fr_rr_rej[0] not in self.crashed_fr_rr_rej[0]:
                print('\n\u001b[31m >>>\u001b[0m received message:' + data)

                self.last_ack = ((self.last_ack + 1) % (math.pow(2, self.k)))
                seq_number = int(data[-self.k:], 2)
                self.send_ack(seq_number, data)

            self.counter_fr_rr_rej[0] += 1

    def send_ack(self, seq_num, data):
        if self.frame_counter == seq_num:
            self.frame_buffer.append(data)
            self.frame_counter = int((self.frame_counter + 1) % math.pow(2, self.k))
            self.has_rejected = False
            self.send_RR(self.counter_fr_rr_rej[1] in self.crashed_fr_rr_rej[1])

        # to discard others after rejection (if seq num is not correct)
        elif not self.has_rejected:
            self.send_REJ(self.counter_fr_rr_rej[2] in self.crashed_fr_rr_rej[2])
            self.has_rejected = True

    def send_RR(self, is_crashed):
        time.sleep(0.5)
        message = 'RR' + str(self.frame_counter)
        print('send RR: \u001b[34m' + message + '\u001b[0m', end='')
        if not is_crashed:
            self.conn.sendall(message.encode())
            print()
        else:
            print('\u001b[31m \u2718 \u001b[0m')

        self.counter_fr_rr_rej[1] += 1

    def send_REJ(self, is_crashed):
        time.sleep(0.5)
        message = 'REJ' + str(self.frame_counter)
        print('send REJ: \u001b[31m' + message + '\u001b[0m', end='')
        if not is_crashed:
            self.conn.sendall(message.encode())
            print()
        else:
            print('\u001b[31m \u2718 \u001b[0m')

        self.counter_fr_rr_rej[2] += 1


if __name__ == '__main__':
    seq_bits = int(input('Enter K: '))
    window_size = int(input('Enter W: '))
    while window_size > math.pow(2, seq_bits) - 1:
        window_size = int(input(' >>> W out of range\nEnter W: '))

    exact_connection = input('If you want connection without data loss Enter Y,\nelse enter anything: ')
    is_random_loss = 'N'
    if exact_connection != 'Y':
        is_random_loss = input('If you want random data loss Enter Y,\nelse enter anything: ')

    crashed_packets = initial_data(exact_connection, is_random_loss)
    print('> So crashed packets are as follows:\u001b[31;1m\ncrashed data:' + str(crashed_packets[0]) +
          '\ncrashed RR messages:' + str(crashed_packets[1]) +
          '\ncrashed REJ messages:' + str(crashed_packets[2]) + '\u001b[0m')

    receiver = Receiver(window_size, seq_bits, crashed_packets)
    receiver.initiate_channel()
