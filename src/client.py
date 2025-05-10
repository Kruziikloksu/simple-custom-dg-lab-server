import multiprocessing
import config
import utils
import custom_logger
import asyncio
import websockets
import json
from utils import DungeonLabMessage
from enums import MessageType, ChannelType, StrengthChangeMode


disconnect_event = asyncio.Event()

websocket = None

client_id = ""
target_id = ""
strength_a = 0
strength_b = 0
strength_limit_a = 0
strength_limit_b = 0


def client_run():
    async def run():
        try:
            uri = f"ws://{config.WS_CLIENT_HOST}:{config.WS_SERVER_PORT}"
            await websocket_client(uri)
        except Exception as e:
            custom_logger.error(f"【Client】 WebSocket connection error: {e}")
        finally:
            if websocket:
                await websocket.close()
    asyncio.run(run())


def client_shutdown():
    global disconnect_event
    disconnect_event.set()


async def websocket_client(uri):
    global disconnect_event, websocket
    try:
        async with websockets.connect(uri) as ws:
            websocket = ws
            while not disconnect_event.is_set():
                response = await websocket.recv(True)
                await on_receive_message(response)
            await websocket.close()
    except websockets.ConnectionClosed:
        custom_logger.info("【Client】 Connection closed")
    except Exception as e:
        custom_logger.error(f"【Client】 Error: {e}")


async def on_receive_message(response: str):
    global client_id, target_id
    try:
        custom_logger.debug(rf"【Client】 Received message: {response}")
        data = DungeonLabMessage.model_validate_json(json_data=response)
        type = data.type
        message = data.message
        if type == MessageType.BIND:
            if message == "targetId":
                client_id = data.clientId
                custom_logger.info(f"【Client】 Bind clientId: {client_id}")
            elif message == "DGLAB" and data.clientId == client_id:
                target_id = data.targetId
                custom_logger.info(f"【Client】 Bind targetId: {target_id}")
        elif type == MessageType.MSG:
            if message.startswith("strength"):
                global strength_a, strength_b, strength_limit_a, strength_limit_b
                strength_arr = message.split("-")
                strength_str = strength_arr[1]
                strength_value_arr = strength_str.split("+")
                strength_a = int(strength_value_arr[0])
                strength_b = int(strength_value_arr[1])
                strength_limit_a = int(strength_value_arr[2])
                strength_limit_b = int(strength_value_arr[3])
        else:
            pass
    except json.JSONDecodeError as e:
        custom_logger.error(f"【Client】 JSON decode error: {e}")
    except Exception as e:
        custom_logger.error(f"【Client】 Error processing message: {e}")


async def send_all_preset_pulse_message(channel: ChannelType):
    preset_dict = utils.get_preset_wave_data_dict()
    for preset in preset_dict.values():
        await send_preset_pulse_message(channel, preset)


async def send_preset_pulse_message(channel: ChannelType, preset: str):
    preset = utils.get_preset_pulse_str(channel, preset)
    await send_dg_message(MessageType.MSG, preset)


async def send_pulse_dg_message(channel: ChannelType, pulse: str):
    pulse = utils.get_pulse_str(channel, pulse)
    await send_dg_message(MessageType.MSG, pulse)


async def send_clear_pulse_dg_message(channel: ChannelType):
    await send_dg_message(MessageType.MSG, utils.get_clear_str(channel))


async def send_strength_dg_message(channel: ChannelType, mode: StrengthChangeMode, value: int):
    await send_dg_message(MessageType.MSG, utils.get_strength_str(channel, mode, value))


async def send_dg_message(type: MessageType, message: str):
    custom_logger.debug(f"【Client】 Received message: {message}")
    global websocket, client_id, target_id
    if websocket:
        json_str = utils.get_dg_message_json(type, client_id, target_id, message)
        custom_logger.debug(f"【Client】 Send message: {json_str}")
        await websocket.send(json_str)


def show_qr_code():
    if websocket:
        remote_address = websocket.remote_address
        qr_code_str = utils.get_qr_code_str(remote_address[0], remote_address[1], client_id)
        custom_logger.debug(f"【Client】 QR code string: {qr_code_str}")
        utils.show_qr_code(qr_code_str)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    client_run()
