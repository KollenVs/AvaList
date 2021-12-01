import time
import random
from modules.location import Location
import modules.notify as notify
from modules.location import refresh_avatar, get_city_info, gen_plr


class_name = "Work"
GARDEN_AWARDS = ["skill", "water", "clay", "peaceOfWood"]
GARBAGE_AWARDS = ["phial", "bigPhial", "wrappingPaper", "peaceOfIron"]


class Work(Location):
    prefix = "w"

    def __init__(self, server):
        super().__init__(server)
        self.kicked = {}
        self.server = server
        self.commands.update({"gr": self.get_room})

    async def get_room(self, msg, client):
        room = f"work_{msg[2]['wid']}_"
        if client.room:
            await self.leave_room(client)
        await self.join_room(client, room)
        ws = {"wid": msg[2]["wid"], "s": random.randint(1, 10000),
              "sttm": int(time.time())}
        if msg[2]["wid"] == "schoolAvataria":
            ws.update({"st": "schoolAvataria", "lvl": 0, "cqc": 5, "cac": 0,
                       "bqc": 0, "awds": [], "wac": 0, "pts": 0,
                       "sid": "sha1"})
        elif msg[2]["wid"] == "garden":
            sid = random.choice(["gd1", "gd2", "gd3"])
            ws.update({"st": "service", "si": [], "sid": sid})
        elif msg[2]["wid"] == "garbage":
            sid = random.choice(["gb1", "gb2"])
            ws.update({"st": "pick", "li": [], "sid": sid})
        await client.send(["w.gr", {"rid": client.room,
                                    "ws": ws}])

    async def room(self, msg, client):
        subcommand = msg[1].split(".")[2]
        if subcommand == "si":  # serviced items
            award = []
            while True:
                if random.random() < 0.8:
                    break
                item = random.choice(GARDEN_AWARDS)
                await self.server.inv[client.uid].add_item(item, "lt", 1)
                item = random.choice(GARBAGE_AWARDS)
                await self.server.inv[client.uid].add_item(item, "lt", 1)
                award.append({"c": 1, "iid": "", "tid": item})
            if award:
                await client.send(["lt.drp", {"itms": award}])
            await client.send(["w.r.si", {"itm": {"tm": int(time.time()),
                                                  "oid": msg[2]["oid"]}}])
            rcr = [1, 10, 15, 20, 35, 50, 80, 100, 150, 300, 500, 700, 1000]
            rc = random.choice(rcr)
            await self.server.redis.incrby(f"id:{client.uid}:slvr", rc)
            await self.server.redis.incrby(f"id:{client.uid}:pgrdnr", 1)
            await refresh_avatar(client, self.server)
            await gen_plr(client, self.server)
            await notify.update_resources(client, self.server)
        elif subcommand == "pi":  # pick item
            await self.server.redis.incrby(f"id:{client.uid}:slvr", 100)
            await client.send(["w.r.pi", {"itm": msg[2]["itm"]}])
            await notify.update_resources(client, self.server)
        elif subcommand == "rs":  # reset session
            await client.send(["w.r.rs", {"scs": True}])
        await super().room(msg, client)
