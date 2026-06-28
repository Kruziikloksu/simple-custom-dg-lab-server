import asyncio
import config
import custom_logger
import server
import client
from uvicorn import Config, Server


async def wait_for_server_started(uvicorn_server: Server, timeout: float = 10.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while not uvicorn_server.started:
        if uvicorn_server.should_exit:
            raise RuntimeError("Server exited before startup completed")
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError("Timed out waiting for server startup")
        await asyncio.sleep(0.05)


async def async_main():
    uvicorn_server = Server(Config(app=server.app, host=config.WS_SERVER_HOST, port=config.WS_SERVER_PORT))
    server.server = uvicorn_server
    server_task = asyncio.create_task(uvicorn_server.serve(), name="dglab-server")
    temp_client_task = None

    try:
        await wait_for_server_started(uvicorn_server)
        custom_logger.info(f"【Main】 Server started at {config.WS_SERVER_HOST}:{config.WS_SERVER_PORT}")

        if config.RUN_TEMP_CLIENT:
            uri = f"ws://{config.TEMP_CLIENT_HOST}:{config.WS_SERVER_PORT}"
            temp_client_task = asyncio.create_task(client.run_client(uri), name="dglab-temp-client")

        await server_task
    finally:
        if temp_client_task is not None:
            await client.client_shutdown()
            temp_client_task.cancel()
            await asyncio.gather(temp_client_task, return_exceptions=True)
        uvicorn_server.should_exit = True
        await asyncio.gather(server_task, return_exceptions=True)


def main():
    custom_logger.info("Starting...")
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        custom_logger.info("Exiting...")


if __name__ == "__main__":
    main()
