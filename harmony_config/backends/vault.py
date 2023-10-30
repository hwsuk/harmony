import munch
import typing

from harmony_config.backends import BaseHarmonyConfigurationProvider, ConfigValueT


class VaultHarmonyConfigurationProvider(BaseHarmonyConfigurationProvider):

    _provider_name = "vault"

    def __init__(self, metadata: munch.Munch):
        raise NotImplementedError("Vault configuration is not supported yet.")

    def load_configuration(self) -> typing.NoReturn:
        pass

    def is_configuration_available(self) -> bool:
        pass

    def is_writable(self) -> bool:
        pass

    def get_configuration_key(self, key: str, expected_type: ConfigValueT = str, required: bool = False,
                              or_else: ConfigValueT = None) -> typing.Optional[ConfigValueT]:
        pass

    def set_configuration_key(self, key: str, new_value: ConfigValueT) -> typing.NoReturn:
        pass