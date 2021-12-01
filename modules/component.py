import time, json, aiohttp, urllib.parse, logging
import random, traceback, const, asyncio, vk_api
from modules.base_module import Module
from modules.location import Location
from modules.location import refresh_avatar, get_city_info, gen_plr, get_cc
import utils.bot_common_sync

class_name = "Component"

token = "" #Токен для вк бота
 
vk = vk_api.VkApi(token=token)
 
vk._auth_token()


def get_exp(lvl):
    expSum = 0
    i = 0
    while i < lvl-1:
        i += 1
        expSum += i * 50
    return expSum

class Component(Module):
    prefix = "cp"

    def __init__(self, server):
        self.server = server
        self.commands = {"cht": self.chat, "m": self.moderation,
                         "ms": self.message}
        self.privileges = self.server.parser.parse_privileges()
        self.help_cooldown = {}
        self.ban_reasons = {1: "нецензурные выражения",
                            5: "клевета в адрес администрации/игроков",
                            6: "клевета в адрес компании/игры",
                            7: "спам или флуд",
                            8: "реклама или ссылки",
                            9: "запрещённые описания и названия",
                            10: "мат и/или оскорбления"}
        self.warning_reasons = {"1": "Манипуляции с игровым аккаунтом",
                                "2": "Махинации с игровой валютой",
                                "3": "Использование игровых ботов",
                                "4": "Использование багов игры",
                                "5": "Клевета в адрес представителей "
                                     "администрации",
                                "6": "Клевета в адрес игры",
                                "7": "Спам или флуд",
                                "8": "Реклама или ссылки",
                                "9": "Запрещённые названия",
                                "10": "Мат или оскорбления",
                                "11": "Умышленное создание трудностей",
                                "12": "Вредоносные файлы",
                                "13": "Выдача за сотрудника",
                                "14": "Попытка доступа к чужому аккаунту",
                                "15": "Введение в заблуждение администрации",
                                "16": "Обман на подарки",
                                "17": "Мошенничество",
                                "18": "Избыточное форматирование",
                                "19": "Иностранный язык"}
        self.mute = {}

    async def chat(self, msg, client):
        if not client.room:
            return
        subcommand = msg[1].split(".")[2]
        if subcommand == "sm":  # send message
            msg.pop(0)
            if client.uid in self.mute:
                time_left = self.mute[client.uid]-time.time()
                if time_left > 0:
                    return await client.send(["cp.ms.rsm", {"txt": "У вас мут на "
                                                            f"{int(time_left)}"
                                                            " секунд"}])
                else:
                    del self.mute[client.uid]
            if msg[1]["msg"]["cid"]:
                if msg[1]["msg"]["cid"].startswith("clan"):
                    r = self.server.redis
                    cid = await r.get(f"id:{client.uid}:clan")
                    for uid in await r.smembers(f"clans:{cid}:m"):
                        if uid in self.server.online:
                            await self.server.online[uid].send(msg)
                else:
                    for uid in msg[1]["msg"]["cid"].split("_"):
                        if uid in self.server.online:
                            await self.server.online[uid].send(msg)
            else:
                if "msg" in msg[1]["msg"]:
                    message = msg[1]["msg"]["msg"]
                    if len(message) > 300:
                        return await client.send(["cp.ms.rsm", {"txt": "Вы отправляете слишком длинные сообщения"}])
                    if len(message) == 0:
                        return await client.send(["cp.ms.rsm", {"txt": "Вы отправляете пустые сообщения"}])
                    if "хуй" in message or "сука" in message or "пизд" in message:
                        minutes = 10
                        self.mute[client.uid] = time.time()+minutes*60
                        await client.send(["cp.m.bccu", {"bcu": {"notes": "",
                                                  "reviewerId": "0",
                                                  "mid": "0", "id": None,
                                                  "reviewState": 1,
                                                  "userId": client.uid,
                                                  "mbt": int(time.time()*1000),
                                                  "mbd": minutes,
                                                  "categoryId": 14}}])
                        return
                    uid = msg[1]["msg"]["sid"]
                    vk.method("messages.send", {"peer_id": 609463996, "message": f"{uid} написал сообщение ({message})", "random_id": random.randint(1, 2147483647)})
                    if message.startswith("/") or message.startswith("!"):
                        try:
                            return await self.system_command(message, client)
                        except Exception:
                            print(traceback.format_exc())
                            msg = "Ошибка в синтаксисе команды, проверьте правильность"
                            await client.send(["cp.ms.rsm", {"txt": msg}])
                            return
                msg[1]["msg"]["sid"] = client.uid
                online = self.server.online
                room = self.server.rooms[client.room]
                for uid in room:
                    try:
                        tmp = online[uid]
                    except KeyError:
                        room.remove(uid)
                        continue
                    await tmp.send(msg)

    async def moderation(self, msg, client):
        subcommand = msg[1].split(".")[2]
        if subcommand == "ar":  # access request
            user_data = await self.server.get_user_data(client.uid)
            if user_data["role"] >= self.privileges[msg[2]["pvlg"]]:
                success = True
            else:
                success = False
            await client.send(["cp.m.ar", {"pvlg": msg[2]["pvlg"],
                                           "sccss": success}])
        elif subcommand == "bu":
            uid = msg[2]["uid"]
            category = msg[2]["bctr"]
            reason = msg[2]["notes"]
            return await self.ban_user(uid, category, reason, client)

    async def kick(self, client, uid, reason):
        user_data = await self.server.get_user_data(client.uid)
        if user_data["role"] < 2:
            return await self.no_permission(client)
        uid_user_data = await self.server.get_user_data(uid)
        if uid_user_data["role"] > user_data["role"]:
            return
        if uid not in self.server.online:
            return await client.send(["cp.ms.rsm", {"txt": "Игрок оффлайн"}])
        tmp = self.server.online[uid]
        tmp.writer.close()
        await client.send(["cp.ms.rsm", {"txt": "Игрок был кикнут"}])
        vk.method("messages.send", {"peer_id": 609463996, "message": f"Администратор({client.uid}) кикнул ({uid})", "random_id": random.randint(1, 2147483647)})

    async def ban_user(self, uid, category, reason, days, client):
        user_data = await self.server.get_user_data(client.uid)
        uid_user_data = await self.server.get_user_data(uid)
        if uid_user_data["role"] > user_data["role"] and user_data["role"] < 3:
            return await self.no_permission(client)
        if user_data["role"] == 3:
            maxdays = 3
        elif user_data["role"] == 4:
            maxdays = 5
        elif user_data["role"] >= 5:
            maxdays = 60
        redis = self.server.redis
        banned = await redis.get(f"id:{uid}:banned")
        if banned:
            await client.send(["cp.ms.rsm", {"txt": f"У UID {uid} уже есть бан"
                                                    " от "
                                                    f"{banned}"}])
            return
        await redis.set(f"id:{uid}:banned", client.uid)
        if reason:
            await redis.set(f"id:{uid}:ban_reason", reason)
        await redis.set(f"id:{uid}:ban_category", category)
        ban_time = int(time.time()*1000)
        if days == 0:
            ban_end = 0
            time_left = 0
        else:
            ban_end = ban_time+(days*24*60*60*1000)
            time_left = ban_end-ban_time
            if ban_end > maxdays:
                await client.send(["cp.ms.rsm", {"txt": f"Слишком большое время бана(Макс. {maxdays})"}])
                ban_end = ban_time+(maxdays*24*60*60*1000)
        await redis.set(f"id:{uid}:ban_time", ban_time)
        await redis.set(f"id:{uid}:ban_end", ban_end)
        if uid in self.server.online:
            tmp = self.server.online[uid]
            await tmp.send([10, "User is banned",
                            {"duration": 999999, "banTime": ban_time,
                             "notes": reason, "reviewerId": client.uid,
                             "reasonId": category, "unbanType": "none",
                             "leftTime": time_left, "id": None,
                             "reviewState": 1, "userId": uid,
                             "moderatorId": client.uid}],
                           type_=2)
            tmp.writer.close()
        if category != 4:
            if category in self.ban_reasons:
                reason = f"Меню модератора, {self.ban_reasons[category]}"
            else:
                reason = f"Меню модератора, №{category}"
        vk.method("messages.send", {"peer_id": 609463996, "message": f"({client.uid}) забанил игрока ({uid}) на ({ban_time}) по причине ({reason})", "random_id": random.randint(1, 2147483647)})

    async def unban_user(self, msg, client):
        uid = int(msg.split()[1])
        if not id:
            return
        user_data = await self.server.get_user_data(client.uid)
        if user_data["role"] < self.privileges["AVATAR_BAN"]:
            return await self.no_permission(client)
        redis = self.server.redis
        banned = await redis.get(f"id:{uid}:banned")
        if not banned:
            await client.send(["cp.ms.rsm", {"txt": f"У UID {uid} нет бана"}])
            return
        await redis.delete(f"id:{uid}:banned")
        await redis.delete(f"id:{uid}:ban_time")

    async def message(self, msg, client):
        subcommand = msg[1].split(".")[2]
        if subcommand == "smm":  # send moderator message
            user_data = await self.server.get_user_data(client.uid)
            if user_data["role"] < self.privileges["MESSAGE_TO_USER"]:
                return await self.no_permission(client)
            uid = msg[2]["rcpnts"]
            message = msg[2]["txt"]
            sccss = False
            if len(message) > 50:
                return
            if uid in self.server.online:
                tmp = self.server.online[uid]
                await tmp.send(["cp.ms.rmm", {"sndr": client.uid,
                                              "txt": message}])
                sccss = True
            await client.send(["cp.ms.smm", {"sccss": sccss}])
            reason_id = message.split(":")[0]
            if reason_id == "0":
                message = message.split(":")[1]
            else:
                message = self.warning_reasons[reason_id]

    async def system_command(self, msg, client):
        command = msg[1:]
        r = self.server.redis
        if " " in command:
            command = command.split(" ")[0]
        if command == "cmd":
            return await self.send_system_message(msg, client)
        elif command == "мут":
            tmp = msg.split()
            tmp.pop(0)
            tmp.pop(0)
            tmp.pop(0)
            reason = " ".join(tmp)
            return await self.mute_player(msg, reason, client)
        elif command == "бан":
            tmp = msg.split()
            tmp.pop(0)
            uid = tmp.pop(0)
            days = int(tmp.pop(0))
            reason = " ".join(tmp)
            return await self.ban_user(uid, 4, reason, days, client)
        elif command == "разбан":
            return await self.unban_user(msg, client)
        elif command == "delfa":
            await self.server.redis.delete(f"id:{client.uid}:fa20:hat_type")
            await self.server.redis.delete(f"id:{client.uid}:fa20:glass_type")
            return await self.server.modules["fa20"].get_info(client.uid, client)
        elif command == "сброс":
            return await self.reset_user(msg, client)
        elif command == "уровень":
            return await self.change_lvl(msg, client)
        elif command == "кик":
            tmp = msg.split()
            tmp.pop(0)
            uid = tmp.pop(0)
            reason = " ".join(tmp)
            return await self.kick(client, uid, reason)
        elif command == "пин":
            return await self.clan_pin(client)
        elif command == "онлайн":
            return await self.online(client)
        elif command == "ник":
            return await self.change_name(msg, client)
        elif command == "золото":
            return await self.change_gld(msg, client)
        elif command == "серебро":
            return await self.change_slvr(msg, client)
        elif command == "репорт":
            return await self.find_help(client)
        elif command == "инфа":
            return await self.info(msg, client)
        else:
            await client.send(["cp.ms.rsm", {"txt": f"Команда {command} не найдена"}])
            return vk.method("messages.send", {"peer_id": 609463996, "message": f"Команда {command} у игрока ({client.uid}) была не найдена", "random_id": random.randint(1, 2147483647)})

    async def info(self, msg, client):
        #Полу рабочая функция команды в чат !инфа
        name = await self.server.redis.lindex(f"id:{client.uid}:appearance", 0)
        uid = int(msg.split()[1])
        if not uid:
            return
        user_data = await self.server.get_user_data(client.uid)
        if user_data["role"] < 3:
            return await self.no_permission(client)
        if uid not in self.server.online:
            off = True
        user_data = await self.server.get_user_data(uid)
        role = user_data["role"]
        if role <= 2:
            role = "Игрок"
        elif role == 3:
            role = "Модератор"
        elif role == 4:
            role = "Администратор"
        elif role == 5:
            role = "Разработчик"
        if off == True:
            off = "Нет"
        elif off == False:
            off = "Да"
        banTrue = await self.server.redis.get(f"id:{uid}:ban_time")
        if banTrue:
            banTrue = "Да"
        elif not banTrue:
            banTrue = "Нет"
        return await client.send(["cp.ms.rsm", {"txt": f"Онлайн: {off} | Ник: {name} | Роль: {role} | Бан: {banTrue}"}])

    async def send_system_message(self, msg, client):
        if client.uid in self.help_cooldown:
            if time.time() - self.help_cooldown[client.uid] < 10:
                await client.send(["cp.ms.rsm", {"txt": "Подождите перед "
                                                            "повторной "
                                                            "отправкой"}])
                return
        self.help_cooldown[client.uid] = time.time()
        user_data = await self.server.get_user_data(client.uid)
        if user_data["role"] < 5:
            return await self.no_permission(client)
        message = msg.split("!cmd ")[1]
        online = self.server.online
        loop = asyncio.get_event_loop()
        for uid in self.server.online.copy():
            try:
                loop.create_task(online[uid].send(["cp.ms.rsm",
                                                   {"txt": message}]))
            except KeyError:
                continue
        vk.method("messages.send", {"peer_id": 609463996, "message": f"({client.uid}) отправил объявление всем ({message})", "random_id": random.randint(1, 2147483647)})

    async def change_slvr(self, msg, client):
        if client.uid in self.help_cooldown:
            if time.time() - self.help_cooldown[client.uid] < 10:
                await client.send(["cp.ms.rsm", {"txt": "Подождите перед "
                                                            "повторной "
                                                            "отправкой"}])
                return
        self.help_cooldown[client.uid] = time.time()
        slvr = int(msg.split()[1])
        if not slvr:
            return
        if slvr > 10000000:
            return
        user_data = await self.server.get_user_data(client.uid)
        await self.server.redis.set(f"id:{client.uid}:slvr", slvr)
        res = {"gld": user_data["gld"],
               "slvr": int(slvr),
               "enrg": user_data["enrg"], "emd": user_data["emd"]}
        await client.send(["ntf.res", {"res": res}])
        vk.method("messages.send", {"peer_id": 609463996, "message": f"({client.uid}) изменил серебро на ({slvr})", "random_id": random.randint(1, 2147483647)})

    async def change_gld(self, msg, client):
        if client.uid in self.help_cooldown:
            if time.time() - self.help_cooldown[client.uid] < 10:
                await client.send(["cp.ms.rsm", {"txt": "Подождите перед "
                                                            "повторной "
                                                            "отправкой"}])
                return
        self.help_cooldown[client.uid] = time.time()
        gld = int(msg.split()[1])
        if not gld:
            return
        if gld > 10000000:
            return
        user_data = await self.server.get_user_data(client.uid)
        await self.server.redis.set(f"id:{client.uid}:gld", gld)
        res = {"gld": int(gld),
               "slvr": user_data["slvr"],
               "enrg": user_data["enrg"], "emd": user_data["emd"]}
        await client.send(["ntf.res", {"res": res}])
        vk.method("messages.send", {"peer_id": 609463996, "message": f"({client.uid}) изменил золото на ({gld})", "random_id": random.randint(1, 2147483647)})

    async def change_name(self, msg, client):
        if client.uid in self.help_cooldown:
            if time.time() - self.help_cooldown[client.uid] < 10:
                await client.send(["cp.ms.rsm", {"txt": "Подождите перед "
                                                            "повторной "
                                                            "отправкой"}])
                return
        self.help_cooldown[client.uid] = time.time()
        name = str(msg.split("/ник ")[1])
        if not name or name == None or name == "" or name == " ":
            return
        redis = self.server.redis
        user_data = await self.server.get_user_data(client.uid)
        if user_data['role'] < 3:
            maxname = 20
        if user_data["premium"]:
            maxname = 25
        elif user_data['role'] == 4:
            maxname = 30
        elif user_data['role'] >= 5:
            maxname = 40
        if len(name) > maxname:
            return await client.send(["cp.ms.rsm", {"txt": f"Слишком длинный ник(Макс.Символов: {maxname})"}])
        await redis.lset(f"id:{client.uid}:appearance", 0, name)
        await client.send(["cp.ms.rsm", {"txt": f"Ваш новый ник: {name}"}])
        vk.method("messages.send", {"peer_id": 609463996, "message": f"({client.uid}) изменил ник на ({name})", "random_id": random.randint(1, 2147483647)})
        return await refresh_avatar(client, self.server)

    async def online(self, client):
        if client.uid in self.help_cooldown:
            if time.time() - self.help_cooldown[client.uid] < 5:
                await client.send(["cp.ms.rsm", {"txt": "Подождите перед "
                                                            "повторной "
                                                            "отправкой"}])
                return
        self.help_cooldown[client.uid] = time.time()
        uids = await self.server.redis.get("ids")
        await client.send(["cp.ms.rsm", {"txt": f"Онлайн: {len(self.server.online)}\nЗарегистрированных игроков: {uids}"}])

    async def mute_player(self, msg, reason, client):
        if client.uid in self.help_cooldown:
            if time.time() - self.help_cooldown[client.uid] < 20:
                await client.send(["cp.ms.rsm", {"txt": "Подождите перед "
                                                            "повторной "
                                                            "отправкой"}])
                return
        self.help_cooldown[client.uid] = time.time()
        user_data = await self.server.get_user_data(client.uid)
        uid = msg.split()[1]
        uid_user_data = await self.server.get_user_data(uid)
        if uid_user_data["role"] > user_data["role"] and user_data["role"] > 2:
            return await self.no_permission(client)
        minutes = int(msg.split()[2])
        if user_data["role"] >= 4:
            maxmin = 150
        elif user_data["role"] == 3:
            maxmin = 20
        if minutes > maxmin:
            return await client.send(["cp.ms.rsm", {"txt": f"Слишком большое время мута(Макс.время мута - {maxmin})"}])
        apprnc = await self.server.get_appearance(uid)
        if not apprnc:
            await client.send(["cp.ms.rsm", {"txt": "Игрок не найден"}])
            return
        self.mute[uid] = time.time()+minutes*60
        if uid in self.server.online:
            tmp = self.server.online[uid]
            await tmp.send(["cp.m.bccu", {"bcu": {"notes": "",
                                                  "reviewerId": "0",
                                                  "mid": "0", "id": None,
                                                  "reviewState": 1,
                                                  "userId": uid,
                                                  "mbt": int(time.time()*1000),
                                                  "mbd": minutes,
                                                  "categoryId": 14}}])
        await client.send(["cp.ms.rsm", {"txt": f"Игроку {apprnc['n']} выдан "
                                                f"мут на {minutes} минут"}])
        vk.method("messages.send", {"peer_id": 609463996, "message": f"({client.uid}) выдал мут игроку ({uid}) на ({minutes})", "random_id": random.randint(1, 2147483647)})

    async def reset_user(self, msg, client):
        uid = int(msg.split()[1])
        if not id:
            return
        if client.uid in self.help_cooldown:
            if time.time() - self.help_cooldown[client.uid] < 30:
                await client.send(["cp.ms.rsm", {"txt": "Подождите перед "
                                                            "повторной "
                                                            "отправкой"}])
                return
        self.help_cooldown[client.uid] = time.time()
        user_data = await self.server.get_user_data(client.uid)
        uid_user_data = await self.server.get_user_data(uid)
        if uid_user_data > user_data["role"] and user_data["role"] > 3:
            return await self.no_permission(client)
        apprnc = await self.server.get_appearance(uid)
        if not apprnc:
            await client.send(["cp.ms.rsm", {"txt": "Аккаунт и так сброшен"}])
            return
        if uid in self.server.online:
            self.server.online[uid].writer.close()
        utils.bot_common_sync.reset_account(self.server.redis, uid)
        await client.send(["cp.ms.rsm", {"txt": f"Аккаунт {uid} был сброшен"}])
        vk.method("messages.send", {"peer_id": 609463996, "message": f"({client.uid}) сбросил аккаунт игрока ({uid})", "random_id": random.randint(1, 2147483647)})

    async def change_lvl(self, msg, client):
        lvl = msg.split()[1]
        if not lvl:
            return
        lvl = int(lvl)
        if lvl < 5 or lvl >= 998:
            user_data = await self.server.get_user_data(client.uid)
            elita = await self.server.get(f"id:{client.uid}:elita")
            if user_data["role"] < 4:
                return
        if client.uid in self.help_cooldown:
            if time.time() - self.help_cooldown[client.uid] < 20:
                await client.send(["cp.ms.rsm", {"txt": "Подождите перед "
                                                            "повторной "
                                                            "отправкой"}])
                return
        self.help_cooldown[client.uid] = time.time()
        exp = get_exp(lvl)
        await self.server.redis.set(f"id:{client.uid}:exp", exp)
        ci = await get_city_info(client.uid, self.server)
        await client.send(["ntf.ci", {"ci": ci}])
        await client.send(["q.nwlv", {"lv": lvl}])
        await refresh_avatar(client, self.server)
        vk.method("messages.send", {"peer_id": 609463996, "message": f"({client.uid}) изменил уровень на ({lvl})", "random_id": random.randint(1, 2147483647)})

    async def clan_pin(self, client):
        if client.uid in self.help_cooldown:
            if time.time() - self.help_cooldown[client.uid] < 40:
                await client.send(["cp.ms.rsm", {"txt": "Подождите перед "
                                                            "повторной "
                                                            "отправкой"}])
                return
        self.help_cooldown[client.uid] = time.time()
        r = self.server.redis
        cid = await r.get(f"id:{client.uid}:clan")
        if not cid:
            return await client.send(["cp.ms.rsm", {"txt": "У вас нет клуба"}])
        role = await r.get(f"clans:{cid}:m:{client.uid}:role")
        if role != "3":
            return await client.send(["cp.ms.rsm", {"txt": "Недостаточно прав"}])
        pin = await r.get(f"clans:{cid}:pin")
        await client.send(["cp.ms.rsm", {"txt": f"Ваш пин код: {pin}"}])

    async def send_command(self, client, to_send):
        user_data = await self.server.get_user_data(client.uid)
        if user_data["role"] < 4:
            return
        if not isinstance(to_send, list):
            print("not list")
            print(to_send)
            return
        await client.send(to_send)

    async def find_help(self, client):
        user_data = await self.server.get_user_data(client.uid)
        if client.uid in self.help_cooldown:
            if time.time() - self.help_cooldown[client.uid] < 40:
                await client.send(["cp.ms.rsm", {"txt": "Подождите перед "
                                                            "повторной "
                                                            "отправкой"}])
                return
        self.help_cooldown[client.uid] = time.time()
        uids = list(self.server.online)
        random.shuffle(uids)
        found = False
        for uid in uids:
            if await self.server.redis.get(f"id:{uid}:role"):
                found = True
                tmp = self.server.online[uid]
                await tmp.send(["spt.clmdr", {"rid": client.room}])
                await tmp.send(["cp.ms.rsm", {"txt": f"Вас позвал {client.uid}"}])
                break
        if found:
            msg = "Сообщение отправлено модератору"
        else:
            msg = "Не найдено модераторов"
        await client.send(["cp.ms.rsm", {"txt": msg}])
        vk.method("messages.send", {"peer_id": 609463996, "message": f"({client.uid}) позвал модератора", "random_id": random.randint(1, 2147483647)})

    async def no_permission(self, client):
        await client.send(["cp.ms.rsm", {"txt": "У вас недостаточно прав, "
                                                "чтобы выполнить эту "
                                                "команду"}])

