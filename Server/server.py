import asyncio
import json
from subprocess import check_output

HOST = '0.0.0.0'
PORT = 9090

clients = []
aliases = []

def to_json(cmd, value):
    js_list = {
        'cmd': cmd,
        'value': value
    }
    return json.dumps(js_list)

def from_json(js_string):
    js_list = json.loads(js_string)
    return js_list['cmd'], js_list['value']

async def handle_clients(reader, writer):
    msg = []
    index = None
    alias = None
    while True:
        data = await reader.read(1024)
        print(data)
        if not data:
            break
        cmd, value = from_json(data.decode('utf-8'))
        if cmd == 'quit':
            break
        elif cmd == 'alias':
            addr, port = writer.get_extra_info('peername')
            clients.append(writer)
            alias = value
            aliases.append(alias)
            index = clients.index(writer)
            print(f'Connection made with {addr}:{port}: {alias!r}')
            msg = 'Connected to ' + check_output(['hostname', '-I']).decode('-utf-8')
            writer.write(msg.encode('utf-8'))
            await writer.drain()
            continue
        
        if aliases[index] == 'Control Panel':
            if cmd == 'lights_power':
                pass
            elif cmd == 'lights_red':
                pass
            elif cmd == 'lights_green':
                pass
            elif cmd == 'lights_blue':
                pass
            elif cmd == 'ac_power':
                pass
            elif cmd == 'ac_temp':
                pass
            elif cmd == 'ac_fan':
                pass


    print(f'{addr}:{port} ({aliases[index]}) Disconnected')
    clients.pop(index)
    aliases.pop(index)
    writer.close()

async def run_server():
    server = await asyncio.start_server(handle_clients, HOST, PORT)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(run_server())