# Introduction
This software allows you to use a pimoroni galactic unicorn rgb matrix running micropython as a clock. 
Made for the original PicoW version of the galactic unicorn and it is unknown if it works on the PicoW 2 version.
# Features
### Internet Connectivity
It supports connectivity via the internet to auto-sync the time. The time can be synced manually by pressing the A button.
The time zone can be changed by using the B button to make it go forward an hour and the C button to make it go backward an hour.
### Weather
It supports displaying the weather next to the time as well
### Brightness Sensor
It uses the brightness sensor to auto-adjust the brightness depending on lighting conditions around the board.
# Setup
Simply just copy the source code onto the galactic unicorn's storage using an IDE such as Thonny to transfer each file.
Next fill out WIFI_SSID and WIFI_PASSWORD with your wifi ssid and wifi password(who would've guessed) in secrets.py, alongside your approximate longitude and latitude, which is needed to display the weather.
