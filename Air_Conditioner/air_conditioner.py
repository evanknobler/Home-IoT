import network
import time
import json
import uasyncio
from machine import Pin

led = Pin('LED', Pin.OUT, value=0)
fan = Pin(15, Pin.OUT, value=0)
compressor = Pin(16, Pin.OUT, value=0)

SSID = 'SylvanTree'
PASSWORD = 'classical'

HOST = '192.168.2.14'
PORT = 80

fan_state = 0
temp = 0

def connect_to_network():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    #wlan.config(pm = 0xa11140)
    wlan.connect(SSID, PASSWORD)

    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('Connection to Network...')
        time.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('Network Connection Failed')
    else:
        status = wlan.ifconfig()
        print('Connected to Network, IP = ' + status[0])

async def run_client():
    reader, writer = await uasyncio.open_connection(HOST, PORT)
    
    writer.write(b'Air Conditioner')
    await writer.drain()
    
    data = await reader.read(1024)
    print(data.decode('utf-8'))
    
    while True:
        data = await reader.read(1024)
        if not data:
            print('Server Closed')
            writer.close()
            break
        msg = json.loads(data.decode('utf-8'))
        if msg['cmd'] == 'fan':
            if msg['value'] == 'on':
                led.value(1)
            elif msg['value'] == 'off':
                led.value(0)
        
        print(data.decode('utf-8'))
        
if __name__ == '__main__':
    connect_to_network()
    loop = uasyncio.new_event_loop()
    loop.run_until_complete(run_client())