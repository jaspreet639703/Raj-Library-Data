import asyncio
from scraper.main import run

async def main():
    print("Starting continuous background worker...")
    while True:
        try:
            print("Worker: Starting a scraping run...")
            await run()
            print("Worker: Finished a full pass over the locations. Sleeping for 1 hour before checking again...")
        except Exception as e:
            print(f"Worker: Error in scraping run: {e}")
        
        # Sleep for 1 hour before running again
        # This keeps the worker alive and checking if new tehsils are added or checkpoints reset
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
