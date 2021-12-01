from modules.base_module import Module
import random

class_name = "FirstApril2020"


class FirstApril2020(Module):
	prefix = "fa20"

	def __init__(self, server):
		self.server = server
		self.commands = {"bs": self.buy_smiles, "bi": self.buy_item, "mph": self.make_photo}
		self.config = server.parser.parse_fa20()

	async def get_info(self, uid, client=None):
		pipe = self.server.redis.pipeline()
		pipe.incrby(f"id:{uid}:fa20:smiles", 0)
		pipe.incrby(f"id:{uid}:fa20:total_smiles", 0)
		pipe.incrby(f"id:{uid}:fa20:cakes", 0)
		pipe.incrby(f"id:{uid}:fa20:hat", 0)
		pipe.incrby(f"id:{uid}:fa20:glass", 0)
		pipe.incrby(f"id:{uid}:fa20:complete", 0)
		pipe.get(f"id:{uid}:fa20:hat_type")
		pipe.get(f"id:{uid}:fa20:glass_type")
		result = await pipe.execute()
		info = {"mi": "firstApril2020", "smlcnt": result[0], "ttlsmlcnt": 2000 if result[1] >= 2000 else result[1], "ckscnt": 999, "htcnt": 999, "glsscnt": 999, "pct": bool(result[5]), "htp": result[6], "gtp": result[7]}
		if client:
			await client.send(["fa20.ui", {"inf": info}])
			await client.send(["ntf.mifv", {"mifvr": {"firstApril2020": info}}])
			await self.server.refresh_avatar(client)
		return info
		
	async def buy_smiles(self, msg, client):
		pack_id = msg[2]["spid"]
		if not pack_id or pack_id not in self.config["packs"] or not self.config["packs"][pack_id]:
			return
		pack_count = int(msg[2]["spcnt"])
		smiles_count = self.config["packs"][pack_id]["smiles"] * pack_count
		gold_price = self.config["packs"][pack_id]["price"] * pack_count
		if await self.server.redis.incrby(f"id:{client.uid}:gld", 0) < gold_price:
			return
		await self.server.redis.decrby(f"id:{client.uid}:gld", gold_price)
		await self.server.redis.incrby(f"id:{client.uid}:fa20:smiles", smiles_count)
		await self.server.redis.incrby(f"id:{client.uid}:fa20:total_smiles", smiles_count)
		await client.send(["ntf.res", {"res": await self.server.get_resources(client.uid)}])
		await client.send(["fa20.bs", {"stc": smiles_count}])
		await self.get_info(client.uid, client=client)
			
	async def buy_item(self, msg, client):
		item = msg[2]["tpid"]
		if not item or item not in self.config["items"] or not self.config["items"][item]:
			return
		count = int(msg[2]["cnt"])
		type_ = self.config["items"][item]["type"]
		price = self.config["items"][item]["price"] * count
		info = await self.get_info(client.uid, client=client)
		if info["smlcnt"] < price:
			return
		await self.server.redis.decrby(f"id:{client.uid}:fa20:smiles", price)
		if type_ == "clothes":
			await self.server.inv[client.uid].add_item(item, "cls")
			await self.server.inv[client.uid].change_wearing(item, True)
		elif type_ == "furniture":
			await self.server.inv[client.uid].add_item(item, "frn", count)
		elif type_ == "clothesSet":
			if await self.server.redis.incrby(f"id:{client.uid}:appearance:gender", 0) == 1:
				gender = "boy"
			else:
				gender = "girl"
			ctp = await self.server.redis.get(f"id:{client.uid}:wearing")
			for cloth in await self.server.redis.smembers(f"id:{client.uid}:{ctp}"):
				await self.server.inv[client.uid].change_wearing(cloth, False)
			for cloth in self.server.modules["a"].sets[gender][item]:
				if await self.server.redis.sismember(f"id:{client.uid}:items", cloth):
					continue
				await self.server.inv[client.uid].add_item(cloth, "cls")
				await self.server.inv[client.uid].change_wearing(cloth, True)
		await self.server.modules["a"].update_crt(client.uid)
		clothes = await self.server.get_clothes(client.uid, type_=2)
		inv = self.server.inv[client.uid].get()
		resources = await self.server.get_resources(client.uid)
		cloth_rating = await self.server.redis.incrby(f"id:{client.uid}:crt", 0)
		await self.get_info(client.uid, client=client)
		await client.send(["fa20.bi", {"tpid": item, "cnt": count, "clths": clothes, "inv": inv, "res": resources, "crt": cloth_rating}])
			
	async def make_photo(self, msg, client):
		amount = 5
		if not await self.server.inv[client.uid].take_item("film", amount):
			return
		await client.send(["ntf.inv", {"it": {"c": await self.server.inv[client.uid].get_item("film"), "lid": "", "tid": "film"}}])
		await client.send(["fa20.mph", {}])