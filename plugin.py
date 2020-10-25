__author__ = "Peter Molnar"
__maintainer__ = "https://petermolnar.net"
__email__ = "mail@petermolnar.net"

"""
<plugin key="sonoff_d1_diy" name="Sonoff D1 Dimmer DIY connector" version="0.1">
    <description>
        <h2>Sonoff D1 Dimmer DIY connector</h2><br/>
    </description>
    <params>
        <param field="Address" label="Local IP Address" width="200px" required="true" default="192.168.0.1"/>
        <param field="Mode1" label="Port" width="200px" default="8081"/>
        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0" default="true" />
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Python" value="18"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import json

class BasePlugin:
    httpConn = None
    runAgain = 6
    disconnectCount = 0

    def __init__(self):
        return

    def onStart(self):
        if Parameters["Mode6"] != "0":
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()

        self.httpConn = Domoticz.Connection(
            Name= Parameters["Address"],
            Transport="TCP/IP",
            Protocol="HTTP",
            Address=Parameters["Address"],
            Port=Parameters["Mode1"]
        )
        self.httpConn.Connect()

    def onStop(self):
        Domoticz.Log("onStop - Plugin is stopping.")

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("Connected to Sonoff DIY interface")
            Connection.Send({
                'Verb' : 'POST',
                'URL'  : '/zeroconf/info',
                'Headers' : {
                    'Content-Type': 'application/json'
                },
                'Data': json.dumps({
                    'data': ''
                })
            })
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+":"+Parameters["Mode1"]+" with error: "+Description)

    def onMessage(self, Connection, Data):
        strData = Data["Data"].decode("utf-8", "ignore")
        Status = int(Data["Status"])
        try:
            strData = json.loads(strData)
            Domoticz.Log("Parsed JSON:" + json.dumps(strData))
            if "data" in strData:
                if (len(Devices) == 0) and "deviceid" in strData["data"]:
                    Domoticz.Device(Name=strData["data"]["deviceid"], Unit=1, Type=244, Subtype=73, Switchtype=7).Create()
                if "switch" in strData["data"] and "brightness" in strData["data"]:
                    n_value = 1 if strData["data"]["switch"] == 'on' else 0
                    s_value = str(strData["data"]["brightness"])
                    Devices[1].Update(
                        nValue=n_value,
                        sValue=s_value
                        #SignalLevel=strData["data"]["signalStrength"],
                        #BatteryLevel=100
                    )
        except:
            Domoticz.Log("Failed to parse response as JSON" + strData)
            return

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        if "Off" == Command or "On" == Command:
            url = "/zeroconf/switch"
            data = {
                "switch": Command.lower()
            }
        else:
            url = "/zeroconf/dimmable"
            if Level > 0:
                switch = "on"
            else:
                switch = "off"
            data = {
                "switch": switch,
                "brightness": Level
            }
        self.httpConn.Send({
            'Verb' : 'POST',
            'URL'  : url,
            'Headers' : {
                'Content-Type': 'application/json'
            },
            'Data': json.dumps({
                "deviceid": "",
                "data": data
            })
        })

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called for connection to: "+Connection.Address+":"+Connection.Port)

    def onHeartbeat(self):
        if (self.httpConn != None and (self.httpConn.Connecting() or self.httpConn.Connected())):
            Domoticz.Debug("onHeartbeat called, Connection is alive.")
            self.httpConn.Send({
                'Verb' : 'POST',
                'URL'  : '/zeroconf/info',
                'Headers' : {
                    'Content-Type': 'application/json'
                },
                'Data': json.dumps({
                    'data': ''
                })
            })
        else:
            self.runAgain = self.runAgain - 1
            if self.runAgain <= 0:
                if (self.httpConn == None):
                    self.onStart()
                self.runAgain = 6
            else:
                Domoticz.Debug("onHeartbeat called, connection is dead")

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def LogMessage(Message):
    if Parameters["Mode6"] == "File":
        f = open(Parameters["HomeFolder"]+"http.html","w")
        f.write(Message)
        f.close()
        Domoticz.Log("File written")

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def DumpHTTPResponseToLog(httpResp, level=0):
    if (level==0): Domoticz.Debug("HTTP Details ("+str(len(httpResp))+"):")
    indentStr = ""
    for x in range(level):
        indentStr += "----"
    if isinstance(httpResp, dict):
        for x in httpResp:
            if not isinstance(httpResp[x], dict) and not isinstance(httpResp[x], list):
                Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")
            else:
                Domoticz.Debug(indentStr + ">'" + x + "':")
                DumpHTTPResponseToLog(httpResp[x], level+1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            Domoticz.Debug(indentStr + "['" + x + "']")
    else:
        Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")
