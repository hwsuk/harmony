import abc
import typing

import munch

ConfigValueT = typing.TypeVar('ConfigValueT')


class BaseHarmonyConfigurationProvider(abc.ABC):
    @abc.abstractmethod
    def __init__(self, metadata: munch.Munch):
        """
        Construct an instance of this ConfigurationProvider.
        :param metadata: The metadata used as extra configuration for the provider.
        """
        pass

    @abc.abstractmethod
    def load_configuration(self) -> typing.NoReturn:
        """
        Load the configuration from the configuration store as required.
        :return: Nothing.
        """
        pass

    @abc.abstractmethod
    def is_configuration_available(self) -> bool:
        """
        Helper method used to determine if the configuration store is able to have values read from it.
        :return: True if the configuration store is available for use, otherwise False.
        """
        pass

    @abc.abstractmethod
    def is_writable(self) -> bool:
        """
        Helper method used to determine if the configuration can be updated from within the application.
        :return: True if the configuration can be written to, otherwise False.
        """
        pass

    @abc.abstractmethod
    def get_configuration_key(
            self,
            key: str,
            expected_type: ConfigValueT = str,
            required: bool = False,
            or_else: ConfigValueT = None
    ) -> typing.Optional[ConfigValueT]:
        """
        Get the specified key from the configuration store.
        Nested keys are demarcated using a dot (.).
        :param key: The configuration key to fetch.
        :param expected_type: The type of the value that should be returned.
        If this differs from the type of value that the backing store returns, an exception will be raised.
        :param required: If True, an exception will be raised instead of returning None if no value is present.
        :param or_else: If not None, this value will be returned if no value is present in the backing store.
                        Should not be used in conjunction with required.
        :return: The value of the key, or None if the key is not found.
        """
        pass

    @abc.abstractmethod
    def set_configuration_key(
            self,
            key: str,
            new_value: ConfigValueT
    ) -> typing.NoReturn:
        """
        Change the value of a configuration key, updating the configuration store in turn.
        Nested keys are demarcated using a dot (.).
        :param key: The key to update.
        :param new_value: The new value of the key.
        :return: Nothing.
        """
        pass
