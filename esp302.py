# -*- coding: utf-8 -*-
"""
Created on Thu Sep 15 14:44:10 2022

@author: Nicolas Faure
"""

import socket  # used for TCP/IP communication

# Prepare 3-byte control message for transmission
TCP_IP = "192.168.254.254"
TCP_PORT = 5002

BUFFER_SIZE = 80


class ESP302:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((TCP_IP, TCP_PORT))

    def close(self):
        self.s.close()

    def sendMessage(self, message):
        self.s.send(message)
        return self.s.recv(BUFFER_SIZE).decode().strip().split(",")[1]

    def getPosition(self, axis: int) -> str:
        message = (str(axis) + "TP?").encode()
        current_pos = self.sendMessage(message)
        print("getPosition :", current_pos)
        return current_pos

    def moveRelative(self, axis: int, pas):
        message = (str(axis) + "PR" + str(pas)).encode()
        self.sendMessage(message)

    def moveAbsolute(self, axis: int, pos):
        message = (str(axis) + "PA" + str(pos)).encode()
        self.sendMessage(message)

    def getMaxVelocity(self, axis: int):
        message = (str(axis) + "VU?").encode()
        print("getMaxVelocity :", self.sendMessage(message))

    def getVelocity(self, axis: int):
        message = (str(axis) + "VA?").encode()
        print("getVelocity :", self.sendMessage(message))

    def setVelocity(self, axis: int, velocity):
        message = (str(axis) + "VA" + str(velocity)).encode()
        self.sendMessage(message)

    def queryAtPosition(self, axis: int, requested_pos) -> bool:
        current_pos = self.getPosition(axis)
        if current_pos == str(requested_pos):
            return True
        else:
            return False


def main():
    test = ESP302()

    test.getPosition(1)

    test.getVelocity(1)

    test.setVelocity(1, 40)

    test.getMaxVelocity(1)
    test.close()


if __name__ == "__main__":
    main()
