import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.job import Job
import custom_logger

main_scheduler = AsyncIOScheduler()

def add_timer(interval_seconds, async_callback, duration_seconds=-1) -> Job:
    custom_logger.debug(f"添加定时任务 {async_callback.__name__} 间隔时间 {interval_seconds}秒 持续时间 {duration_seconds}秒")
    timer_job = main_scheduler.add_job(async_callback, 'interval', seconds=interval_seconds)
    if not main_scheduler.running:
        main_scheduler.start()
    if duration_seconds > 0:
        def remove_job():
            try:
                custom_logger.debug(f"定时任务已执行{duration_seconds}秒 移除定时任务")
                timer_job.remove()
            except Exception as e:
                custom_logger.error(f"移除定时任务异常 {e}")
        asyncio.get_event_loop().call_later(duration_seconds, remove_job)
    return timer_job


async def run():
    main_scheduler.start()
    await asyncio.Event().wait()
