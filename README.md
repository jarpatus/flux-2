# flux-2
Enhanced version of Home Assistant's Flux component allowing more granular control of color temperature and brightness making flux-2 more suitable for us living far from the equator. 

One can now define various time spans by setting following flux options in configuration.yaml:\
    start_time: '07:00'\
    sunrise_time: '08:00'\
    sunset_time: '18:00'\
    stop_time: '20:00'
    
Time between start_time and sunrise_time is dawn, time between sunrise_time and sunset_time is day, time between sunset_time and stop_time is dusk. 

Flux-2 can adjust color temperature within each time span by setting following flux options in configuration.yaml:\
    start_colortemp: 2500\
    sunrise_colortemp: 5500\
    sunset_colortemp: 5500\
    stop_colortemp: 2500\
    
Flux-2 can adjust brigthness within each time span by setting following flux options in configuration.yaml:\
    start_brightness: 255
    sunrise_brightness: 255
    sunset_brightness: 255
    stop_brightness: 128
    
These options allows quite granular control e.g. you can set lights to ramp up agressively during dusk, then stay at full brightness during the day and then ramp down less agressively on dawn - whatever is your preference.
