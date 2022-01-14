# NOTE: This is no good.. doesn't supply signal strength value of devices

import asyncio
import bleak
from bleak import discover

async def main():
    devices = await discover()
    for d in devices:
        print(d)


if __name__ == "__main__":
    asyncio.run(main())