import asyncio
import re
import config
import utils
import enums
import custom_logger
import uuid
import json
import io
from models import DungeonLabMessage, DungeonLabSimpleMessage, DungeonLabStrengthInfo, DungeonLabStrengthMessage, DungeonLabClearMessage, DungeonLabPulseMessage, DungeonLabPresetPulseMessage, DungeonLabTempClientInfo
from enums import MessageType, ChannelType
from pydantic import ValidationError
from uvicorn import Config, Server
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
import qrcode

# region Server
app = FastAPI()
server: Optional[Server] = None
temp_client_id: Optional[str] = None
strength_a = 0
strength_b = 0
strength_limit_a = 0
strength_limit_b = 0


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
    heartbeat_task = None
    try:
        await on_client_connected(websocket, full_path)
        heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
        while True:
            message = await websocket.receive_text()
            await on_receive_message(websocket, message)
    except WebSocketDisconnect:
        await on_client_disconnected(websocket)
    except Exception as e:
        custom_logger.error(f"【Server】 WebSocket endpoint error: {e}")
        await on_client_disconnected(websocket)
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            await asyncio.gather(heartbeat_task, return_exceptions=True)
# endregion


# region ClientManager
client_dict = {}  # {uid:websocket}
relationship_dict = {}  # {client_id:target_id}


def clear_client_dict():
    client_dict.clear()
    relationship_dict.clear()


def add_client(websocket: WebSocket) -> str:
    global temp_client_id
    existing_uid = get_client_uid(websocket)
    if existing_uid is not None:
        return existing_uid

    uid = str(uuid.uuid4())
    client_dict[uid] = websocket
    if temp_client_id is None:
        temp_client_id = uid
    return uid


def remove_client(websocket: WebSocket):
    global temp_client_id
    uid = get_client_uid(websocket)
    if uid is None:
        return

    client_dict.pop(uid, None)
    if temp_client_id == uid:
        temp_client_id = None

    relationship_to_remove = [
        client_id
        for client_id, target_id in relationship_dict.items()
        if client_id == uid or target_id == uid
    ]
    for client_id in relationship_to_remove:
        relationship_dict.pop(client_id, None)


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
    try:
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
    except Exception as e:
        custom_logger.debug(f"【Server】 Peer disconnect notification skipped: {e}")
    finally:
        remove_client(websocket)
# endregion


# region Handlers
async def on_receive_message(websocket, response):
    global strength_a, strength_b, strength_limit_a, strength_limit_b, temp_client_id
    try:
        uid = get_client_uid(websocket)
        try:
            custom_logger.debug(f"【Server】 Receive client {uid} message: {response}")
            data = DungeonLabMessage.model_validate_json(json_data=response)
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            custom_logger.warning(f"【Server】 Invalid client {uid} message: {e}")
            await send_dg_message(websocket, enums.MessageType.MSG, "", "", enums.StatusCode.INVALID_JSON_FORMAT.value)
            return

        if data:
            message_type = data.type
            message = data.message
            client_id = data.clientId
            target_id = data.targetId
            should_forward = True
            if message_type == enums.MessageType.BIND:
                should_forward = await on_receive_bind_type_message(websocket, client_id, target_id, message)
            elif message_type == enums.MessageType.MSG:
                if temp_client_id:
                    temp_target_id = get_target_id_by_client_id(temp_client_id)
                    if temp_target_id and client_id == temp_client_id and uid == temp_target_id:
                        update_temp_strength(message)
            elif message_type == enums.MessageType.HEARTBEAT:
                pass
            elif message_type == enums.MessageType.BREAK:
                pass
            elif message_type == enums.MessageType.ERROR:
                custom_logger.error(f"【Server】 Client {uid} error: {message}")
            elif message_type == enums.MessageType.CUSTOM:
                await on_receive_custom_message(websocket, client_id, target_id, message)
                should_forward = False
            if should_forward and message_type != enums.MessageType.CUSTOM and uid is not None:
                if uid in relationship_dict.keys():
                    target_id = get_target_id_by_client_id(uid)
                    if target_id is not None:
                        target_websocket = get_client_websocket(target_id)
                        await send_dg_message(target_websocket, message_type, uid, target_id, message)
                if uid in relationship_dict.values():
                    client_id = get_client_id_by_target_id(uid)
                    if client_id is not None:
                        client_websocket = get_client_websocket(client_id)
                        await send_dg_message(client_websocket, message_type, client_id, uid, message)
    except Exception as e:
        custom_logger.error(f"【Server】 Error processing message: {e}")


async def on_receive_bind_type_message(websocket, client_id, target_id, message):
    is_client_id_exist = client_id in client_dict.keys()
    is_target_id_exist = target_id in client_dict.keys()
    if not is_client_id_exist or not is_target_id_exist:
        await send_dg_message(websocket, enums.MessageType.BIND, client_id, target_id, enums.StatusCode.TARGET_CLIENT_NOT_FOUND.value)
        return False
    is_client_id_bind = client_id in relationship_dict.keys() or client_id in relationship_dict.values()
    is_target_id_bind = target_id in relationship_dict.keys() or target_id in relationship_dict.values()
    if is_client_id_bind or is_target_id_bind:
        await send_dg_message(websocket, enums.MessageType.MSG, client_id, target_id, enums.StatusCode.ID_ALREADY_BOUND.value)
        return False
    else:
        bind_client(client_id, target_id)
        await send_dg_message(websocket, enums.MessageType.BIND, client_id, target_id, enums.StatusCode.SUCCESS.value)
        return True


def update_temp_strength(message: str):
    global strength_a, strength_b, strength_limit_a, strength_limit_b
    if not message.startswith("strength"):
        return

    strength_arr = message.split("-", maxsplit=1)
    if len(strength_arr) != 2:
        return

    strength_value_arr = strength_arr[1].split("+")
    if len(strength_value_arr) != 4:
        return

    try:
        strength_a = int(strength_value_arr[0])
        strength_b = int(strength_value_arr[1])
        strength_limit_a = int(strength_value_arr[2])
        strength_limit_b = int(strength_value_arr[3])
    except ValueError as e:
        custom_logger.warning(f"【Server】 Invalid strength message: {message}, error: {e}")


async def on_receive_custom_message(websocket, client_id: str, target_id: str, message: str):
    if message.startswith("preset-"):
        match = re.match(r"preset-([A-Za-z]+):(.*)", message)
        if match:
            channel_str = match.group(1)
            if channel_str not in ChannelType.__members__:
                await send_dg_message(websocket, enums.MessageType.ERROR, client_id, target_id, enums.StatusCode.INVALID_JSON_FORMAT.value)
                return
            channel = ChannelType[channel_str]
            preset = match.group(2)
            preset_pulse_section_list = utils.get_preset_pulse_section_str_list(preset)
            target_websocket = get_client_websocket(target_id)
            if target_websocket is None:
                await send_dg_message(websocket, enums.MessageType.ERROR, client_id, target_id, enums.StatusCode.RECIPIENT_NOT_FOUND.value)
                return
            for section in preset_pulse_section_list:
                pulse_str = utils.get_pulse_str(channel, section)
                await send_dg_message(target_websocket, enums.MessageType.MSG, client_id, target_id, pulse_str)


@app.post("/dungeon_lab_message")
async def on_post_dungeon_lab_message(dungeon_lab_message: DungeonLabSimpleMessage):
    sent = await send_dg_message_to_temp_target(dungeon_lab_message.type, dungeon_lab_message.message)
    if not sent:
        return Response(content="No bound DG-LAB APP", status_code=409)
    return {"sent": True}


@app.post("/dungeon_lab_strength_message")
async def on_post_dungeon_lab_strength_message(pulse_message: DungeonLabStrengthMessage):
    strength_str = utils.get_strength_str(pulse_message.channel, pulse_message.mode, pulse_message.value)
    sent = await send_dg_message_to_temp_target(MessageType.MSG, strength_str)
    if not sent:
        return Response(content="No bound DG-LAB APP", status_code=409)
    return {"sent": True}


@app.post("/dungeon_lab_clear_message")
async def on_post_dungeon_lab_clear_message(pulse_message: DungeonLabClearMessage):
    clear_str = utils.get_clear_str(pulse_message.channel)
    sent = await send_dg_message_to_temp_target(MessageType.MSG, clear_str)
    if not sent:
        return Response(content="No bound DG-LAB APP", status_code=409)
    return {"sent": True}


@app.post("/dungeon_lab_pulse_message")
async def on_post_dungeon_lab_pulse_message(pulse_message: DungeonLabPulseMessage):
    pulse_str = utils.get_pulse_str(pulse_message.channel, pulse_message.pulse)
    sent = await send_dg_message_to_temp_target(MessageType.MSG, pulse_str)
    if not sent:
        return Response(content="No bound DG-LAB APP", status_code=409)
    return {"sent": True}


@app.post("/dungeon_lab_preset_pulse_message")
async def on_post_dungeon_lab_preset_pulse_message(pulse_message: DungeonLabPresetPulseMessage):
    section_pulse_list = utils.get_preset_pulse_section_str_list(pulse_message.preset)
    any_sent = False
    for section_pulse in section_pulse_list:
        pulse_str = utils.get_pulse_str(pulse_message.channel, section_pulse)
        sent = await send_dg_message_to_temp_target(MessageType.MSG, pulse_str)
        any_sent = any_sent or sent
    if not any_sent:
        return Response(content="No bound DG-LAB APP", status_code=409)
    return {"sent": True}


@app.get("/dungeon_lab_temp_strength_info")
async def on_get_dungeon_lab_temp_strength_info():
    global strength_a, strength_b, strength_limit_a, strength_limit_b
    info = DungeonLabStrengthInfo(
        strengthA=strength_a,
        strengthB=strength_b,
        strengthLimitA=strength_limit_a,
        strengthLimitB=strength_limit_b
    )
    return info


@app.get("/dungeon_lab_temp_client_info")
async def on_get_dungeon_lab_temp_client_info():
    client_id = temp_client_id or ""
    target_id = get_target_id_by_client_id(client_id) if client_id else None
    qr_code = utils.get_qr_code_str(config.WS_CLIENT_HOST, config.WS_SERVER_PORT, client_id) if client_id else ""
    return DungeonLabTempClientInfo(
        clientId=client_id,
        targetId=target_id or "",
        bound=bool(target_id),
        qrCode=qr_code
    )


@app.get("/dungeon_lab_temp_client_qr.png")
async def on_get_dungeon_lab_temp_client_qr_png():
    client_id = temp_client_id or ""
    if not client_id:
        return Response(status_code=404)

    qr_code = utils.get_qr_code_str(config.WS_CLIENT_HOST, config.WS_SERVER_PORT, client_id)
    img = qrcode.make(qr_code)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")
# endregion


# region Send
async def send_dg_message_to_temp_target(type: MessageType, message: str):
    global temp_client_id
    try:
        custom_logger.debug(f"【Server】 Send message to temp DG-LAB: {{type:{type.value},message:{message},...}}")
        if temp_client_id:
            temp_target_id = get_target_id_by_client_id(temp_client_id)
            if temp_target_id:
                ws = get_client_websocket(temp_target_id)
                if ws is not None:
                    await send_dg_message(ws, type, temp_client_id, temp_target_id, message)
                    return True
        return False
    except Exception as e:
        custom_logger.error(f"【Server】 Error sending message to temp DG-LAB: {e}")
        return False


async def send_heartbeat(websocket: WebSocket):
    while True:
        await asyncio.sleep(config.HEARTBEAT_INTERVAL)
        try:
            uid = get_client_uid(websocket)
            if uid:
                await send_dg_message(websocket, MessageType.HEARTBEAT, uid, "", enums.StatusCode.SUCCESS.value)
            else:
                return
        except asyncio.CancelledError:
            raise
        except Exception as e:
            custom_logger.warning(f"【Server】 Send heartbeat error: {e}")
            return


async def send_dg_message(websocket: Optional[WebSocket], type: MessageType, client_id: str, target_id: str, message: str):
    if websocket is not None:
        json_str = utils.get_dg_message_json(type, client_id, target_id, message)
        uid = get_client_uid(websocket)
        custom_logger.debug(f"【Server】 Send message to client {uid}: {json_str}")
        await websocket.send_text(json_str)
# endregion


if __name__ == "__main__":
    server_run()
