# Home Assistant Custom Components

## How to load custom components
https://developers.home-assistant.io/docs/en/creating_component_loading.html

## Blebox switchBox(D)
__To enable this switch, add the following lines to your configuration.yaml file:__
```
switch:
  - platform: blebox_switchbox
    host: IP_ADDRESS
```
__Configuration variables:__
* __host__ (*Required*): The IP address of your switchBox(D), eg. 192.168.1.32
* __type__ (*Optional*): The device type (switchBox or switchBoxD). If not set, will be detected automatically
* __name__ (*Optional*): The name to use when displaying this switch. If not set, will be used relay name from the device
* __relay__ (*Optional*): The number of the relay. Default is 0, for switchBoxD you can set 0 or 1

<img src="https://raw.githubusercontent.com/d4m/hassio_components/master/blebox_switchbox.png" />

## Blebox wLightBox
__To enable this switch, add the following lines to your configuration.yaml file:__
```
light:
  - platform: blebox_wlightbox
    host: IP_ADDRESS
```
__Configuration variables:__
* __host__ (*Required*): The IP address of your wLightBox, eg. 192.168.1.32
* __name__ (*Optional*): The name to use when displaying this switch. If not set, will be used the device name

<img src="https://raw.githubusercontent.com/d4m/hassio_components/master/blebox_wlightbox1.png" />
<img src="https://raw.githubusercontent.com/d4m/hassio_components/master/blebox_wlightbox2.png" height="500" />
