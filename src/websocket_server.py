import asyncio
import websockets
from apscheduler.job import Job
from typing import Awaitable, Callable, Optional, Any
import config
import timer_manager
from websockets.asyncio.server import ServerConnection
from websockets.asyncio.server import Server
import custom_logger

class WebSocketServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server: Optional[Server] = None
        self.stop_event = asyncio.Event()
        self.on_heartbeat_callback: Optional[Callable] = None
        self.on_client_connected_callback: Optional[Callable] = None
        self.on_client_disconnected_callback: Optional[Callable] = None
        self.on_receive_client_message_callback: Optional[Callable] = None
        self.heartbeat_job: Optional[Job] = None

    async def start(self) -> None:
        try:
            custom_logger.debug(f"启动WebSocket服务 {self.host}:{self.port}")
            self.server = await websockets.serve(
                self._client_connect_handler,
                self.host,
                self.port
            )
            self.heartbeat_job = timer_manager.add_timer(
                config.HEARTBEAT_INTERVAL,
                self._heartbeat,
            )
            await self.stop_event.wait()
        except Exception as e:
            custom_logger.error(f"WebSocket启动失败 {e}")
        # finally:
        #     await self.stop()

    async def stop(self) -> None:
        if self.heartbeat_job is not None:
            self.heartbeat_job.remove()
            self.heartbeat_job = None
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        self.stop_event.clear()
        custom_logger.debug("WebSocket服务已关闭")

    def set_on_heartbeat_callback(self, callback: Callable) -> None:
        self.on_heartbeat_callback = callback

    def set_on_client_connected_callback(self, callback: Callable) -> None:
        self.on_client_connected_callback = callback

    def set_on_client_disconnected_callback(self, callback: Callable) -> None:
        self.on_client_disconnected_callback = callback

    def set_on_receive_client_message_callback(self, callback: Callable) -> None:
        self.on_receive_client_message_callback = callback

    async def _heartbeat(self) -> None:
        if self.on_heartbeat_callback:
            try:
                await self.on_heartbeat_callback()
            except Exception as e:
                custom_logger.error(f"心跳回调执行失败 {e}")

    async def _client_connect_handler(self, websocket:ServerConnection) -> None:
        client_ip = websocket.remote_address[0]
        custom_logger.debug(f"客户端连接 {client_ip}")
        try:
            if self.on_client_connected_callback:
                await self.on_client_connected_callback(websocket)
            async for message in websocket:
                if self.on_receive_client_message_callback:
                    try:
                        await self.on_receive_client_message_callback(websocket, message)
                    except Exception as e:
                        custom_logger.error(f"消息处理失败 {e}")
        except websockets.exceptions.ConnectionClosedError:
            custom_logger.info(f"客户端断开 {client_ip}")
        except Exception as e:
            custom_logger.error(f"连接异常 {repr(e)}")
        finally:
            if self.on_client_disconnected_callback:
                try:
                    await self.on_client_disconnected_callback(websocket)
                except Exception as e:
                    custom_logger.error(f"客户端断连回调执行失败: {e}")
