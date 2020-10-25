# domoticz-sonoff-d1-diy

[Domoticz](https://www.domoticz.com/) plugin to support [Sonoff D1 dimmer](https://sonoff.tech/product/wifi-diy-smart-switches/d1-smart-dimmer-switch) in [Sonoff DIY mode](http://developers.sonoff.tech/d1-http-api.html).

`DIY mode` is a setting in newer Sonoff devices where the stock firmware will let you access HTTP REST API endpoints to query, and control the device. To enable the `DIY mode`, follow the steps on https://tasmota.github.io/docs/Sonoff-DIY/ . 

The plugin will show up as a Hardware option in Domoticz. At the moment each D1 will need a separate Hardware added - kinda makes sense, given they are all actually different and separate physical pieces, plus because the IP addresses need storing. If you know of a better way, I'll all open for pull requests.

