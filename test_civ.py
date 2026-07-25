"""
==========================================================
ON3RT Radio Suite
Test CI-V - Lecture ID IC-7300
==========================================================
"""

import time
import serial
from serial.tools import list_ports

PORT = "COM20"
BAUDRATE = 19200
TIMEOUT = 2.0


def list_com():

    print("=" * 60)
    print("PORTS DISPONIBLES")
    print("=" * 60)

    for p in list_ports.comports():
        print(f"{p.device:8} {p.description}")

    print("=" * 60)
    print()


def send(ser, frame):

    print("TX :", frame.hex(" ").upper())

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    ser.write(frame)
    ser.flush()

    start = time.time()

    while True:

        if ser.in_waiting:

            data = ser.read(ser.in_waiting)

            print("RX :", data.hex(" ").upper())
            return

        if time.time() - start > TIMEOUT:
            print("RX : TIMEOUT")
            return

        time.sleep(0.01)


def main():

    print()
    print("=" * 60)
    print("TEST CI-V IC-7300")
    print("=" * 60)

    list_com()

    try:

        ser = serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=TIMEOUT,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )

    except Exception as e:

        print("Impossible d'ouvrir", PORT)
        print(e)
        return

    print("Connexion OK")
    print()

    #
    # Lecture de l'identifiant radio
    #
    print("--------------------------------------------")
    print("Lecture ID Radio")
    print("--------------------------------------------")

    send(
        ser,
        bytes.fromhex("FE FE 94 E0 19 00 FD")
    )

    print()

    ser.close()

    print("=" * 60)
    print("FIN")
    print("=" * 60)


if __name__ == "__main__":
    main()