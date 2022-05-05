from modules.base_module import Module
import time
import random
import vk_api

class_name = "Mobile"

token = ""
 
vk = vk_api.VkApi(token=token)
 
vk._auth_token()

MESSAGE_AD_PRICE = int(3)

class Mobile(Module):
    prefix = "mb"

    def __init__(self, server):
        self.server = server
        self.commands = {"mkslf": self.make_selfie,
                         "smad": self.send_mobile_ad,
                         "sma": self.save_mobile_appearance, "gtmms": self.get_messages, "sdmm": self.send_message,
                         "rmmm": self.remove_message, "rmmmsdg": self.remove_dialog}

    async def remove_dialog(self, msg, client):
        uid = msg[2]["uid"]
        pipe = self.server.redis.pipeline()
        for messageId in await self.server.redis.smembers(f"id:{client.uid}:mobile_dialogs:{uid}"):
            pipe.delete(f"id:{client.uid}:mobile_dialogs:{uid}:{messageId}")
            pipe.srem(f"id:{client.uid}:mobile_dialogs", uid)
        for messageId in await self.server.redis.smembers(f"id:{uid}:mobile_dialogs:{client.uid}"):
            pipe.delete(f"id:{uid}:mobile_dialogs:{uid}:{messageId}")
            pipe.srem(f"id:{uid}:mobile_dialogs", client.uid)
        await pipe.execute()        

    async def remove_message(self, msg, client):
        message = msg[2]["ms"]
        messageId = message["dt"]
        recipient = message["rid"]
        pipe = self.server.redis.pipeline()
        pipe.srem(f"id:{client.uid}:mobile_dialogs:{recipient}", messageId)
        pipe.srem(f"id:{recipient}:mobile_dialogs:{client.uid}", messageId)
        pipe.delete(f"id:{client.uid}:mobile_dialogs:{recipient}:{messageId}")
        pipe.delete(f"id:{recipient}:mobile_dialogs:{client.uid}:{messageId}")
        await pipe.execute()
        if await self.server.redis.scard(f"id:{client.uid}:mobile_dialogs:{recipient}") <= 0:
            await self.server.redis.srem(f"id:{client.uid}:mobile_dialogs", recipient)
        if await self.server.redis.scard(f"id:{recipient}:mobile_dialogs:{client.uid}") <= 0:
            await self.server.redis.srem(f"id:{recipient}:mobile_dialogs", client.uid)

    async def send_message(self, msg, client):
        message = msg[2]["ms"]
        message["sid"] = client.uid
        recipient = message["rid"]
        text = message["txt"].strip()
        if message["sid"] == recipient:
            client.writer.close()
            return
        current_time = int(time.time()) + random.randint(1, 5)
        message["dt"] = current_time
        messageId = current_time
        pipe = self.server.redis.pipeline()
        pipe.sadd(f"id:{client.uid}:mobile_dialogs", recipient)
        pipe.sadd(f"id:{recipient}:mobile_dialogs", client.uid)
        pipe.sadd(f"id:{client.uid}:mobile_dialogs:{recipient}", messageId)
        pipe.sadd(f"id:{recipient}:mobile_dialogs:{client.uid}", messageId)
        pipe.rpush(f"id:{client.uid}:mobile_dialogs:{recipient}:{messageId}", client.uid, recipient, current_time, text)
        pipe.rpush(f"id:{recipient}:mobile_dialogs:{client.uid}:{messageId}", client.uid, recipient, current_time, text)
        pipe.set(f"id:{recipient}:mobile:new_messages_count", "1")
        await pipe.execute()
        if recipient in self.server.online.copy():
            message["nw"] = True
            await self.server.online[recipient].send(["mb.sdmm", {"ms": message}])
        message["nw"] = False
        await client.send(["mb.sdmm", {"ms": message}])

    async def get_messages(self, msg, client):
        uid = msg[2]["uid"]
        if await self.server.redis.get(f"id:{client.uid}:mobile:new_messages_count"):
            await self.server.redis.delete(f"id:{client.uid}:mobile:new_messages_count")
            await client.send(["ntf.mbm", {"mb": await self.get_mobile_appearance(client.uid)}])
        if not uid:
            return await self.get_dialogs(client)
        if not await self.server.redis.sismember(f"id:{client.uid}:mobile_dialogs", uid):
            return await client.send(["mb.gtmms", {"uid": uid, "ml": []}])
        messages = []
        for messageId in await self.server.redis.smembers(f"id:{client.uid}:mobile_dialogs:{uid}"):
            inf = await self.server.redis.lrange(f"id:{client.uid}:mobile_dialogs:{uid}:{messageId}", 0, -1)
            if not inf:
                await self.server.redis.srem(f"id:{client.uid}:mobile_dialogs", uid)
                await self.server.redis.delete(f"id:{client.uid}:mobile_dialogs:{uid}:{messageId}")
                continue
            sender = inf[0]
            recipient = inf[1]
            date = inf[2]
            text = inf[3]
            messages.append({"sid": sender, "rid": recipient, "dt": date, "nw": False, "txt": text})
        await client.send(["mb.gtmms", {"uid": uid, "ml": messages}])

    async def get_dialogs(self, client):
        messages = []
        for uid in await self.server.redis.smembers(f"id:{client.uid}:mobile_dialogs"):
            for messags in await self.server.redis.smembers(f"id:{client.uid}:mobile_dialogs:{uid}"):
                messageId = messags
            inf = await self.server.redis.lrange(f"id:{client.uid}:mobile_dialogs:{uid}:{messageId}", 0, -1)
            if not inf:
                await self.server.redis.srem(f"id:{client.uid}:mobile_dialogs", uid)
                await self.server.redis.delete(f"id:{client.uid}:mobile_dialogs:{uid}:{messageId}")
                continue
            sender = inf[0]
            recipient = inf[1]
            date = inf[2]
            text = inf[3]
            messages.append({"sid": sender, "rid": recipient, "dt": date, "nw": False, "txt": text})
        await client.send(["mb.gtmms", {"uid": None, "ml": messages}])

    async def make_selfie(self, msg, client):
        amount = 1
        if msg[2]["stg"]:
            amount += 1
        if not await self.server.inv[client.uid].take_item("film", amount):
            return
        cnt = await self.server.redis.lindex(f"id:{client.uid}:items:film", 1)
        if cnt:
            cnt = int(cnt)
        else:
            cnt = 0
        await client.send(["ntf.inv", {"it": {"c": cnt, "lid": "",
                                              "tid": "film"}}])
        await client.send(["mb.mkslf", {"sow": client.uid,
                                        "stg": msg[2]["stg"],
                                        "zm": msg[2]["zm"]}])
        if msg[2]["stg"]:
            if msg[2]["stg"] in self.server.online:
                tmp = self.server.online[msg[2]["stg"]]
                await tmp.send(["mb.mkslf", {"sow": client.uid, "stg": tmp.uid,
                                             "zm": msg[2]["zm"]}])

    async def send_mobile_ad(self, msg, client):
        user_data = await self.server.get_user_data(client.uid)
        if user_data["gld"] < MESSAGE_AD_PRICE:
            await client.send(["err", {"code": 101, "message": "", "params": {}}])
            return
        await self.server.redis.decrby(f"id:{client.uid}:gld", MESSAGE_AD_PRICE)
        await client.send(["ntf.res", {"res": {"gld": user_data["gld"] - MESSAGE_AD_PRICE,
                                         "slvr": user_data["slvr"],
                                         "enrg": user_data["enrg"],
                                         "emd": user_data["emd"]}}])
        mobile_ad = msg[2]["mad"]
        await client.send(["mb.smad", {"uid": client.uid, "mad": mobile_ad}])

    async def save_mobile_appearance(self, msg, client):
        skin = msg[2]["mb"]["sk"]
        accessory = msg[2]["mb"]["ac"]
        ringtone = msg[2]["mb"]["rt"]
        if skin not in self.server.game_items["game"]:
            return
        if accessory not in self.server.game_items["game"]:
            await self.server.redis.delete(f"id:{client.uid}:mobile_ac")
        else:
            if not await self.server.inv[client.uid].get_item(accessory):
                shop = self.server.modules["sh"]
                if not await shop.buy(client, accessory):
                    return
            await self.server.redis.set(f"id:{client.uid}:mobile_ac",
                                        accessory)
        if ringtone not in self.server.game_items["game"]:
            await self.server.redis.delete(f"id:{client.uid}:mobile_rt")
        else:
            if not await self.server.inv[client.uid].get_item(ringtone):
                shop = self.server.modules["sh"]
                if not await shop.buy(client, ringtone):
                    return
            await self.server.redis.set(f"id:{client.uid}:mobile_rt",
                                        ringtone)
        if not await self.server.inv[client.uid].get_item(skin):
            shop = self.server.modules["sh"]
            if not await shop.buy(client, skin):
                return
        await self.server.redis.set(f"id:{client.uid}:mobile_skin", skin)
        await client.send(["ntf.mbm", {"mb": {"ac": accessory, "rt": ringtone,
                                              "sk": skin, "nmc": 0}}])
        await client.send(["mb.sma", {}])
