from modules.base_module import Module

class_name = "Trade"


class Trade(Module):
    prefix = "trd"

    def __init__(self, server):
        self.server = server
        self.commands = {"init": self.init}

    async def init(self, msg, client):
        #Тестовый обмен(Не рабочий)
        return await client.send(["trd.init", {"trid": msg[2]['trid']}])
