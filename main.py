import asyncio
import ctypes
import random
import sys
import traceback

import aiohttp
from art import text2art
from termcolor import colored, cprint

from better_proxy import Proxy

from core import Grass
from core.utils import logger, file_to_list
from core.utils.accounts_db import AccountsDB
from core.utils.exception import LoginException, RegistrationException
from data.config import ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH, THREADS, REGISTER_DELAY, CLAIM_REWARDS_ONLY, MINING_MODE


def bot_info(name: str = ""):
    cprint(text2art(name), 'green')
    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetConsoleTitleW(f"{name}")
    print(f"{colored('EnJoYeR <crypto/> moves:', color='light_yellow')} {colored('https://t.me/+tdC-PXRzhnczNDli', color='light_green')}")


class ProxyManager:
    def __init__(self, proxies):
        self.proxy_map = {proxy: None for proxy in proxies}  # Map proxy to the account using it

    def get_proxy_for_account(self, account):
        for proxy, assigned_account in self.proxy_map.items():
            if assigned_account is None or assigned_account == account:
                self.proxy_map[proxy] = account
                return proxy
        raise Exception("No available proxies for this account.")

    def release_proxy(self, proxy):
        if proxy in self.proxy_map:
            self.proxy_map[proxy] = None


async def validate_proxy(proxy_url: str) -> bool:
    """Проверка прокси перед использованием."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://httpbin.org/ip", proxy=proxy_url, timeout=10) as response:
                return response.status == 200
    except Exception:
        return False


async def worker_task(_id, account: str, proxy_manager: ProxyManager, db: AccountsDB = None):
    email, password = account.split(":")[:2]
    grass = None
    proxy = None

    try:
        proxy = proxy_manager.get_proxy_for_account(account)
        grass = Grass(_id, email, password, proxy, db)

        if MINING_MODE:
            await asyncio.sleep(random.uniform(1, 2) * _id)
            logger.info(f"Starting №{_id} | {email} | {proxy}")
            await grass.start()
        elif CLAIM_REWARDS_ONLY:
            await grass.claim_rewards()
        return True

    except (LoginException, RegistrationException) as e:
        logger.warning(f"{_id} | {e}")
    except Exception as e:
        logger.error(f"{_id} | Unexpected error: {e} {traceback.format_exc()}")
    finally:
        if proxy:
            proxy_manager.release_proxy(proxy)
        if grass:
            await grass.session.close()


async def main():
    accounts = file_to_list(ACCOUNTS_FILE_PATH)
    proxies = [Proxy.from_str(proxy).as_url for proxy in file_to_list(PROXIES_FILE_PATH)]

    if not accounts:
        logger.warning("No accounts found!")
        return

    if not proxies:
        logger.warning("No proxies found!")
        return

    db = AccountsDB("proxy_database.db")
    await db.connect()

    # Проверка и фильтрация прокси
    valid_proxies = []
    for proxy in proxies:
        if await validate_proxy(proxy):
            valid_proxies.append(proxy)
        else:
            logger.warning(f"Invalid proxy: {proxy}")

    if not valid_proxies:
        logger.error("No valid proxies available!")
        return

    proxy_manager = ProxyManager(valid_proxies)

    tasks = []
    for i, account in enumerate(accounts):
        tasks.append(worker_task(i + 1, account, proxy_manager, db))

    await asyncio.gather(*tasks)
    await db.close_connection()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    bot_info("GRASS_AUTO")
    asyncio.run(main())
