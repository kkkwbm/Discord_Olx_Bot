import asyncio
import os
import sys
import dataset
import dotenv
import hikari
import lightbulb
from loguru import logger as log
from loguru._datetime import datetime

from scraper import generate_embed, scrape  # The OLX scraper and embed generation functions
from requests.exceptions import ConnectionError
from urllib3.exceptions import MaxRetryError
from loguru import logger as log  # Ensure 'loguru' logger is properly imported


dotenv.load_dotenv()

bot = lightbulb.BotApp(token=os.getenv("TOKEN"))  # Initialize the bot with the Discord token
db = dataset.connect("sqlite:///olx_subscriptions.db")  # Database to store subscriptions
table = db["subscriptions"]  # Subscriptions table in the database


def restart_program():
    try:
        print("Restarting the program...")
        python = sys.executable
        script_path = os.path.abspath(sys.argv[0])

        # Wrap paths with spaces in double quotes to avoid issues
        os.execl(python, python, script_path, *sys.argv[1:])
    except Exception as e:
        print(f"Failed to restart program: {e}")

# Function to handle the background scraping task
async def run_background() -> None:
    log.info("OLX Scraper started.")

    while True:
        try:
            log.info("Executing scraping loop")
            for sub in db["subscriptions"]:
                print(sub)
                # Scrape offers based on each subscription (URL, channel)
                items = scrape(db, sub)
                log.debug(f"{len(items)} items found for subscription ID {sub['id']}")

                for item in items:
                    embed = generate_embed(item, sub["id"])  # Create an embed for Discord
                    await bot.rest.create_message(sub["channel_id"], embed=embed)  # Send to Discord

                # Update the last_sync field if new items were found
                if len(items) > 0:
                    try:
                        # Ensure you are converting only a valid timestamp
                        last_sync_timestamp = int(datetime.now().timestamp())
                        table.update(
                            {
                                "id": sub["id"],
                                "last_sync": last_sync_timestamp,
                            },
                            ["id"],
                        )
                    except ValueError as e:
                        log.error(f"Failed to update last_sync due to a ValueError: {e}")

            log.info(f"Sleeping for {os.getenv('INTERVAL', 60)} seconds")
            await asyncio.sleep(int(os.getenv("INTERVAL", 60)))  # Wait between scraping runs
        except (ConnectionError, MaxRetryError) as e:
            log.error(f"Connection error occurred: {e}. Retrying in 10 seconds...")
            await asyncio.sleep(10)
        except KeyError as e:
            log.error(f"Key error occurred: {e}. Skipping to the next subscription.")
        except Exception as e:
            log.error(f"An unexpected error occurred: {e}")
            # Restart if the error is critical or otherwise can't continue
            restart_program()


# Discord bot event handler to mark the bot as ready
@bot.listen(hikari.ShardReadyEvent)
async def ready_listener(_):
    log.info("Bot is ready")
    log.info(f"{table.count()} subscriptions registered")
    asyncio.create_task(run_background())  # Start the background task


@bot.command()
@lightbulb.option("excluded_words", "Words to exclude from the offers (space-separated)", type=str, required=False, default="")
@lightbulb.option("url", "URL to OLX search", type=str, required=True)
@lightbulb.option("channel", "Channel to receive alerts", type=hikari.TextableChannel, required=True)
@lightbulb.command("subscribe", "Subscribe to an OLX search")
@lightbulb.implements(lightbulb.SlashCommand)
async def subscribe(ctx: lightbulb.Context) -> None:
    # Check if excluded_words is provided and handle it
    excluded_words = ctx.options.excluded_words.split() if ctx.options.excluded_words else []

    # Store the subscription with excluded_words
    table.insert({
        "url": ctx.options.url,
        "channel_id": ctx.options.channel.id,
        "excluded_words": " ".join(excluded_words),  # Store space-separated excluded words
        "last_sync": -1
    })
    log.info(f"Subscription created for {ctx.options.url} with excluded words: {excluded_words}")
    await ctx.respond(f"✅ Created subscription with excluded words: {', '.join(excluded_words) if excluded_words else 'None'}")



# Command to list all subscriptions
@bot.command()
@lightbulb.command("subscriptions", "Get a list of subscriptions")
@lightbulb.implements(lightbulb.SlashCommand)
async def subscriptions(ctx: lightbulb.Context) -> None:
    embed = hikari.Embed(title="Subscriptions")
    for sub in table:
        embed.add_field(name="#" + str(sub["id"]), value=sub["url"])
    await ctx.respond(embed)


# Command to unsubscribe from a search
@bot.command()
@lightbulb.option("id", "ID of the subscription", type=int, required=True)
@lightbulb.command("unsubscribe", "Unsubscribe from a search")
@lightbulb.implements(lightbulb.SlashCommand)
async def unsubscribe(ctx: lightbulb.Context) -> None:
    table.delete(id=ctx.options.id)
    log.info(f"Deleted subscription #{ctx.options.id}")
    await ctx.respond(f"🗑 Deleted subscription #{ctx.options.id}.")


if __name__ == "__main__":
    if os.name != "nt":
        import uvloop

        uvloop.install()

    # Start the bot and set the status
    bot.run(activity=hikari.Activity(name="OLX articles!", type=hikari.ActivityType.WATCHING))


