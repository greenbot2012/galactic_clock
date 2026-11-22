import time
import math
import machine
import network
import ntptime
from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN as DISPLAY
import urequests
from pngdec import PNG

current_weather="cloud"
def get_weather_by_ip():
    try:
        # Step 1: Get approximate latitude and longitude using free IP geolocation (no key needed)
        geo_response = urequests.get("https://ipapi.co/json/")
        geo_data = geo_response.json()
        geo_response.close()
        
        lat = geo_data.get("latitude")
        lon = geo_data.get("longitude")
        
        if not lat or not lon:
            print("Could not parse coordinates from IP, using defaults.")
            from secrets import lat, lon
        else:
            print(f"IP Location found -> Lat: {lat}, Lon: {lon}")

        # Step 2: Fetch weather from Open-Meteo using the dynamic coordinates
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=weather_code"
        
        response = urequests.get(weather_url)
        data = response.json()
        response.close()
        
        code = data.get("current", {}).get("weather_code", 0)
        print(code)
        # Map WMO weather codes to your specified categories
        if code in [0,1]:
            return "sun"
        elif code in [2, 3, 45, 48]: # Clear variations, overcast, and fog
            return "cloud"
        elif code in [95, 96, 99]:     # Thunderstorms / storms
            return "storm"
        else:
            # Covers drizzle, rain, showers, and snow (mapped to rain)
            return "rain"
            
    except Exception as e:
        print("Error fetching weather/location via IP:", e)
        return "cloud"  # Fallback state if network hiccup occur
manual_sync=True
try:
    from secrets import WIFI_SSID, WIFI_PASSWORD
    wifi_available = True
except ImportError:
    print("Create secrets.py with your WiFi credentials to get time from NTP")
    wifi_available = False


# constants for controlling the background colour throughout the day
MIDDAY_HUE = 1.1
MIDNIGHT_HUE = 0.8
HUE_OFFSET = -0.1

MIDDAY_SATURATION = 1.0
MIDNIGHT_SATURATION = 1.0

MIDDAY_VALUE = 0.8
MIDNIGHT_VALUE = 0.3


# create galactic object and graphics surface for drawing
gu = GalacticUnicorn()
graphics = PicoGraphics(DISPLAY)
png = PNG(graphics)
# create the rtc object
rtc = machine.RTC()

width = GalacticUnicorn.WIDTH
height = GalacticUnicorn.HEIGHT

# set up some pens to use later
WHITE = graphics.create_pen(255, 255, 255)
BLACK = graphics.create_pen(0, 0, 0)


@micropython.native  # noqa: F821
def from_hsv(h, s, v):
    i = math.floor(h * 6.0)
    f = h * 6.0 - i
    v *= 255.0
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)

    i = int(i) % 6
    if i == 0:
        return int(v), int(t), int(p)
    if i == 1:
        return int(q), int(v), int(p)
    if i == 2:
        return int(p), int(v), int(t)
    if i == 3:
        return int(p), int(q), int(v)
    if i == 4:
        return int(t), int(p), int(v)
    if i == 5:
        return int(v), int(p), int(q)


# function for drawing a gradient background
def gradient_background(start_hue, start_sat, start_val, end_hue, end_sat, end_val):
    half_width = width // 2
    for x in range(0, half_width):
        hue = ((end_hue - start_hue) * (x / half_width)) + start_hue
        sat = ((end_sat - start_sat) * (x / half_width)) + start_sat
        val = ((end_val - start_val) * (x / half_width)) + start_val
        colour = from_hsv(hue, sat, val)
        graphics.set_pen(graphics.create_pen(int(colour[0]), int(colour[1]), int(colour[2])))
        for y in range(0, height):
            graphics.pixel(x, y)
            graphics.pixel(width - x - 1, y)

    colour = from_hsv(end_hue, end_sat, end_val)
    graphics.set_pen(graphics.create_pen(int(colour[0]), int(colour[1]), int(colour[2])))
    for y in range(0, height):
        graphics.pixel(half_width, y)


# function for drawing outlined text
def outline_text(text, x, y):
    graphics.set_pen(BLACK)
    graphics.text(text, x - 1, y - 1, -1, 1)
    graphics.text(text, x, y - 1, -1, 1)
    graphics.text(text, x + 1, y - 1, -1, 1)
    graphics.text(text, x - 1, y, -1, 1)
    graphics.text(text, x + 1, y, -1, 1)
    graphics.text(text, x - 1, y + 1, -1, 1)
    graphics.text(text, x, y + 1, -1, 1)
    graphics.text(text, x + 1, y + 1, -1, 1)

    graphics.set_pen(WHITE)
    graphics.text(text, x, y, -1, 1)


# Connect to wifi and synchronize the RTC time from NTP
# Connect to wifi and synchronize the RTC time from NTP
def sync_time():
    if not wifi_available:
        return
    # Start connection
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(pm=0xa11140)  # Turn WiFi power saving off for some slow APs
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    # Wait for connect success or failure (up to 10 seconds)
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection...')
        graphics.set_pen(BLACK)
        graphics.clear()
        if manual_sync:
            clock = "syncing..."

            # calculate text position so that it is centred
            w = graphics.measure_text(clock, 1)
            x = int(width / 2 - w / 2 + 1)
            y = 2
            outline_text(clock, x, y)
            
        else:
            redraw_display_if_reqd()
        gu.update(graphics)
        
        # Wait 1 second between checks so the Wi-Fi chip has time to connect
        time.sleep(1)

    if wlan.status() == 3:  # Check if successfully connected (STAT_GOT_IP)
        print("Connected successfully!")
        try:
            ntptime.settime()
            print("Time set via NTP")
            global current_weather
            current_weather = get_weather_by_ip()
            print("Current weather condition:", current_weather)
        except OSError:
            print("Error Getting Time from NTP.")
    else:
        print("Connection FAILED. Status code:", wlan.status())

    wlan.disconnect()
    wlan.active(False)
    clock = "syncing..."

    # calculate text position so that it is centred
    w = graphics.measure_text(clock, 1)
    x = int(width / 2 - w / 2 + 1)
    y = 2
    outline_text(clock, x, y)

# NTP synchronizes the time to UTC, this allows you to adjust the displayed time
# by one hour increments from UTC by pressing the volume up/down buttons
#
# We use the IRQ method to detect the button presses to avoid incrementing/decrementing
# multiple times when the button is held.
utc_offset = -5
f = open('data.txt')
utc_offset=int(f.read())
f.close()


up_button = machine.Pin(GalacticUnicorn.SWITCH_B, machine.Pin.IN, machine.Pin.PULL_UP)
down_button = machine.Pin(GalacticUnicorn.SWITCH_C, machine.Pin.IN, machine.Pin.PULL_UP)


def adjust_utc_offset(pin):
    global utc_offset, last_second
    if pin == up_button:
        utc_offset += 1
        last_second = None
        f = open('data.txt','w')
        f.write(str(utc_offset))
        f.close()
    if pin == down_button:
        utc_offset -= 1
        last_second = None
        f = open('data.txt','w')
        f.write(str(utc_offset))
        f.close()

up_button.irq(trigger=machine.Pin.IRQ_FALLING, handler=adjust_utc_offset)
down_button.irq(trigger=machine.Pin.IRQ_FALLING, handler=adjust_utc_offset)


year, month, day, wd, hour, minute, second, _ = rtc.datetime()

last_second = second


# Check whether the RTC time has changed and if so redraw the display
def redraw_display_if_reqd():
    global year, month, day, wd, hour, minute, second, last_second, current_weather, png

    year, month, day, wd, hour, minute, second, _ = rtc.datetime()
    if second != last_second:
        hour = (hour + utc_offset) % 24
        time_through_day = (((hour * 60) + minute) * 60) + second
        percent_through_day = time_through_day / 86400
        percent_to_midday = 1.0 - ((math.cos(percent_through_day * math.pi * 2) + 1) / 2)

        hue = ((MIDDAY_HUE - MIDNIGHT_HUE) * percent_to_midday) + MIDNIGHT_HUE
        sat = ((MIDDAY_SATURATION - MIDNIGHT_SATURATION) * percent_to_midday) + MIDNIGHT_SATURATION
        val = ((MIDDAY_VALUE - MIDNIGHT_VALUE) * percent_to_midday) + MIDNIGHT_VALUE

        gradient_background(hue, sat, val, hue + HUE_OFFSET, sat, val)
        if hour==0 or hour==24:
            display_hour=12
            night=False
        elif hour==12:
            night=True
            display_hour=12            
        elif hour>12:
            display_hour=hour-12
            night=True
        else:
            display_hour=hour
            night=False
        if night:
            clock = "{:02}:{:02}pm".format(display_hour, minute)
        else:
            clock = "{:02}:{:02}am".format(display_hour, minute)

        # calculate text position so that it is centred
        w = graphics.measure_text(clock, 1)
        x = 4
        y = 2

        outline_text(clock, x, y)

        last_second = second
        
        png.open_file(current_weather+".png")
        png.decode(0, 0)


# set the font
graphics.set_font("bitmap8")
gu.set_brightness(0.5)

# Text display sleep time in ms
TEXT_SLEEP = 500


# the onboard light sensor has a wide range from 0 t0 4095
# It is therefore needed to set a lower max and a higher minimum
MIN_LS_VALUE = 10
MAX_LS_VALUE = 295  # 4095 to use the full range
MIN_RANGE = 0.1
MAX_RANGE = 1

# Rate of display change i.e the lower the value the slower the transition
TRANSITION_RATE = 1.0 / 72.0


# perform linear interpolation to map a range of values to discrete
def map_range(
    x,
    min_input=MIN_LS_VALUE,
    max_input=MAX_LS_VALUE,
    min_output=MIN_RANGE,
    max_output=MAX_RANGE,
):
    return (x - min_input) * (max_output - min_output) / (
        max_input - min_input
    ) + min_output


# gets the light sensor value from onboard sensor and interpolates it
# clamps the brightness value it outside the ranges specified
def calculate_brightness(prev_brightness_val):
    current_lsv = gu.light()
    current_brightness_val = map_range(current_lsv)

    # uses the previous value to smooth out display changes reducing flickering
    brightness_diff = current_brightness_val - prev_brightness_val
    brightness_val = prev_brightness_val + (brightness_diff * TRANSITION_RATE)
    if brightness_val > 1:
        brightness_val = 1
    elif brightness_val < 0.1:
        brightness_val = 0.1

    return brightness_val


# draws percentage icon
def draw_percentage(x, y):
    graphics.rectangle(x + 1, y + 1, 2, 2)
    graphics.line(x + 1, y + 5, x + 6, y)
    graphics.rectangle(x + 4, y + 4, 2, 2)


# sets up a handy function we can call to clear the screen
def clear():
    graphics.set_pen(BLACK)
    graphics.clear()


mode = "auto"  # set auto brightness on
last = time.ticks_ms()
brightness_value = MIN_RANGE  # set the initial brightness level to the specified minimum
sync_timer=0
sync_delay=5000
while True:
    if gu.is_pressed(GalacticUnicorn.SWITCH_A):
        manual_sync=True
        sync_timer=0
    if sync_timer==0:
        sync_time()
        sync_timer=sync_delay
    elif sync_timer>0:
        sync_timer-=1
    else:
        sync_timer=sync_delay
    redraw_display_if_reqd()
    brightness_value = calculate_brightness(brightness_value)
    gu.set_brightness(brightness_value)


    # update the display
    gu.update(graphics)
    manual_sync=False

    time.sleep(0.01)