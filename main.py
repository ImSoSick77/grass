import asyncio
import random
import uuid
import aiohttp
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_random, retry_if_exception_type
from core.utils import logger
from core.utils.accounts_db import AccountsDB
from core.utils.exception import (
    LoginException, ProxyBlockedException, ProxyForbiddenException, ProxyError,
    WebsocketConnectionFailedError, SiteIsDownException, FailureLimitReachedException
)
from better_proxy import Proxy

class Grass:
    def __init__(self, _id, email, password, proxy=None, db=None):
        self.id = _id
        self.email = email
        self.password = password
        self.proxy = Proxy.from_str(proxy).as_url if proxy else None
        self.db = db
        self.session = aiohttp.ClientSession(trust_env=True, connector=aiohttp.TCPConnector(ssl=False))
        self.fail_count = 0
        self.limit = 7

    async def start(self):
        """Main mining process."""
        logger.info(f"{self.id} | Starting mining for {self.email} using proxy {self.proxy}...")

        while True:
            try:
                self.check_site_status()
                user_id = await self.login()
                browser_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.proxy or ""))
                await self.mine(browser_id, user_id)

            except LoginException as e:
                logger.warning(f"{self.id} | Login failed: {e}")
                break
            except ProxyBlockedException:
                logger.warning(f"{self.id} | Proxy blocked. Changing proxy...")
                await self.change_proxy()
            except ProxyError:
                logger.warning(f"{self.id} | Proxy error. Retrying with a new proxy...")
                await self.change_proxy()
            except WebsocketConnectionFailedError:
                logger.warning(f"{self.id} | Websocket connection failed. Retrying...")
                self.fail_count += 1
            except SiteIsDownException:
                logger.warning(f"{self.id} | Site is down. Retrying later...")
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"{self.id} | Unexpected error: {e}")

            if self.fail_count >= self.limit:
                logger.error(f"{self.id} | Too many failures. Stopping mining for {self.email}.")
                break

    async def mine(self, browser_id, user_id):
        """Simulate mining actions."""
        while True:
            try:
                await asyncio.sleep(random.randint(100, 120))
                logger.info(f"{self.id} | Mining grass for {self.email}...")
            except Exception as e:
                logger.error(f"{self.id} | Error during mining: {e}")
                break

    async def login(self):
        """Simulate login to the platform."""
        logger.info(f"{self.id} | Logging in with {self.email}...")
        await asyncio.sleep(random.uniform(1, 2))  # Simulate network delay
        if random.random() > 0.9:  # Simulate login failure
            raise LoginException("Login failed due to invalid credentials.")
        return str(uuid.uuid4())

    async def change_proxy(self):
        """Change proxy to a new one."""
        self.proxy = await self.get_new_proxy()
        logger.info(f"{self.id} | Changed proxy to {self.proxy}")

    async def get_new_proxy(self):
        """Fetch a new proxy from the database."""
        if not self.db:
            logger.error("Proxy database not available!")
            raise ProxyError("No proxy database.")
        proxy = await self.db.get_new_proxy()
        if not proxy:
            logger.error("No proxies available in the database!")
            raise ProxyError("No proxies left.")
        return Proxy.from_str(proxy).as_url

    def check_site_status(self):
        """Check if the site is accessible."""
        if random.random() > 0.95:  # Simulate site down
            raise SiteIsDownException("Site is currently down.")

    async def close(self):
        """Close the session."""
        await self.session.close()

async def main():
    accounts = ["user1@example.com:password1", "user2@example.com:password2"]
    proxies = ["proxy1", "proxy2"]

    db = AccountsDB("proxy_database.db")
    await db.connect()

    tasks = []
    for i, account in enumerate(accounts):
        proxy = proxies[i % len(proxies)]
        grass = Grass(i + 1, *account.split(":"), proxy, db)
        tasks.append(grass.start())

    await asyncio.gather(*tasks)
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
