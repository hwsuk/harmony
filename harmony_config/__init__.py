import os
import json
import munch
import typing
import inspect
import importlib

from loguru import logger
from harmony_config.backends import BaseHarmonyConfigurationProvider

config = None
_providers: typing.Dict[str, typing.Type[BaseHarmonyConfigurationProvider]] = {}

if not config:
    logger.info("Resolving configuration provider...")

    # Load the default config file to get info about which provider to configure.
    with open("config.json", "r") as f:
        _cfg = munch.munchify(json.load(f))

    # Is a provider configured?
    if not hasattr(_cfg, 'configuration_provider'):
        raise RuntimeError("A configuration provider is not configured.")

    _cfg = _cfg.configuration_provider

    if not hasattr(_cfg, 'name') or not hasattr(_cfg, 'metadata'):
        raise RuntimeError("A configuration provider is not configured.")

    # Determine the configuration provider to use on startup.
    _config_provider_name = _cfg.name

    # Search the configuration providers and check that they're valid.
    if not _providers:
        _backends_package_dir = os.path.join(os.path.dirname(__file__), 'backends')
        _module_names = [module.replace(".py", "")
                         for module in os.listdir(_backends_package_dir)
                         if module.endswith(".py")
                         and module != "__init__.py"]

        for module_name in _module_names:
            # For each module, import all the classes and see if any are valid configuration providers.
            _module = importlib.import_module(f"harmony_config.backends.{module_name}")

            # We don't want to check the base class so filter it out.
            _classes = [member[1] for member in inspect.getmembers(_module) if inspect.isclass(member[1])]
            _classes = list(filter(lambda cls: cls != BaseHarmonyConfigurationProvider, _classes))

            for _provider_class in _classes:
                if not issubclass(_provider_class, BaseHarmonyConfigurationProvider):
                    raise RuntimeError(f"Configuration provider class '{module_name}' "
                                       f"is not an instance of BaseHarmonyConfigurationProvider")

                if not hasattr(_provider_class, "_provider_name") or type(getattr(_provider_class, "_provider_name")) is not str:
                    raise RuntimeError(f"Configuration provider '{_provider_class.__name__}' "
                                       f"does not have a _provider_name value")

                _provider_name = getattr(_provider_class, "_provider_name")

                if _provider_name in _providers.keys():
                    raise RuntimeError(f"Configuration provider has duplicate name: "
                                       f"tried to add a {_provider_class} called '{_provider_name}' but there's already"
                                       f"a '{_provider_name}' of type {type(_providers[_provider_name])}")

                _providers[_provider_name] = _provider_class

    # If no providers were found, fail.
    if not _providers:
        raise RuntimeError("No valid configuration providers were found.")

    try:
        _preferred_provider_module = _providers[_config_provider_name]
    except KeyError:
        raise RuntimeError(f"Invalid configuration provider specified: "
                           f"got '{_config_provider_name}', but only [{', '.join(_providers.keys())}] are registered")

    config = _preferred_provider_module(metadata=_cfg.metadata)
    config.load_configuration()
