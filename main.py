import logging
import sys
import time

import typer
import os
import json
from pathlib import Path
from saucenao_api.containers import SauceResponse
from saucenao_api import SauceNao
from typing_extensions import Annotated

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

app = typer.Typer()

DEFAUL_FORMAT = "[{author}]{title}{extension}"


def select_result(results: SauceResponse):
    for i, result in enumerate(results):
        print(f"{i}: {result.title} by {result.author}")
    print("Select result:")
    selection = int(input())
    return results[selection]


@app.command()
def run_once(source_dir: Annotated[Path, typer.Argument(
    resolve_path=True, exists=True, file_okay=False, dir_okay=True, readable=True)],
             api_key: Annotated[str, typer.Option(help="Saucenao API-Key")] = None,
             debug: Annotated[bool, typer.Option(help="Debug mode")] = False,
             log_file: Annotated[Path, typer.Option(help="Log file")] = None,
             force_overwrite: Annotated[bool, typer.Option(help="Force overwrite of existing json files")] = False,
             rename: Annotated[bool, typer.Option(help="Rename files")] = False,
             rename_format: Annotated[str, typer.Option(help="Format for renaming files")] = DEFAUL_FORMAT):
    if not api_key:
        # TODO: Check if API-key in config file
        logging.warning("No API-Key provided")
        api_key = os.getenv("SAUCENAO_API_KEY")
        if not api_key:
            logging.error("No API-Key found in env")
            raise typer.Exit(code=1)
    if debug:
        logger.setLevel(logging.DEBUG)
    if log_file:
        handler = logging.FileHandler(log_file)
        logger.addHandler(handler)
    logger.debug(f"Source dir: {source_dir}")
    logger.debug(f"API-Key: {api_key}")

    saucenao = SauceNao(api_key=api_key)
    for file in source_dir.iterdir():
        if file.is_file():
            if file.suffix not in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
                logger.debug(f"Skipping {file} because it is not an image")
                continue
            # If json file already exists, skip
            if not force_overwrite and file.with_suffix(file.suffix + ".json").exists():
                logger.debug(f"Skipping {file} because json file already exists")
                results = SauceResponse(file.with_suffix(file.suffix + ".json").open("r"))
            else:
                logger.info(f"Searching {file}")
                results = saucenao.from_file(file.open("rb"))

            if results and rename:
                logger.debug(f"Results: {results}")
                logger.info(f"Found {len(results)} results for {file}")
                logger.debug(f"Results: {results}")
                result = select_result(results)
                author = result.author if result.author else "Unknown"
                title = result.title if result.title else "Unknown"
                new_file_name = rename_format.format(author=author, title=title,
                                                     extension=file.suffix)
                logger.debug(f"New file name: {new_file_name}")
                new_path = file.rename(file.with_name(new_file_name))
                with new_path.with_suffix(new_path.suffix + ".json").open("w") as f:
                    json.dump(results.raw, f, indent=4)
            else:
                logger.info(f"No results found for {file}")
            if results.long_remaining <= 0:
                logger.warning(f"API-Key has no more requests left. Wait 24 hours or change API-Key")
            if results.short_remaining <= 0:
                logger.info(f"API-Key has no more requests left. Waiting 30 seconds")
                time.sleep(30)


if __name__ == "__main__":
    app()
