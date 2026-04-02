# Example usage:
# from dht21 import AHT20
# sensor = AHT20(1, 2)
# if sensor.Is_Calibrated():
#     temp = sensor.T()
#     humidity = sensor.RH()
#     print(f"Temperature: {temp}°C, Humidity: {humidity}%")


'''
AHT20, AHT21 (humidity and temperature sensors)
MicroPython driver for micro:bit

CREDIT for CRC calculation:
    SOURCE: AHT30 Datasheet, 3.CRCcheck, page 11.
    Function: unsigned char Calc_CRC8()
    Translated from C++
    to MicroPython for the micro:bit.

AUTHOR: fredscave.com
DATE  : 2024/11
VERSION : 1.00
'''
from machine import I2C, Pin
from micropython import const
import time

ADDR = const(0x38)
CMD_INIT = [0xBE, 0x08, 0x00]
CMD_MEASURE = [0xAC, 0x33, 0x00]
CMD_RESET = const(0xBA)
CRC_INIT = const(0xFF)
CRC_POLY = const(0x31)

class AHT21():
    def __init__(self, scl_pin, sda_pin, addr=ADDR):
        time.sleep_ms(100)
        self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=100_000)
        self.addr = addr
        self.IsChecksum = False
        self.Initialise()
        time.sleep_ms(10)
        self.IsCalibrated = self.Read_Status() & 0b00001000

    def Initialise(self):
        self.i2c.writeto(self.addr, bytearray(CMD_INIT))

    def Read_Status(self):
        buf = self.i2c.readfrom(self.addr, 1)
        return buf[0]

    def Is_Calibrated(self):
        return bool(self.IsCalibrated)

    def Is_Checksum(self):
        return self.IsChecksum

    def Read(self):
        self.i2c.writeto(self.addr, bytearray(CMD_MEASURE))
        time.sleep_ms(80)
        busy = True
        while busy:
            #buf = self.i2c.readfrom(self.addr, 1)
            time.sleep_ms(10)
            busy = self.Read_Status() & 0b10000000
        buf = self.i2c.readfrom(self.addr, 7)
        measurements = self._Convert(buf)
        return measurements

    def T(self):
        measurements = self.Read()
        return round(measurements[1], 1)

    def RH(self):
        measurements = self.Read()
        return int(measurements[0] + 0.5)

    def Reset(self):
        self.i2c.writeto(self.addr, bytes([CMD_RESET]))
        time.sleep_ms(20)

    def _Convert(self, buf):
        RawRH = ((buf[1] << 16) |( buf[2] << 8) | buf[3]) >> 4
        # RH = RawRH * 100 / 0x100000
        RH = RawRH * 100 / 1048575
        RawT = ((buf[3] & 0x0F) << 16) | (buf[4] << 8) | buf[5]
        # T = ((RawT * 200) / 0x100000) - 50
        T = (RawT * 200 / 1048575) - 50
        self.IsChecksum = self._Compare_Checksum(buf)
        return (RH, T, self.IsChecksum)

    def _Compare_Checksum(self, buf):
        check = bytearray(1)
        check[0] = CRC_INIT
        for byte in buf[:6]:
            check[0] ^= byte
            for x in range(8):
                if check[0] & 0b10000000:
                    check[0] = (check[0] << 1) ^ CRC_POLY
                else:
                    check[0] = check[0]<< 1
        return check[0] == buf[6]
