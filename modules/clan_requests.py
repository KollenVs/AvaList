from modules.base_module import Module
import operator
import time 
from modules.location import gen_plr, refresh_avatar

class_name = "ClanRequests"


class ClanRequests(Module):
    prefix = "crq"

    def __init__(self, server):
        self.server = server
        self.commands = {"lrci": self.load_requests_for_clan_id, "lrui": self.load_requests_for_user_id, "crr": self.create_request, 
                         "alr": self.approve_request, "dlr": self.delete_request, "urst": self.update_requests_show_time} 

    def load_requests_for_clan_id(self, msg, client):
        r = self.server.redis
        clan_requests_list = []
        client.send(["crq.lrq", {"rqls": clan_requests_list}]) 

    def load_requests_for_user_id(self, msg, client):
        r = self.server.redis
        clan_requests_list = []
        client.send(["crq.lrq", {"rqls": clan_requests_list}])

    def create_request(self, msg, client):
        client.send(["err", {"code": 153, "message" : "", "params": ""}])

    def approve_request(self, msg, client):
        r = self.server.redis
        client.send(["crq.alr", {"rid": 1}])

    def delete_request(self, msg, client):
        r = self.server.redis
        client.send(["crq.dlr", {"rid": 1}]) 

    def update_requests_show_time(self, msg, client):
        self.load_requests_for_user_id(msg, client)      