import network
import json
import uasyncio
from machine import Pin
import utime
import _thread

led = Pin('LED', Pin.OUT, value=0)

left_pin = Pin(2, Pin.IN, Pin.PULL_UP)
middle_pin = Pin(3, Pin.IN, Pin.PULL_UP)
right_pin = Pin(4, Pin.IN, Pin.PULL_UP)

echo = Pin(14, Pin.IN, Pin.PULL_DOWN)
trig = Pin(15, Pin.OUT, value=0);

RS = Pin(12, Pin.OUT, value=0)
RW = Pin(11, Pin.OUT, value=0)
E = Pin(10, Pin.OUT, value=0)
D7 = Pin(9, Pin.OUT, value=0)
D6 = Pin(8, Pin.OUT, value=0)
D5 = Pin(7, Pin.OUT, value=0)
D4 = Pin(6, Pin.OUT, value=0)

SSID = 'Pit bull network 3'
PASSWORD = '6wfc353HHH'

HOST = 'raspberrypi.local'
PORT = 9090

DEVICE_ALIAS = 'Control Panel'

state = 'MAIN'
temperature = 65
fan = 'off'
compressor = 'off'

last_det = False
light_state = False

writer = None
reader = None

class Button:
    def __init__(self, button):
        self.button = button
        self.last_pressed = False
    
    def is_pressed(self):
        #print(self.button.value())
        return not self.button.value()
    
    def debounce(self):
        pressed = self.is_pressed()
        ret = 0
        if pressed and not self.last_pressed:
            utime.sleep_ms(250)
            if self.is_pressed():
                ret = 2
            else:
                ret = 1
        self.last_pressed = pressed
        return ret

class Ultrasonic:
    def __init__(self, trig, echo):
        self.trig = trig
        self.echo = echo
    
    def get_distance(self):
        self.trig.value(1)
        self.trig.value(0)
        start = None
        distance_cm = None
        started = False
        while True:
            if self.echo.value() and not started:
                start = utime.ticks_us()
                started = True
            elif not self.echo.value() and started:
                end = utime.ticks_us()
                distance_cm = utime.ticks_diff(end, start) / 58
                break
        return distance_cm
    
    def detected(self, threshold):
        distance = self.get_distance()
        if distance <= threshold:
            return True
        else:
            return False

class LCD:
    def __init__(self, RS, E, D7, D6, D5, D4):
        self.RS = RS
        self.E = E
        self.D7 = D7
        self.D6 = D6
        self.D5 = D5
        self.D4 = D4
        
    def write8(self, num):
        self.D4.value((num & 16) >> 4)
        self.D5.value((num & 32) >> 5)
        self.D6.value((num & 64) >> 6)
        self.D7.value((num & 128) >> 7)
        self.pulse()
        self.D4.value((num & 1) >> 0)
        self.D5.value((num & 2) >> 1)
        self.D6.value((num & 4) >> 2)
        self.D7.value((num & 8) >> 3)
        self.pulse()

    def write4(self, num):
        self.D4.value((num & 1) >> 0)
        self.D5.value((num & 2) >> 1)
        self.D6.value((num & 4) >> 2)
        self.D7.value((num & 8) >> 3)
        self.pulse()

    def pulse(self):
        self.E.value(1)
        utime.sleep_us(40)
        self.E.value(0)
        utime.sleep_us(40)

    def setup(self):
        self.RS.value(0)
        self.write4(0b0011)
        self.write4(0b0011)
        self.write4(0b0011)
        self.write4(0b0010)
        self.write8(0b00101000)
        self.write8(0b00001100)
        self.write8(0b00000110)
        self.clear()
        self.RS.value(1)

    def move_cursor_right(self, shift):
        self.RS.value(0)
        for s in range(shift):
            self.write8(0b00010100)
        self.RS.value(1)

    def set_cursor(self, line, col):
        self.RS.value(0)
        shift = col
        if line == 2:
            shift = shift + 40
        self.write8(0b00000010)
        utime.sleep_ms(2)
        self.move_cursor_right(shift)
        self.RS.value(1)

    def display(self, text):
        for c in text:
            self.write8(ord(c))
            
    def clear(self):
        RS.value(0)
        self.write8(0b00000001)
        utime.sleep_ms(2)
        RS.value(1)

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
        utime.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('Network Connection Failed')
    else:
        status = wlan.ifconfig()
        print('Connected to Network, IP = ' + status[0])

async def connect_to_server():
    global reader
    global writer
    reader, writer = await uasyncio.open_connection(HOST, PORT)
    writer.write(to_json('alias', DEVICE_ALIAS).encode('utf-8'))
    await writer.drain()
    data = await reader.read(1024)
    print(data.decode('utf-8')) 

async def run_client():
    global reader
    global writer
    await connect_to_server()
    uasyncio.create_task(interface_panel())
    
    while True:
        data = await reader.read(1024)
        if not data:
            print('Disconnected from Server')
            writer.close()
            break
        await uasyncio.sleep_ms(10)

def to_json(cmd, value):
    js_list = {
        'cmd': cmd,
        'value': value
    }
    return json.dumps(js_list)

def from_json(js_string):
    js_list = json.loads(js_string)
    return js_list['cmd'], js_list['value']

def poll_ultrasonic():
    global light_state
    global last_det
    det = ultrasonic.detected(20)
    msg = None
    if det and not last_det:
        if light_state:
            print('off')
            msg = to_json('lights', 'off')
            writer.write(msg.encode('-utf-8'))
            await writer.drain()
            light_state = False
        else:
            print('on')
            msg = to_json('lights', 'on')
            writer.write(msg.encode('-utf-8'))
            await writer.drain()
            light_state = True
    last_det = det

def display_main():
    display.clear()
    display.set_cursor(1, 5)
    display.display('Control')
    display.set_cursor(2, 6)
    display.display('Panel')
    
def display_ac():
    global fan
    global compressor
    
    display.clear()
    display.set_cursor(1, 5)
    display.display('AC:' + fan)
    display.set_cursor(2, 0)
    display.display(f'Temp:{temperature}')
    display.set_cursor(2, 8)
    display.display('Cool:' + compressor)

async def interface_panel():
    global state
    global fan
    global compressor
    global temperature
    ac_opt = 'power'
    lights_opt = 'power'
    display_main()
    while True:
        #await poll_ultrasonic()
        left = left_button.debounce()
        middle = middle_button.debounce()
        right = right_button.debounce()
            
        if state == 'MAIN':
            if middle == 1:
                state = 'AC_POWER'
                display_ac()
        elif state == 'AC_POWER':
            if middle == 1:
                state = 'MAIN'
                display_main()
            elif middle == 2:
                state = 'AC_TEMP'
            elif left and fan == 'on':
                fan = 'off'
                display_ac()
            elif right and fan == 'off':
                fan = 'on'
                display_ac()
        elif state == 'AC_TEMP':
            if middle == 1:
                state = 'MAIN'
                display_main()
            elif middle == 2:
                state = 'AC_COOL'
            elif left and temperature > 60:
                temperature = temperature - 1
                display_ac()
            elif right and temperature < 75:
                temperature = temperature + 1
                display_ac()
        elif state == 'AC_COOL':
            if middle == 1:
                state = 'MAIN'
                display_main()
            elif middle == 2:
                state = 'AC_POWER'
            elif left and compressor == 'on':
                compressor = 'off'
                display_ac()
            elif right and compressor == 'off':
                compressor = 'on'
                display_ac()
        await uasyncio.sleep_ms(50)

if __name__ == '__main__':
    display = LCD(RS, E, D7, D6, D5, D4)
    ultrasonic = Ultrasonic(trig, echo)
    left_button = Button(left_pin)
    middle_button = Button(middle_pin)
    right_button = Button(right_pin)
    display.setup()
    connect_to_network()
    loop = uasyncio.new_event_loop()
    loop.run_until_complete(run_client())