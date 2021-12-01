import logging
import time
from modules.base_module import Module
from client import Client
import common
import asyncio


class Location(Module):
	def __init__(self, server):
		self.server = server
		self.commands = {"r": self.room}
		self.refresh_cooldown = {}
		self.actions = {"ks": "kiss", "hg": "hug", "gf": "giveFive",
						"k": "kickAss", "sl": "slap", "lks": "longKiss",
						"hs": "handShake", "aks": "airKiss"}

	async def room(self, msg, client):
		user_data = await self.server.get_user_data(client.uid)
		subcommand = msg[1].split(".")[2]
		if subcommand in ["u", "m", "k", "sa", "sl", "bd", "lks", "hs",
						  "ks", "hg", "gf", "aks"]:
			msg.pop(0)
			if msg[1]["uid"] != client.uid:
				return
			if "at" in msg[1]:
				prefix = msg[0].split(".")[0]
			if subcommand == "u":
				client.position = (msg[1]["x"], msg[1]["y"])
				client.direction = msg[1]["d"]
				if "at" in msg[1]:
					client.action_tag = msg[1]["at"]
				else:
					client.action_tag = ""
				client.state = msg[1]["st"]
			elif subcommand in self.actions:
				action = self.actions[subcommand]
				uid = msg[1]["tmid"]
				rl = self.server.modules["rl"]
				link = await rl.get_link(client.uid, uid)
				if link:
					await rl.add_progress(action, link)
				acti = await self.server.redis.set(f"id:{client.uid}:act",
									user_data["act"] + 1)
				await client.send(["acmr.adac", {"vl": 1}])
				clanId = await self.server.redis.get(f"id:{client.uid}:clan")
				loop = asyncio.get_event_loop()
				if clanId:
					for uid in await self.server.redis.smembers(f"clans:{clanId}:m"):
						if uid in self.server.online:
							tmp = self.server.online[uid]
							loop.create_task(tmp.send(["ca.uma", {"uid": client.uid, "cid": clanId, "cmam": {"ap": acti, "cid": clanId, "ah": []}}]))
			online = self.server.online
			try:
				room = self.server.rooms[client.room].copy()
			except KeyError:
				return
			for uid in room:
				try:
					tmp = online[uid]
				except KeyError:
					continue
				await tmp.send(msg)
		elif subcommand == "ra":
			if client.uid in self.refresh_cooldown:
				if time.time() - self.refresh_cooldown[client.uid] < 3:
					return
			self.refresh_cooldown[client.uid] = time.time()
			await refresh_avatar(client, self.server)
		elif "tg.am" in msg[1]:
			if user_data["avaManStyle"] == msg[2]["as"] or not msg[2]["as"]:
				await self.server.redis.delete(f"id:{client.uid}:avaManStyle")
			else:
				await self.server.redis.set(f"id:{client.uid}:avaManStyle", msg[2]["as"])
			ci = await get_city_info(client.uid, self.server)
			await client.send(["ntf.ci", {"ci": ci}])
			await refresh_avatar(client, self.server)
		else:
			print(f"Command {msg[1]} not found")

	async def join_room(self, client, room):
		if room in self.server.rooms:
			self.server.rooms[room].append(client.uid)
		else:
			self.server.rooms[room] = [client.uid]
		client.room = room
		client.position = (-1.0, -1.0)
		client.action_tag = ""
		client.state = 0
		client.dimension = 4
		plr = await gen_plr(client, self.server)
		prefix = common.get_prefix(client.room)
		online = self.server.online
		new_room = self.server.rooms[room].copy()
		location_name = room.split("_")[0]
		if location_name == "canyon":
			client.canyon_lid = "l1"
			cc = await get_cc(room, self.server)
		else:
			cc = None
		for uid in new_room:
			if uid not in online:
				continue
			tmp = online[uid]
			await tmp.send([f"{prefix}.r.jn", {"plr": plr, "cc": cc}])
			await tmp.send([client.room, client.uid], type_=16)

	async def leave_room(self, client):
		if client.uid not in self.server.rooms[client.room]:
			return
		self.server.rooms[client.room].remove(client.uid)
		old_room = self.server.rooms[client.room].copy()
		if old_room:
			prefix = common.get_prefix(client.room)
			online = self.server.online
			location_name = client.room.split("_")[0]
			if location_name == "canyon":
				cc = await get_cc(client.room, self.server)
			else:
				cc = None
			for uid in old_room:
				try:
					tmp = online[uid]
				except KeyError:
					continue
				await tmp.send([f"{prefix}.r.lv", {"uid": client.uid,
												   "cc": cc}])
				await tmp.send([client.room, client.uid], type_=17)
		else:
			del self.server.rooms[client.room]
		room = client.room.split("_")
		if room[0] == "house" and room[1] == client.uid:
			await self.server.modules["h"].owner_at_house(client.uid, False)
		client.room = None


async def gen_plr(client, server):
	if isinstance(client, Client):
		uid = client.uid
	else:
		uid = client
	apprnc = await server.get_appearance(uid)
	if not apprnc:
		return None
	user_data = await server.get_user_data(uid)
	clths = await server.get_clothes(uid, type_=2)
	mobile_skin = await server.redis.get(f"id:{uid}:mobile_skin")
	mobile_accessory = await server.redis.get(f"id:{uid}:mobile_ac")
	mobile_ringtone = await server.redis.get(f"id:{uid}:mobile_rt")
	if not mobile_skin:
		mobile_skin = "whiteMobileSkin"
	plr = {"uid": uid, "apprnc": apprnc, "clths": clths,
		   "mbm": {"ac": mobile_accessory, "sk": mobile_skin,
				   "rt": mobile_ringtone},
		   "usrinf": {"rl": user_data["role"], "sid": uid}}
	bubble = await server.redis.get(f"id:{uid}:bubble")
	text_color = await server.redis.get(f"id:{uid}:tcl")
	chat_bubble = await server.redis.get(f"id:{uid}:chat_bubble")
	plr["chtdcm"] = {"bdc": bubble, "tcl": text_color, "bt": chat_bubble,
					 "spks": ["bushStickerPack", "froggyStickerPack",
							  "doveStickerPack", "jackStickerPack",
							  "catStickerPack", "sharkStickerPack", "korgiStickerPack", "octopusStickerPack"]}
	plr["mifvr"] =  {"firstApril2020": await server.modules["fa20"].get_info(uid)}
	if isinstance(client, Client):
		if await server.redis.get(f"id:{uid}:loc_disabled"):
			shlc = False
		else:
			shlc = True
		plr["locinfo"] = {"st": client.state, "s": "127.0.0.1",
						  "at": client.action_tag, "d": client.dimension,
						  "x": client.position[0], "y": client.position[1],
						  "shlc": shlc, "pl": "", "l": client.room}
	cid = await server.redis.get(f"id:{uid}:clan")
	if cid:
		clan = server.modules["cln"]
		info = await clan.get_clan(cid)
		plr["clif"] = {"tg": info["tag"], "icn": info["icon"],
					   "ctl": info["name"], "clv": info["lvl"], "cid": cid,
					   "crl": info["members"][uid]["role"]}
	else:
		plr["clif"] = None
	plr["ci"] = await get_city_info(uid, server)
	lgrdnr = await server.redis.get(f"id:{uid}:lgrdnr") # Получение уровня с работ
	if not lgrdnr:
		lgrdnr = 1
	lgrdnr = int(lgrdnr)
	pgrdnr = await server.redis.get(f"id:{uid}:pgrdnr") # Получение очков с работ
	if not pgrdnr:
		pgrdnr = 0
	pgrdnr = int(pgrdnr)
	if lgrdnr == 1: # Первый уровень в саду
		if pgrdnr >= 60:
			await server.redis.incrby(f"id:{uid}:lgrdnr", 1)
			await server.redis.set(f"id:{uid}:pgrdnr", 0)
	plr["pf"] = {"pf": {"jntr": {"tp": "jntr", "l": 1, "pgs": 0},
						"phtghr": {"tp": "phtghr", "l": 1, "pgs": 0},
						"grdnr": {"tp": "grdnr", "l": lgrdnr, "pgs": pgrdnr},
						"vsgst": {"tp": "vsgst", "l": 1, "pgs": 0}}}
	return plr


async def get_city_info(uid, server):
	user_data = await server.get_user_data(uid)
	rl = server.modules["rl"]
	relations = await server.redis.smembers(f"rls:{uid}")
	cmid = 0
	ceid = 0
	for link in relations:
		relation = await rl._get_relation(uid, link)
		if not relation:
			continue
		if relation["rlt"]["s"] // 10 == 7:
			cmid = relation["uid"]
		if relation["rlt"]["s"] // 10 == 6:
			ceid = relation["uid"]
		if ceid and cmid:
			break
	if await server.redis.get(f"id:{uid}:hide_crown"):
		show_crown = False
	else:
		show_crown = True
	psrtdcr = await server.redis.get(f"id:{uid}:psrtdcr")
	if psrtdcr:
		psrtdcr = int(psrtdcr)
	else:
		psrtdcr = 1
	snowscore = await server.redis.get(f"id:{uid}:snowscore")
	if snowscore:
		snowscore = int(snowscore)
	else:
		snowscore = 0
	plcmt = {"pc": {"snowboardRating": {"uid": 0, "ct": 2, "cid": 812,
										"cr": snowscore}}}
	ci = {"exp": user_data["exp"], "crt": user_data["crt"],
		  "hrt": user_data["hrt"], "fexp": 0, "gdc": 0, "lgt": 0,
		  "vip": user_data["premium"], "vexp": user_data["prem_time"],
		  "vsexp": user_data["prem_time"], "vsact": True, "vret": 0,
		  "vfgc": 0, "ceid": ceid, "cmid": cmid, "dr": True, "spp": 0,
		  "tts": None, "eml": None, "ys": 0, "ysct": 0, "fak": None,
		  "shcr": show_crown, "gtrfrd": 0, "strfrd": 0, "rtrtm": 0,
		  "kyktid": None, "actrt": user_data["act"], "compid": 0,
		  "actrp": 0, "actrd": 1899999999, "shousd": False, "rpt": user_data["reputation"],
		  "as": user_data["avaManStyle"], "lvt": user_data["lvt"], "lrnt": 0, "lwts": 0,
		  "skid": "iceRinkSkate3", "skrt": int(time.time()+1000000),
		  "bcld": 0, "trid": user_data["trid"], "trcd": 0, "sbid": None,
		  "sbrt": 0, "plcmt": plcmt, "pamns": {"amn": []}, "crst": 0,
		  "psrtdcr": psrtdcr, "dl": True}
	if user_data["premium"]:
		ci["actrp"] = 1
	return ci


async def refresh_avatar(client, server):
	if not client.room:
		return
	plr = await gen_plr(client, server)
	prefix = common.get_prefix(client.room)
	online = server.online
	room = server.rooms[client.room].copy()
	for uid in room:
		try:
			tmp = online[uid]
		except KeyError:
			continue
		await tmp.send([f"{prefix}.r.ra", {"plr": plr}])


async def get_cc(room, server):
	room = server.rooms[room].copy()
	online = server.online
	cc = {"cc": []}
	i = 1
	for uid in room:
		if uid not in online:
			continue
		car = await get_car(uid, server.redis)
		cc["cc"].append({'pss': [uid], 'uid': uid,
						 'ctid': car, 'gtp': '', 'sid': str(i)})
		i += 1
	return cc


async def get_car(uid, r):
	for room in await r.smembers(f"rooms:{uid}"):
		for item in await r.smembers(f"rooms:{uid}:{room}:items"):
			if "car" in item.lower() or "bike" in item.lower() or \
			   "tank" in item.lower():
				return item.split("_")[0]
	return "carPtcChrry"

