import json
import munch
import typing

from harmony_config.backends import BaseHarmonyConfigurationProvider, ConfigValueT


class JsonHarmonyConfigurationProvider(BaseHarmonyConfigurationProvider):
    _provider_name = "json"

    def __init__(self, metadata: munch.Munch):
        if not hasattr(metadata, 'config_file_location'):
            raise RuntimeError("JSON configuration provider has no config_file_location metadata")

        self.config_store = None
        self.config_file_location = metadata.config_file_location

    def load_configuration(self) -> typing.NoReturn:
        with open(self.config_file_location, "r") as f:
            self.config_store = munch.munchify(json.load(f))

    def is_configuration_available(self) -> bool:
        return self.config_store is not None

    def is_writable(self) -> bool:
        return False

    def get_configuration_key(
            self,
            key: str,
            expected_type: ConfigValueT = str,
            required: bool = False,
            or_else: ConfigValueT = None
    ) -> typing.Optional[ConfigValueT]:
        subkeys = key.split('.')
        value = self.config_store

        for subkey in subkeys:
            if hasattr(value, subkey):
                value = getattr(value, subkey)
            else:
                value = None
                break

        if required and value is None:
            raise RuntimeError(f"Required key {key} was not found in the configuration.")

        if type(value) is not expected_type:
            raise RuntimeError(f"Value at {key} should be of type {expected_type.__name__}, "
                               f"but is a {type(value).__name__}")

        return value if value is not None else or_else

    def set_configuration_key(self, key: str, new_value: ConfigValueT) -> typing.NoReturn:
        raise RuntimeError("JSON configuration is not writable.")
