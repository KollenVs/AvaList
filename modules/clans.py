from modules.base_module import Module
import operator
import time 
from modules.location import gen_plr, refresh_avatar
import random

class_name = "Clans"


class Clans(Module):
    prefix = "cln"

    def __init__(self, server):
        self.server = server
        self.commands = {"crt": self.create_clan_, "grci": self.get_random_clan_ids, "lcmids": self.load_clan_models_by_ids, 
                         "dcl": self.delete_clan}

    def create_clan_(self, msg, client):
        r = self.server.redis     
        user_data = self.server.get_user_data(client.uid)
        r.set(f"id:{client.uid}:gld", user_data["gld"] - 100)
        res = {"gld": user_data["gld"] - 100, "slvr": user_data["slvr"],
               "enrg": user_data["enrg"], "emd": user_data["emd"]}
        client.send(["ntf.res", {"res": res}])
        self.create_clan(msg, client)
        
    def create_clan(self, msg, client): 
        cid = client.uid        
        clan_title = str(msg[2]["ctl"])
        clan_tag = str(msg[2]["ctg"])
        clan_icon = str(msg[2]["cin"])
        clan_room = str(msg[2]["rtid"])
        clan_pin_code = int(msg[2]["pc"])
        r = self.server.redis        
        pipe = r.pipeline()               
        pipe.set(f"clans:{cid}:id", cid)
        pipe.set(f"clans:{cid}:name", clan_title)
        pipe.set(f"clans:{cid}:tag", clan_tag)
        pipe.set(f"clans:{cid}:icon", clan_icon)
        pipe.set(f"clans:{cid}:room", clan_room)
        pipe.set(f"clans:{cid}:owner", client.uid)
        pipe.set(f"clans:{cid}:create_date", int(time.time()))
        pipe.set(f"clans:{cid}:pin", clan_pin_code) 
        pipe.set(f"clans:{cid}:lvl", 1)
        pipe.sadd(f"clans:{cid}:m", client.uid)
        pipe.set(f"id:{client.uid}:clan_id", cid)
        pipe.set(f"clans:{cid}:m:{client.uid}:role", 3)
        pipe.execute()
        created_clan = self.get_clan(cid)
        members = {}
        for member in self.server.redis.smembers(f"clans:{cid}:m"):
            role = self.server.redis.get(f"clans:{cid}:m:{member}:role")
            members[member] = {"uid": int(member), "cid": int(cid), "rl": int(role), "jd": 0, "ap": 0, "ccn": 0, "cam": None, "ccm": None}  
        client.send(["ntf.cli", {"cli": {"cid": cid, "ctl": created_clan["name"], "crl": 3, "clv": created_clan["lvl"],
                                 "acv": 0, "icn": created_clan["icon"], "crst": int(time.time()), "tg": created_clan["tag"]}}]) 
                                 
        client.send(["cln.crt", {"scs": True, "err": 0, "clm": {"cid": cid, "ttl": created_clan["name"], "lvl": created_clan["lvl"],
                                "acv": 0, "icn": created_clan["icon"], "crst": int(time.time()), "tg": created_clan["tag"], "exp": 0,
                                "crdt": created_clan["create_date"], "crid": created_clan["owner"], "st": 0, "ccn": 0, "mmbs": members,
                                "hpc": True, "pvt": False, "cinv": {}, "clrtg": 0, "ctstrd": False, "ctspls": 0}}]) 
        ci = gen_plr(client.uid, self.server)["ci"]
        client.send(["ntf.ci", {"ci": ci}]) 
        refresh_avatar(client, self.server)        

    def get_clan(self, cid):
        r = self.server.redis  	
        pipe = r.pipeline()
        pipe.get(f"clans:{cid}:name")
        pipe.get(f"clans:{cid}:tag")
        pipe.get(f"clans:{cid}:icon")
        pipe.get(f"clans:{cid}:room")
        pipe.get(f"clans:{cid}:owner")
        pipe.get(f"clans:{cid}:create_date")
        pipe.get(f"clans:{cid}:pin")
        pipe.get(f"clans:{cid}:lvl")
        result = pipe.execute() 
        if not result[5]:
            return      
        return {"name": result[0], "tag": result[1], "icon": result[2], "room": result[3],
                "owner": result[4], "create_date": result[5], "pin": result[6], "lvl": int(result[7])}
                
    def delete_clan_(self, cid): 
        r = self.server.redis
        pipe = r.pipeline()
        pipe.delete(f"clans:{cid}:name")
        pipe.delete(f"clans:{cid}:tag")
        pipe.delete(f"clans:{cid}:icon")
        pipe.delete(f"clans:{cid}:room")
        pipe.delete(f"clans:{cid}:owner")
        pipe.delete(f"clans:{cid}:create_date")
        pipe.delete(f"clans:{cid}:pin")
        pipe.delete(f"clans:{cid}:lvl")
        pipe.delete(f"clans:{cid}:m")          
                
    def get_random_clan_ids(self, msg, client):
        clan_ids = []
        max_uid = int(self.server.redis.get("uids"))
        for i in range(1, max_uid+1):
            user_data = self.server.get_user_data(i)
            if not user_data["clan_id"] and user_data["clan_id"] in clan_ids:
                continue
            clan_ids.append(int(user_data["clan_id"])) 
            random.shuffle(clan_ids)            
        client.send(["cln.grci", {"clid": msg[2]["clid"], "cids": clan_ids}])
        
    def load_clan_models_by_ids(self, msg, client):
        clan_ids = msg[2]["cids"]
        clan_models = []
        for cid in clan_ids:
            clan_id = int(cid)
            clan_info = self.get_clan(clan_id)
            if not clan_info:
                continue
            members = {}
            for member in self.server.redis.smembers(f"clans:{cid}:m"):
                role = self.server.redis.get(f"clans:{cid}:m:{member}:role")
                if not role:
                    role = 0
                members[member] = {"uid": int(member), "cid": int(cid), "rl": int(role), "jd": 0, "ap": 0, "ccn": 0, "cam": None, "ccm": None}         
            clan_models.append({"id": clan_id, "ttl": clan_info["name"], "tg": clan_info["tag"],
                                 "lvl": clan_info["lvl"], "exp": 0, "crdt": clan_info["create_date"], "crid": clan_info["owner"],
                                 "st": 0, "ccn": 0, "mmbs": members, "icn": clan_info["icon"], "hpc": True, "pvt": False,
                                 "cinv": {}, "clrtg": 0, "ctstrd": False, "ctspls": 0})
        client.send(["cln.lcmids", {"clid": msg[2]["clid"], "clms": clan_models}])  

    def delete_clan(self, msg, client):       
        r = self.server.redis           
        user_data = self.server.get_user_data(client.uid)
        cid = int(user_data["clan_id"])
        pin_code = int(msg[2]["pc"])
        clan_pin_code = int(self.get_clan(cid)["pin"])
        creator_role = r.get(f"clans:{cid}:m:{client.uid}:role")
        if not int(creator_role) == 3 or not pin_code == clan_pin_code:
            return client.send(["cln.err", {"code": 102}])                                   
        members = r.smembers(f"clans:{cid}:m")
        for member in members:
            r.delete(f"id:{int(member)}:clan_id")
        for tmp in self.server.online.copy():
            if not tmp.uid in members:
                continue          
        tmp.send(["ntf.cli", {}])              
        self.delete_clan_(cid) 
        ci = gen_plr(tmp.uid, self.server)["ci"]
        tmp.send(["ntf.ci", {"ci": ci}]) 
        refresh_avatar(tmp, self.server)     
        tmp.send(["clmb.lvc", {"uid": client.uid}])
        tmp.send(["clmb.rmv", {"cid": cid}])    
    