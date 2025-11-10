import argparse
import asyncio
import logging
import time
from aiohttp import ClientSession, TCPConnector

# Configure logging
logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class AsyncRequestSender:
    def __init__(self, url, total_requests=100000, concurrency=1000, max_retries=3):
        self.url = url
        self.total_requests = total_requests
        self.concurrency = concurrency
        self.max_retries = max_retries
        self.success_count = 0
        self.failure_count = 0
        self.semaphore = asyncio.Semaphore(concurrency)

    async def send_request(self, session):
        async with self.semaphore:
            for attempt in range(self.max_retries + 1):
                try:
                    async with session.get(self.url) as response:
                        if response.status == 200:
                            return True
                        return False
                except Exception as e:
                    if attempt == self.max_retries:
                        logger.error(f'Request failed after {self.max_retries} attempts: {str(e)}')
                        return False
                    await asyncio.sleep(0.5 * attempt)

    async def worker(self, session):
        while True:
            if self.success_count + self.failure_count >= self.total_requests:
                return

            success = await self.send_request(session)
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1

            if (self.success_count + self.failure_count) % 1000 == 0:
                logger.info(f'Progress: {self.success_count + self.failure_count}/{self.total_requests} '
                            f'Success: {self.success_count} Failed: {self.failure_count}')

    async def run(self):
        connector = TCPConnector(limit=0, ssl=False)
        async with ClientSession(connector=connector) as session:
            workers = [asyncio.create_task(self.worker(session)) for _ in range(self.concurrency)]
            await asyncio.gather(*workers)


async def main():
    parser = argparse.ArgumentParser(description='Send multiple async HTTP requests')
    parser.add_argument('--url', type=str, required=True, help='Target URL')
    parser.add_argument('--requests', type=int, default=100000, help='Total number of requests')
    parser.add_argument('--concurrency', type=int, default=1000, help='Number of concurrent requests')
    parser.add_argument('--retries', type=int, default=3, help='Max retries per request')

    args = parser.parse_args()

    start_time = time.time()

    sender = AsyncRequestSender(
        url=args.url,
        total_requests=args.requests,
        concurrency=args.concurrency,
        max_retries=args.retries
    )

    await sender.run()

    duration = time.time() - start_time
    logger.info(f'Completed {sender.success_count + sender.failure_count} requests in {duration:.2f} seconds')
    logger.info(f'Success rate: {sender.success_count / (sender.success_count + sender.failure_count) * 100:.2f}%')
    logger.info(f'Requests per second: {(sender.success_count + sender.failure_count) / duration:.2f}')


if __name__ == '__main__':
    asyncio.run(main())