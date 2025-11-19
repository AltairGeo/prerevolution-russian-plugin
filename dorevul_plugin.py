__id__ = "russian-retro-translator"
__name__ = "Pre-Revolutionary Translator"
__description__ = "Make your messages in retro russian style!"
__author__ = "AltairGeo"
__version__ = "0.0.1"
__icon__ = "exteraPlugins/1"
__min_version__ = "11.12.0"

from base_plugin import BasePlugin, HookResult, HookStrategy
from ui.settings import Header, Switch
from typing import Any

class ChadTranslator(BasePlugin):
    def __init__(self) -> None:
        super().__init__()

    def on_plugin_load(self) -> None:
        self.add_on_send_message_hook()

    def on_send_message_hook(self, account: int, params: Any) -> HookResult:

        if self.get_setting("translator_enabled") is True:
            params.message = "Гойда"
            return HookResult(strategy=HookStrategy.MODIFY, params=params)

        return HookResult(strategy=HookStrategy.DEFAULT)


    def create_settings(self):
        return [
            Header("Pre-Revolution Style"),
            Switch(key="translator_enabled", text="Enable a translator", default=True),
        ]
