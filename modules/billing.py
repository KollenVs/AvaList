from modules.base_module import Module
import modules.notify as notify
import const

class_name = "Billing"


class Billing(Module):
    prefix = "b"

    def __init__(self, server):
        self.server = server
        self.commands = {"chkprchs": self.check_purchase,
                         "bs": self.buy_silver}

    async def check_purchase(self, msg, client):
        if not const.FREE_GOLD:
            return
        amount = int(msg[2]["prid"].split("pack")[1])
        user_data = await self.server.get_user_data(client.uid)
        gold = user_data["gld"] + amount
        await self.server.redis.set(f"id:{client.uid}:gld", gold)
        await self.server.redis.set(f"id:{client.uid}:act",
                                    user_data["act"] + 1)
        await client.send(["acmr.adac", {"vl": 1}])
        await notify.update_resources(client, self.server)
        await client.send(["b.ingld", {"ingld": amount}])

    async def buy_silver(self, msg, client):
        user_data = await self.server.get_user_data(client.uid)
        if user_data["gld"] < msg[2]["gld"]:
            return
        await self.server.redis.set(f"id:{client.uid}:gld",
                                    user_data["gld"] - msg[2]["gld"])
        await self.server.redis.set(f"id:{client.uid}:slvr",
                                    user_data["slvr"] + msg[2]["gld"] * 100)
        await notify.update_resources(client, self.server)
        await client.send(["b.inslv", {"inslv": msg[2]["gld"] * 100}])
