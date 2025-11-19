__id__ = "russian-retro-translator"
__name__ = "Pre-reform Russian style for messages"
__description__ = "Make your messages in retro russian style!\nAuthor: @Altairgeo\nSource: https://github.com/AltairGeo/prerevolution-russian-plugin"
__author__ = "@Altairgeo"
__version__ = "0.1.0"
__icon__ = "exteraPlugins/1"
__min_version__ = "11.12.0"


"""
Data creation: 19.11.2025
Sources: https://github.com/AltairGeo/prerevolution-russian-plugin
Создано с любовью <3
"""

from base_plugin import BasePlugin, HookResult, HookStrategy
from ui.settings import Header, Input, Switch, Text, Divider
from typing import Any, Dict, List
from file_utils import get_cache_dir, read_file, write_file
from pathlib import Path
from copy import copy
import json
import requests
from string import punctuation



# Константы

DEFAULT_DICT_ADDRESS = "https://pub.files.delroms.ru/pre_rev_dict.json"

CONSONANTS = ("б", "в", "г", "д", "ж", "з", "й", "к", "л", "м", "н", "п", "р", "с", "т", "ф", "х", "ц", "ч", "ш", "щ")
VOWELS = ("а", "е", "ё", "и", "о", "у", "ы", "э", "ю", "я")

# Слова игнорируемые для перевода
EXCEPT_WORDS = ("он", "и")


class WordPresent:
    """
    Класс для представления слова, инкапсулирует логику перевода с современного на дореформенный.
    Для перевода слова присутствуют 2 способа:
        1. Найти в словаре который представляется ввиде хэш-таблицы.
        2. Воспользоваться упрощённым алгоритмом для перевода, реализованным в методе `__simplificate_translate_to_old_style`, если слово не найдено в словаре.

    Использует __slots__ для оптимизации.
    Все слова обрабатываются в нижнем регистре.

    Attributes:
        self.origin - Исконное слово
        self._rus_dict - Переданный словарь с переводами слов.
        self.is_title - Флак обозначающий начиналось ли слово с заглавной буквы.

    Реализует методы:
        __simplificate_translate_to_old_style - упрощённый перевод на дореформенный.
        old - Параметр-интерфейс для перевода в дореформенный.
        from_text - classmethod для преобразования текста в список объектов WordPresent.
        from_words_to_str - Статичный метод для преобразования списка объектов WordPresent в переведённую строку.
    """
    __slots__ = ("is_title", "_rus_dict", "origin")

    def __init__(self, word: str, rus_dict: Dict[str, str]) -> None:
        self.origin = word
        self._rus_dict = rus_dict
        self.is_title = word.istitle()

    def __simplificate_translate_to_old_style(self) -> str:
        """
        Реализация алгоритма упрощённого перевода на дореформенный.

        Работа алгоритма:
            1. Если слово оканчивается на согласную, то добавляем в конец твёрдый знак.
            2. Если после буквы "и" идёт гласная, то буква "и" становится буквой "i"
        """
        old_str = copy(self.origin)

        if old_str[-1] in CONSONANTS:
            old_str += "ъ"

        result_chars = []
        i = 0
        while i < len(old_str):
            current_char = old_str[i]
            if current_char == "и" and i + 1 < len(old_str) and old_str[i + 1] in VOWELS:
                result_chars.append("i")
                i += 1
            else:
                result_chars.append(current_char)
                i += 1

        return "".join(result_chars)


    @property
    def old(self) -> str:
        """
        property-метод используемый в качестве интерфейса для перевода на дореформенный.
        Логика:
            Если слово в списке исключений или слово является знаком пунктуации, то отдаёт оригинал слова.
            Ищет слово в словаре, если не найдено, то прогоняет через упрощённый алгоритм перевода.
        """
        if self.origin in EXCEPT_WORDS or self.origin in punctuation:
            return self.origin

        old_word = self._rus_dict.get(self.origin.lower())

        if not old_word:
            old_word = self.__simplificate_translate_to_old_style()

        return old_word if not self.is_title else old_word.title()

    @classmethod
    def from_text(cls, text: str, ru_dict: dict) -> List["WordPresent"]:
        """
        Метод для преобразования текста в набор объектов WordPresent.
        Логика работы:
            1. Разбивает текст по пробелам.
            2. Отделяет от слова знаки пунктуации если таковые присутствуют.
            3. Создаёт список объектов и возвращает его.
        """
        dirt_list_of_words = text.split(" ")

        list_sepparated = []
        for i in dirt_list_of_words:
            if not i:
                continue

            if i[0] in punctuation:
                list_sepparated.append(i[0])
                i = i[1:]
            elif i[-1] in punctuation:
                list_sepparated.append(i[-1])
                i = i[:-1]
            list_sepparated.append(i)

        return [cls(i, ru_dict) for i in list_sepparated] # type: ignore

    @staticmethod
    def from_words_to_str(words: List["WordPresent"]) -> str:
        """
        Статический метод для склеивания списка объектов-слов в переведённую строку.
        Логика работы:
            1. Создать новый список с переведёнными строками.
            2. Склеить список переведённых слов по след. правилам:
                1. Если слово первое, то записываем как есть.
                2. Если это знак пунктуации, то записываем как есть.
                3. В остальных случаях добавляем перед словом пробел.
            3. Возвращаем результат конкатенации строк.
        """
        final_str = ""
        list_of_strs = [i.old for i in words]
        for i, v in enumerate(list_of_strs, start=0):
            if i == 0 or v in punctuation:
                pass
            else:
                v = f" {v}"
            final_str += v
        return final_str


class ChadTranslator(BasePlugin):
    """
    Класс плагина.
    В своём состоянии хранит словарь русско-современных --- русско-дореформенных слов, ввиде хэш-таблицы.

    Инкапсулирует логику проверки и загрузки русско-русского словаря.
    Реализует хук для работы с сообщением перед отправкой.
    Управляет настройками плагина.
    """
    def __init__(self) -> None:
        super().__init__()
        self.rus_dict: Dict[str, str] | None = None

    def on_plugin_load(self) -> None:
        self.add_on_send_message_hook()
        self._check_rus_dict()

    def _check_rus_dict(self) -> None:
        url_dict: str = self.get_setting("url_of_modern_retro_dict") or DEFAULT_DICT_ADDRESS
        path_to_dict = Path(get_cache_dir() + url_dict.split("/")[-1])

        # If dictionary exist
        if self.rus_dict is not None:
            return


        # Try to load from cache
        try:
            if path_to_dict.exists():
                str_json = read_file(str(path_to_dict))
                rus_dict_f = json.loads(str_json)
                if rus_dict_f:
                    self.rus_dict = rus_dict_f
                    return
        except Exception:
            pass

        # Download from server
        try:
            resp = requests.get(url_dict)
            if resp.status_code != 200:
                raise Exception("bad status")

            write_file(str(path_to_dict), resp.text)
            rus_dict = json.loads(resp.text)

            if not rus_dict:
                raise Exception()

            self.rus_dict = rus_dict
        except Exception:
            raise ValueError("Не удалось загрузить или обработать словарь.")


    def on_send_message_hook(self, account: int, params: Any) -> HookResult:
        enabled = self.get_setting("translator_enabled")
        if enabled is None:
            enabled = True
        if enabled is True:
            self._check_rus_dict()
            if not self.rus_dict:
                raise Exception("Словарь не инициализирован!")
            words = WordPresent.from_text(params.message, self.rus_dict)
            message = WordPresent.from_words_to_str(words)
            params.message = message
            return HookResult(strategy=HookStrategy.MODIFY, params=params)

        return HookResult(strategy=HookStrategy.DEFAULT, params=params)


    def create_settings(self):
        return [
            Header("Main settings"),
            Switch(key="translator_enabled", text="Enable a translator", default=True),
            Input(key="url_of_modern_retro_dict", text="URL address of dict Modern-Old Russian", default=DEFAULT_DICT_ADDRESS),
        ]
