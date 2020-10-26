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
    oustandingPings = 0
    connectRetry = 3

    def __init__(self):
        return

    def query_status(self, Connection):
        Connection.Send(
            {
                "Verb": "POST",
                "URL": "/zeroconf/info",
                "Headers": {"Content-Type": "application/json"},
                "Data": json.dumps({"data": ""}),
            }
        )

    def onStart(self):
        if Parameters["Mode6"] != "0":
            Domoticz.Debugging(int(Parameters["Mode6"]))

        self.httpConn = Domoticz.Connection(
            Name=Parameters["Address"],
            Transport="TCP/IP",
            Protocol="HTTP",
            Address=Parameters["Address"],
            Port=Parameters["Mode1"],
        )
        self.httpConn.Connect()

    def onStop(self):
        Domoticz.Log("onStop - Plugin is stopping.")

    def onConnect(self, Connection, Status, Description):
        if Status == 0:
            Domoticz.Debug("Connected to Sonoff DIY interface")
            self.query_status(Connection)
        else:
            Domoticz.Log(
                "Failed to connect ("
                + str(Status)
                + ") to: "
                + Parameters["Address"]
                + ":"
                + Parameters["Mode1"]
                + " with error: "
                + Description
            )

    def onMessage(self, Connection, Data):
        try:
            strData = Data["Data"].decode("utf-8", "ignore")
            strData = json.loads(strData)
            # Status = int(Data["Status"])
            Domoticz.Debug("Parsed JSON:" + json.dumps(strData))
            self.oustandingPings = self.oustandingPings - 1
        except:
            Domoticz.Error("Failed to parse response as JSON" + strData)
            return

        if "data" not in strData:
            Domoticz.Debug("`data` missing from Parsed JSON")
            return

        data = strData["data"]

        # skip these messages, they are not status updates
        if "deviceid" not in data:
            Domoticz.Debug("`deviceid` missing from Parsed JSON")
            return
        # create new devices if the don't exist just yet
        existing_devices = [d.DeviceID for d in Devices.values()]
        if data["deviceid"] not in existing_devices:
            # I guess brightness is only present in a dimmer
            # I could be wrong
            if "brightness" in data:
                Domoticz.Device(
                    Name=data["deviceid"],
                    Unit=1,
                    Type=244,
                    Subtype=73,
                    Switchtype=7,
                    DeviceID=data["deviceid"],
                ).Create()

        # now the device certainly exists, so find it
        device = None
        for index, d in Devices.items():
            if data["deviceid"] == d.DeviceID:
                device = Devices[index]

        if not device:
            Domoticz.Error("something is wrong: the device was not found?!")
            return

        if "switch" in data and "brightness" in data:
            if data["switch"] == "on":
                n_value = 1
            else:
                n_value = 0
            s_value = str(data["brightness"])

            device.Update(
                nValue=n_value,
                sValue=s_value,
                SignalLevel=int((1 / (-1 * data["signalStrength"])) * 100),
                BatteryLevel=100,
            )

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug(
            "onCommand called for Unit "
            + str(Unit)
            + ": Parameter '"
            + str(Command)
            + "', Level: "
            + str(Level)
        )

        # in case of 'on' and 'off', the dimmable endpoint doesn't seem to respect the switch status
        if Command.lower() in ["off", "on"]:
            url = "/zeroconf/switch"
            data = {"switch": Command.lower()}
        else:
            url = "/zeroconf/dimmable"
            if Level > 0:
                switch = "on"
            else:
                switch = "off"
            data = {"switch": switch, "brightness": Level}
        self.httpConn.Send(
            {
                "Verb": "POST",
                "URL": url,
                "Headers": {"Content-Type": "application/json"},
                "Data": json.dumps({"deviceid": "", "data": data}),
            }
        )

    def onDisconnect(self, Connection):
        Domoticz.Log(
            "onDisconnect called for connection to: "
            + Connection.Address
            + ":"
            + Connection.Port
        )

    def onHeartbeat(self):
        try:
            if self.httpConn and self.httpConn.Connected():
                self.oustandingPings = self.oustandingPings + 1
                if self.oustandingPings > 6:
                    Domoticz.Log(
                        "Too many outstanding connection issues forcing disconnect."
                    )
                    self.httpConn.Disconnect()
                    self.nextConnect = 0
                else:
                    self.query_status(self.httpConn)
            else:
                # if not connected try and reconnected every 3 heartbeats
                self.oustandingPings = 0
                self.nextConnect = self.nextConnect - 1
                if self.nextConnect <= 0:
                    self.nextConnect = 3
                    self.httpConn.Connect()
            return True
        except:
            Domoticz.Log(
                "Unhandled exception in onHeartbeat, forcing disconnect."
            )
            self.onDisconnect(self.httpConn)
            self.httpConn = None

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
    _plugin.onNotification(
        Name, Subject, Text, Status, Priority, Sound, ImageFile
    )


def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


# Generic helper functions
def LogMessage(Message):
    if Parameters["Mode6"] == "File":
        f = open(Parameters["HomeFolder"] + "http.html", "w")
        f.write(Message)
        f.close()
        Domoticz.Log("File written")


def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
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
    if level == 0:
        Domoticz.Debug("HTTP Details (" + str(len(httpResp)) + "):")
    indentStr = ""
    for x in range(level):
        indentStr += "----"
    if isinstance(httpResp, dict):
        for x in httpResp:
            if not isinstance(httpResp[x], dict) and not isinstance(
                httpResp[x], list
            ):
                Domoticz.Debug(
                    indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'"
                )
            else:
                Domoticz.Debug(indentStr + ">'" + x + "':")
                DumpHTTPResponseToLog(httpResp[x], level + 1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            Domoticz.Debug(indentStr + "['" + x + "']")
    else:
        Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")
