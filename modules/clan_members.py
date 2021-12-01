from modules.base_module import Module
import operator
import time 
from modules.location import gen_plr, refresh_avatar
class_name = "ClanMembers"


class ClanMembers(Module):
    prefix = "clmb"

    def __init__(self, server):
        self.server = server
        self.commands = {"chr": self.change_member_role, "lvc": self.leave_clan_member,
                         "rmm": self.remove_clan_member}

    def change_member_role(self, msg, client):
        r = self.server.redis
        uid = int(msg[2]["uid"]) 
        role = int(msg[2]["rl"])
        pin_code = 0
        if role == 3:
            pin_code = int(msg[2]["pc"])
        user_data = self.server.get_user_data(client.uid) 
        cid = user_data["clan_id"]  
        current_clan = self.server.modules["cln"].get_clan(cid)    
        members = r.smembers(f"clans:{cid}:m")        
        if role == 3 and pin_code != get_clan(cid)["pin"]:
            return client.send(["cln.err", {"code": 102}])  
        r.set(f"clans:{cid}:m:{uid}:role", role)
        for tmp in self.server.online.copy():
            if not tmp.uid in members:
                continue
            tmp.send(["cln.ucm", {"cmr": {"uid": uid, "cid": cid, "rl": role, "jd": 0, "ap": 0, "ccn": 0, "cam": {}, "ccm": {}}}])
            ci = gen_plr(tmp, self.server)["ci"]
            tmp.send(["ntf.ci", {"ci": ci}])
            tmp.send(["ntf.cli", {"cli": {"cid": cid, "ctl": current_clan["name"], "crl": 3, "clv": current_clan["lvl"],
                                 "acv": 0, "icn": current_clan["icon"], "crst": int(time.time()), "tg": current_clan["tag"]}}])

    def leave_clan_member(self, msg, client):
        r = self.server.redis
        user_data = self.server.get_user_data(client.uid) 
        cid = user_data["clan_id"] 
        current_clan = self.server.modules["cln"].get_clan(cid)        
        members = r.smembers(f"clans:{cid}:m") 
        r.delete(f"clans:{cid}:m:{client.uid}")
        r.delete(f"clans:{cid}:m:{client.uid}:role")           
        r.delete(f"id:{client.uid}:clan_id")
        for tmp in self.server.online.copy():
            if not tmp.uid in members:
                continue
            tmp.send(["clmb.lvc", {"uid": client.uid}])
            tmp.send(["clmb.rmm", {"uid": client.uid}])
            ci = gen_plr(tmp, self.server)["ci"]
            tmp.send(["ntf.ci", {"ci": ci}])
            tmp.send(["ntf.cli", {"cli": {"cid": cid, "ctl": current_clan["name"], "crl": 3, "clv": current_clan["lvl"],
                                 "acv": 0, "icn": current_clan["icon"], "crst": int(time.time()), "tg": current_clan["tag"]}}])            

    def remove_clan_member(self, msg, client):
        r = self.server.redis
        uid = int(msg[2]["uid"]) 
        user_data = self.server.get_user_data(client.uid) 
        cid = user_data["clan_id"]
        current_clan = self.server.modules["cln"].get_clan(cid)        
        members = r.smembers(f"clans:{cid}:m") 
        role = r.get(f"clans:{cid}:m:{client.uid}:role")        
        if int(role) < 2:
            return client.send(["cln.err", {"code": 102}])  
        r.delete(f"clans:{cid}:m:{uid}")
        r.delete(f"clans:{cid}:m:{uid}:role")           
        r.delete(f"id:{uid}:clan_id")
        for tmp in self.server.online.copy():
            if not tmp.uid in members:
                continue
            tmp.send(["clmb.lvc", {"uid": client.uid}])
            tmp.send(["clmb.rmm", {"uid": client.uid}])
            ci = gen_plr(tmp, self.server)["ci"]
            tmp.send(["ntf.ci", {"ci": ci}])
            tmp.send(["ntf.cli", {"cli": {"cid": cid, "ctl": current_clan["name"], "crl": 3, "clv": current_clan["lvl"],
                      "acv": 0, "icn": current_clan["icon"], "crst": int(time.time()), "tg": current_clan["tag"]}}])            