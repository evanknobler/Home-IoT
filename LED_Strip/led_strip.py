from machine import Pin
from neopixel import NeoPixel
import time
    
def travel(start, end, color, speed):
    delay = 1/(2*speed)
    dir = 1
    if start > end:
        dir = -1
    for i in range(start, end+dir, dir):
        np[i] = color
        np.write()
        time.sleep(delay)
        np[i] = (0, 0, 0)
        np.write()
        time.sleep(delay)

def pong(color, speed):
    for i in range(50):
        travel(i, 99-i, color, speed)
        np[99-i] = color
        travel(99-i-1, i+1, color, speed)
        np[i] = color

def set_color(color):
    for i in range(99):
        np[i] = color
    np.write()

def fade():
    set_color((0, 0, 0))
    for i in range(255):
        set_color((np[0][0]+1, np[0][1]+1, np[0][2]+1))
    for i in range(255):
        set_color((np[0][0]-1, np[0][1]-1, np[0][2]-1))
    
if __name__ == '__main__':
    np = NeoPixel(Pin(3), 100)
    color = (255, 255, 255)
    while True:
        fade()