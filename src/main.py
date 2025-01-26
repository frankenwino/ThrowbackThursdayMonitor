import asyncio
from checker import WebChecker
from pathlib import Path

async def main():
    url: str = "https://www.boras.se/upplevaochgora/kulturochnoje/borasbiorodakvarn/throwbackthursday.4.706b03641584ebf5394d6c1a.html"
    directory: Path = Path(__file__).resolve().parent
    db_file_path: Path = Path(directory, 'db.json')
    
    web_checker = WebChecker(url=url, db_file_path=db_file_path)
    await web_checker.go()

if __name__ == "__main__":
    asyncio.run(main())