import asyncio
import multiprocessing
import config
import custom_logger
import server
import client


def run_server():
    server.server_run()


def run_client():
    client.client_run()


def start_process(target):
    p = multiprocessing.Process(target=target)
    p.daemon = True
    p.start()
    return p


async def main():
    custom_logger.info("Starting...")
    try:
        start_process(run_server)
        if config.RUN_TEMP_CLIENT:
            await asyncio.sleep(1)
            start_process(run_client)
        while True:
            pass
    except KeyboardInterrupt:
        custom_logger.info("Exiting...")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    asyncio.run(main())
