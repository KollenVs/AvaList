from modules.base_module import Module
from lxml import etree
import binascii
import struct
import protocol

class_name = "Descriptor"

class Descriptor(Module):
    prefix = "dscr"

    def __init__(self, server):
        self.server = server
        self.commands = {"init": self.init_descriptors, "load": self.load_descriptors}
        self.outsideLocations = self.parse_outside_locations_descriptor()
        self.data = None
        self.init_data()

    async def load_descriptors(self, msg, client):
        await client.send(['dscr.ldd', {"init": False, "tgc20module": [{"scls": [{"pltf": "vkontakte", "scurl": "https://vk.com/avataryaclub", "urlid": "tgc20.socialLink"}], "dwnurl": "https://tortuga.games/tgc/", "dwnurlst": "tgc20.downloadLink", "awdp": 100, "awdpc": "100 рублей", "trid": "tgcClient", "tracttm": "432000"}]}])
        
    def init_data(self):
        self.data = struct.pack(">b", 34)
        self.data += protocol.encodeArray(self.message())
        self.data = self._make_header(self.data) + self.data
        
    def _make_header(self, msg):
        header_length = 1
        mask = 0
        mask |= (1 << 3)
        header_length += 4
        buf = struct.pack(">i", len(msg)+header_length)
        buf += struct.pack(">B", mask)
        buf += struct.pack(">I", binascii.crc32(msg))
        return buf    
        
    def parse_outside_locations_descriptor(self):
        root = etree.parse("files/outsideLocations.xml").getroot()
        locations = []
        for location in root.findall(".//location"):
            locationConfig = {}
            locationConfig["id"] = location.attrib["id"]
            locationConfig["zid"] = location.attrib["zoneId"]
            locationConfig["drid"] = location.attrib["defaultRoomId"]
            locationConfig["ldc"] = location.attrib["loadingContent"]
            rooms = []
            for room in location.findall(".//room"):
                roomConfig = {"vip": False, "ml": 0}
                roomConfig["id"] = room.attrib["id"]
                roomConfig["uc"] = room.attrib["map"]
                roomConfig["bgs"] = room.attrib["backgroundSound"]
                roomConfig["dc"] = room.attrib["dresscode"]
                rooms.append(roomConfig)
            locationConfig["rms"] = rooms
            locations.append(locationConfig)
        return locations 

    async def init_descriptors(self, msg, client):
        if client.drop:
            return
        try:
            client.writer.write(self.data)
            await client.writer.drain()
        except (BrokenPipeError, ConnectionResetError, AssertionError,
                TimeoutError, OSError, AttributeError):
            client.writer.close()
            
    def message(self):
        return ['dscr.ldd', {"init": True, "outsideLocations": self.outsideLocations, "clths": []}]