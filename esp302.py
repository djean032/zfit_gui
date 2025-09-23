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

    def getPosition(self, motor):
        message = (str(motor) + "TP?").encode()
        print("getPosition :", self.sendMessage(message))

    def moveRelative(self, motor, pas):
        message = (str(motor) + "PR" + str(pas)).encode()
        self.sendMessage(message)

    def moveAbsolute(self, motor, pos):
        message = (str(motor) + "PA" + str(pos)).encode()
        self.sendMessage(message)

    def getMaxVelocity(self, motor):
        message = (str(motor) + "VU?").encode()
        print("getMaxVelocity :", self.sendMessage(message))

    def getVelocity(self, motor):
        message = (str(motor) + "VA?").encode()
        print("getVelocity :", self.sendMessage(message))

    def setVelocity(self, motor, velocity):
        message = (str(motor) + "VA" + str(velocity)).encode()
        self.sendMessage(message)

    def isMoving(self, motor):
        pass


def main():
    test = ESP302()

    test.getPosition(1)

    test.getVelocity(1)

    test.setVelocity(1, 40)

    test.getMaxVelocity(1)
    test.close()


if __name__ == "__main__":
    main()
