import os
import typing
import inspect
import importlib

from loguru import logger
from discord.ext import commands

_cog_cache: typing.Dict[str, typing.Type[commands.Cog]] = {}

# On startup, all cogs in the harmony_cogs package will be resolved, and added to a cache.
# We can use this to load cogs on startup.
if not _cog_cache:
    logger.info("Resolving cogs...")

    # Get a list of all of the module files that might contain cogs.
    _cogs_package_dir = os.path.dirname(__file__)
    _module_names = [module.replace(".py", "")
                     for module in os.listdir(_cogs_package_dir)
                     if module.endswith(".py")
                     and module != "__init__.py"]

    for module_name in _module_names:
        _module = importlib.import_module(f"harmony_cogs.{module_name}")

        # Get only classes which appear to be cogs
        _classes = [member[1] for member in inspect.getmembers(_module) if inspect.isclass(member[1])]
        _classes = list(filter(lambda cls: issubclass(cls, commands.Cog), _classes))

        for _cog_class in _classes:
            # Check if the cog has a _cog_name, if not then error out
            if not hasattr(_cog_class, "_cog_name"):
                raise RuntimeError(f"Cog {_cog_class.__name__} does not have a _cog_name value.")

            # Get the _cog_name
            _cog_name = getattr(_cog_class, "_cog_name")

            logger.debug(f"Resolved cog called {_cog_name}; class name {_cog_class.__name__}")

            # Check if there are any duplicate names
            if _cog_name in _cog_cache:
                raise RuntimeError(f"Cog has duplicate name:"
                                   f"tried to add a {_cog_class.__name__} called '{_cog_name}' but there's already a"
                                   f"{_cog_name} of type {type(_cog_cache[_cog_name])}")

            _cog_cache[_cog_name] = _cog_class

logger.info(f"Resolved {len(_cog_cache)} cogs:")

for cog_name, cog_class in _cog_cache.items():
    logger.info(f"{cog_name}: {cog_class.__name__}")


def fetch_cog_by_name(name: str) -> typing.Type[commands.Cog]:
    """
    Fetch a cog by its name.
    :param name: The name of the cog to load.
    :return: The cog class, if found. Otherwise, a KeyError will be thrown
    """
    try:
        return _cog_cache[name]
    except KeyError as e:
        raise KeyError(f"A cog with name {name} was not found.") from e


def get_cog_cache() -> typing.Dict[str, typing.Type[commands.Cog]]:
    """
    Get the loaded cog cache.
    :return: The cog cache.
    """
    return _cog_cache
