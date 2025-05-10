import asyncio
import multiprocessing
import re
import config
import utils
import enums
import custom_logger
import uuid
import json
from models import DungeonLabMessage, DungeonLabSimpleMessage, DungeonLabStrengthMessage, DungeonLabClearMessage, DungeonLabPulseMessage, DungeonLabPresetPulseMessage
from enums import MessageType, ChannelType
from uvicorn import Config, Server
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# region Server
app = FastAPI()
server: Optional[Server] = None


def server_run():
    global server
    server = Server(Config(app=app, host=config.WS_SERVER_HOST, port=config.WS_SERVER_PORT))
    server.run()


async def server_shutdown():
    global server
    if server is not None:
        await server.shutdown()
        server = None


@app.websocket("/{full_path:path}")
async def websocket_endpoint(websocket: WebSocket, full_path: str):
    await websocket.accept()
    await on_client_connected(websocket, full_path)
    try:
        heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
        while True:
            message = await websocket.receive_text()
            await on_receive_message(websocket, message)
    except WebSocketDisconnect:
        await on_client_disconnected(websocket)
    finally:
        heartbeat_task.cancel()
# endregion


# region ClientManager
client_dict = {}  # {uid:websocket}
relationship_dict = {}  # {client_id:target_id}


def clear_client_dict():
    client_dict.clear()
    relationship_dict.clear()


def add_client(websocket: WebSocket) -> str:
    if websocket not in client_dict.values():
        uid = str(uuid.uuid4())
        client_dict[uid] = websocket
    return uid


def remove_client(websocket: WebSocket):
    for uid, ws in client_dict.items():
        if ws == websocket:
            del client_dict[uid]
            break
    for client_id, target_id in relationship_dict.items():
        if client_id == uid or target_id == uid:
            del relationship_dict[client_id]
            break


def get_client_websocket(uid) -> Optional[WebSocket]:
    if uid in client_dict:
        return client_dict[uid]
    return None


def get_client_uid(websocket: WebSocket) -> Optional[str]:
    for uid, ws in client_dict.items():
        if ws == websocket:
            return uid
    return None


def get_target_id_by_client_id(client_id: str) -> Optional[str]:
    if client_id in relationship_dict:
        return relationship_dict[client_id]
    return None


def get_client_id_by_target_id(target_id: str) -> Optional[str]:
    for client_id, target in relationship_dict.items():
        if target == target_id:
            return client_id
    return None


def bind_client(client_id: str, target_id: str):
    relationship_dict[client_id] = target_id
# endregion


# region Handlers
async def on_client_connected(websocket: WebSocket, full_path: str):
    uid = add_client(websocket)
    custom_logger.info(f"【Server】 Client {uid} connected to {full_path}")
    await send_dg_message(websocket, enums.MessageType.BIND, uid, "", "targetId")
    if not full_path.strip():
        qr_code_str = utils.get_qr_code_str(config.WS_CLIENT_HOST, config.WS_SERVER_PORT, uid)
        custom_logger.debug(f"【Server】 QR code string: {qr_code_str}")
        utils.show_qr_code(qr_code_str)


async def on_client_disconnected(websocket):
    uid = get_client_uid(websocket)
    custom_logger.info(f"【Server】 Client {uid} disconnected")
    if uid is not None:
        if uid in relationship_dict.keys():
            target_id = get_target_id_by_client_id(uid)
            if target_id is not None:
                target_websocket = get_client_websocket(target_id)
                await send_dg_message(target_websocket, enums.MessageType.BREAK, uid, target_id, enums.StatusCode.CLIENT_DISCONNECTED.value)
        if uid in relationship_dict.values():
            client_id = get_client_id_by_target_id(uid)
            if client_id is not None:
                client_websocket = get_client_websocket(client_id)
                await send_dg_message(client_websocket, enums.MessageType.BREAK, client_id, uid, enums.StatusCode.CLIENT_DISCONNECTED.value)
    remove_client(websocket)
# endregion


# region Handlers
async def on_receive_message(websocket, response):
    try:
        uid = get_client_uid(websocket)
        try:
            custom_logger.debug(f"【Server】 Receive client {uid} message: {response}")
            data = DungeonLabMessage.model_validate_json(json_data=response)
        except json.JSONDecodeError:
            await send_dg_message(websocket, enums.MessageType.MSG, "", "", enums.StatusCode.INVALID_JSON_FORMAT.value)
        if data:
            type = data.type
            message = data.message
            client_id = data.clientId
            target_id = data.targetId
            if type == enums.MessageType.BIND:
                await on_receive_bind_type_message(websocket, client_id, target_id, message)
            elif type == enums.MessageType.MSG:
                pass
            elif type == enums.MessageType.HEARTBEAT:
                pass
            elif type == enums.MessageType.BREAK:
                pass
            elif type == enums.MessageType.ERROR:
                custom_logger.error(f"【Server】 Client {uid} error: {message}")
            elif type == enums.MessageType.CUSTOM:
                await on_receive_custom_message(websocket, client_id, target_id, message)
            if type != enums.MessageType.CUSTOM and uid is not None:
                if uid in relationship_dict.keys():
                    target_id = get_target_id_by_client_id(uid)
                    if target_id is not None:
                        target_websocket = get_client_websocket(target_id)
                        await send_dg_message(target_websocket, type, uid, target_id, message)
                if uid in relationship_dict.values():
                    client_id = get_client_id_by_target_id(uid)
                    if client_id is not None:
                        client_websocket = get_client_websocket(client_id)
                        await send_dg_message(client_websocket, type, client_id, uid, message)
    except Exception as e:
        custom_logger.error(f"【Server】 Error processing message: {e}")


async def on_receive_bind_type_message(websocket, client_id, target_id, message):
    is_client_id_exist = client_id in client_dict.keys()
    is_target_id_exist = target_id in client_dict.keys()
    if not is_client_id_exist or not is_target_id_exist:
        await send_dg_message(websocket, enums.MessageType.BIND, client_id, target_id, enums.StatusCode.TARGET_CLIENT_NOT_FOUND.value)
    is_client_id_bind = client_id in relationship_dict.keys() or client_id in relationship_dict.values()
    is_target_id_bind = target_id in relationship_dict.keys() or target_id in relationship_dict.values()
    if is_client_id_bind or is_target_id_bind:
        await send_dg_message(websocket, enums.MessageType.MSG, client_id, target_id, enums.StatusCode.ID_ALREADY_BOUND.value)
    else:
        bind_client(client_id, target_id)
        await send_dg_message(websocket, enums.MessageType.BIND, client_id, target_id, enums.StatusCode.SUCCESS.value)


async def on_receive_custom_message(websocket, client_id: str, target_id: str, message: str):
    if message.startswith("preset-"):
        match = re.match(r"preset-([A-Za-z]+):(.*)", message)
        if match:
            channel_str = match.group(1)
            channel = ChannelType[channel_str]
            preset = match.group(2)
            preset_pulse_section_list = utils.get_preset_pulse_section_str_list(preset)
            target_websocket = get_client_websocket(target_id)
            for section in preset_pulse_section_list:
                pulse_str = utils.get_pulse_str(channel, section)
                await send_dg_message(target_websocket, enums.MessageType.MSG, client_id, target_id, pulse_str)


@app.post("/dungeon_lab_message")
async def on_post_dungeon_lab_message(dungeon_lab_message: DungeonLabSimpleMessage):
    await send_dg_message_to_all_target(dungeon_lab_message.type, dungeon_lab_message.message)


@app.post("/dungeon_lab_strength_message")
async def on_post_dungeon_lab_strength_message(pulse_message: DungeonLabStrengthMessage):
    strength_str = utils.get_strength_str(pulse_message.channel, pulse_message.mode, pulse_message.value)
    await send_dg_message_to_all_target(MessageType.MSG, strength_str)


@app.post("/dungeon_lab_clear_message")
async def on_post_dungeon_lab_clear_message(pulse_message: DungeonLabClearMessage):
    clear_str = utils.get_clear_str(pulse_message.channel)
    await send_dg_message_to_all_target(MessageType.MSG, clear_str)


@app.post("/dungeon_lab_pulse_message")
async def on_post_dungeon_lab_pulse_message(pulse_message: DungeonLabPulseMessage):
    pulse_str = utils.get_pulse_str(pulse_message.channel, pulse_message.pulse)
    await send_dg_message_to_all_target(MessageType.MSG, pulse_str)


@app.post("/dungeon_lab_preset_pulse_message")
async def on_post_dungeon_lab_preset_pulse_message(pulse_message: DungeonLabPresetPulseMessage):
    section_pulse_list = utils.get_preset_pulse_section_str_list(pulse_message.preset)
    for section_pulse in section_pulse_list:
        pulse_str = utils.get_pulse_str(pulse_message.channel, section_pulse)
        await send_dg_message_to_all_target(MessageType.MSG, pulse_str)
# endregion


# region Send
async def send_dg_message_to_all_target(type: MessageType, message: str):
    try:
        custom_logger.debug(f"【Server】 Broadcast message to DG-LAB: {{type:{type.value},message:{message},...}}")
        for client_id, target_id in relationship_dict.items():
            ws = get_client_websocket(target_id)
            await send_dg_message(ws, type, client_id, target_id, message)
    except Exception as e:
        custom_logger.error(f"【Server】 Error broadcasting message to DG-LAB: {e}")


async def send_heartbeat(websocket: WebSocket):
    while True:
        await asyncio.sleep(config.HEARTBEAT_INTERVAL)
        try:
            uid = get_client_uid(websocket)
            if uid:
                await send_dg_message(websocket, MessageType.HEARTBEAT, uid, "", enums.StatusCode.SUCCESS.value)
        except Exception as e:
            print(f"【Server】 Send heartbeat error: {e}")


async def send_dg_message(websocket: Optional[WebSocket], type: MessageType, client_id: str, target_id: str, message: str):
    if websocket is not None:
        json = utils.get_dg_message_json(type, client_id, target_id, message)
        uid = get_client_uid(websocket)
        custom_logger.debug(f"【Server】 Send message to client {uid}: {json}")
        await websocket.send_text(json)
# endregion


if __name__ == "__main__":
    multiprocessing.freeze_support()
    server_run()
