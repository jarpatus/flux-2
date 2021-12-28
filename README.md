# flux-2
Enhanced version of Home Assistant's Flux component allowing more granular control of color temperature and brightness making flux-2 more suitable for us living far from the equator. 

## Configuration

One can now define various time spans by setting following flux options in configuration.yaml (if not set then options do default to corresponding astronomical times):
```
    start_time: '07:00'
    sunrise_time: '08:00'
    sunset_time: '18:00'
    stop_time: '20:00'
```
    
Time between start_time and sunrise_time is dawn, time between sunrise_time and sunset_time is day, time between sunset_time and stop_time is dusk. 

Flux-2 can adjust color temperature within each time span by setting following flux options in configuration.yaml:
```
    start_colortemp: 2500
    sunrise_colortemp: 5500
    sunset_colortemp: 5500
    stop_colortemp: 2500
```
    
Flux-2 can adjust brigthness within each time span by setting following flux options in configuration.yaml:
```
    start_brightness: 128
    sunrise_brightness: 255
    sunset_brightness: 255
    stop_brightness: 128
```
    
These options allows quite granular control e.g. you can set lights to ramp up agressively during dusk, then stay at full brightness during the day and then ramp down less agressively on dawn - whatever is your preference.

Full configuration example:
```
switch:
  - platform: flux
    name: Flux
    lights: !include_dir_merge_list includes/entities/lights/
    start_time: '07:00'
    sunrise_time: '08:00'
    sunset_time: '18:00'
    stop_time: '19:00'
    start_colortemp: 2500
    sunrise_colortemp: 5500
    sunset_colortemp: 5500
    stop_colortemp: 2500
    start_brightness: 255
    sunrise_brightness: 255
    sunset_brightness: 255
    stop_brightness: 128
    disable_brightness_adjust: false
    mode: mired
    transition: 0.5
```

## Installation

Install by dropping flux into ~/.homeassistant/custom_components . Please notice that flux-2 may or may not be compatible with the latest Home Assistant. I sadly lack time and cannot maintain this actively just like I cannot update my own Home Assistant installation actively :(

## Tips and tricks

Home Assistant won't "enforce" scenes etc. so if you have some bulbs powered off from mains they will start with color temperature and brigthness of whatever they want even when flux is supposed to be running and won't get updated until next scheduled flux "update". This may be highly annoying so to avoid ridiculously low interval setting following automation can be used to apply flux as soons as home assistant will detect bulb (on this example entity_ids are listed on separate yaml files on ~/.homeassistant/includes/entities/lights/):

```
- alias: Flux update on light on
  trigger:
  - platform: state
    entity_id: !include_dir_merge_list includes/entities/lights/
    to: 'on'
  condition:
  - condition: state
    entity_id: switch.flux
    state: 'on'
  action:
  - service: switch.flux_update
    data:
      transition: 1
```
