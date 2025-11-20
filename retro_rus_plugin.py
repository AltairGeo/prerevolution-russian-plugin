from enum import Enum
from base_plugin import BasePlugin, HookResult, HookStrategy
from ui.settings import Divider, Header, Input, Switch, Text
from typing import Any, Dict, List
from file_utils import delete_file, get_cache_dir, read_file, write_file
from pathlib import Path
from copy import copy
import json
import requests
from string import punctuation
from urllib.parse import urlparse
import re
from ui.alert import AlertDialogBuilder
from client_utils import get_last_fragment
from android_utils import log
from ui.bulletin import BulletinHelper
from client_utils import get_last_fragment

__id__ = "russian-retro-translator"
__name__ = "Pre-reform Russian style for messages"
__description__ = "Make your messages in retro russian style!\nAuthor: @Altairgeo\nSource: https://github.com/AltairGeo/prerevolution-russian-plugin"
__author__ = "@Altairgeo"
__version__ = "0.1.1"
__icon__ = "DorevForm/0"
__min_version__ = "11.12.0"


"""
Data creation: 19.11.2025
Sources: https://github.com/AltairGeo/prerevolution-russian-plugin
Создано с любовью <3
"""


# Константы

DEFAULT_DICT_ADDRESS = "https://pub.files.delroms.ru/pre_rev_dict.json"

CONSONANTS = (
    "б",
    "в",
    "г",
    "д",
    "ж",
    "з",
    "к",
    "л",
    "м",
    "н",
    "п",
    "р",
    "с",
    "т",
    "ф",
    "х",
    "ц",
    "ч",
    "ш",
    "щ",
)
VOWELS = ("а", "е", "ё", "и", "о", "у", "ы", "э", "ю", "я", "й")
# й - здесь не ошибка, присутствует для соответствия дореволюционным правилам.


RUSSIAN_MODERN_ALPHABET = set(VOWELS + CONSONANTS)

# Слова игнорируемые для перевода
EXCEPT_WORDS = ("он", "и")


class CaseOfWord:
    def __init__(self, word: str) -> None:
        self.origin = word

    @property
    def case_map(self) -> List[bool]:
        return [i.isupper() for i in self.origin]

    @staticmethod
    def apply_case_map_to_word(word: str, case_map: List[bool]) -> str:
        if all(case_map):
            return word.upper()

        if all([i is False for i in case_map]):
            return word

        if len(word) > len(case_map):
            for _ in range(len(word) - len(case_map)):
                case_map.append(False)

        final_word = ""
        for w, c in zip(word, case_map):
            if c:
                final_word += w.upper()
            else:
                final_word += w

        return final_word


class WordTypeEnum(Enum):
    TO_TRANSLATE = 0
    ENGLISH = 1

    @staticmethod
    def get_type_of_word(word: str) -> "WordTypeEnum":
        if all([(i in RUSSIAN_MODERN_ALPHABET) for i in word.lower().strip()]):
            return WordTypeEnum.TO_TRANSLATE
        else:
            return WordTypeEnum.ENGLISH


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
        self.type_of_word - Обозначение типа слова для корректной обработки. Является WordTypeEnum
        self._case - Список отображающий изначальное присутствие заглавных в слове.

    Реализует методы:
        __simplificate_translate_to_old_style - упрощённый перевод на дореформенный.
        old - Параметр-интерфейс для перевода в дореформенный.
        from_text - classmethod для преобразования текста в список объектов WordPresent.
        from_words_to_str - Статичный метод для преобразования списка объектов WordPresent в переведённую строку.
    """

    __slots__ = ("type_of_word", "_rus_dict", "origin", "_case_map")

    def __init__(self, word: str, rus_dict: Dict[str, str]) -> None:
        self.origin = word
        self._rus_dict = rus_dict
        self.type_of_word = WordTypeEnum.get_type_of_word(word)
        self._case_map = CaseOfWord(word).case_map

    def __simplificate_translate_to_old_style(self) -> str:
        """
        Реализация алгоритма упрощённого перевода на дореформенный.

        Работа алгоритма:
            I. Если слово оканчивается на согласную, то добавляем в конец твёрдый знак.
            II. Если после буквы "и" идёт гласная, то буква "и" становится буквой "i"
        """
        old_str = copy(self.origin)

        # I
        if old_str[-1] in CONSONANTS:
            old_str += "ъ"

        # II
        result_chars = []
        i = 0
        while i < len(old_str):
            current_char = old_str[i]
            if (
                current_char == "и"
                and i + 1 < len(old_str)
                and old_str[i + 1] in VOWELS
            ):
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
            1.  Если слово:
                    в списке исключений,
                    cлово является знаком пунктуации,
                    слово состоить из английских букв,
                то отдаёт оригинал слова.
            2. Ищет слово в словаре, если не найдено, то прогоняет через упрощённый алгоритм перевода.
            3. Применяет карту заглавных.
        """
        if (
            self.origin in EXCEPT_WORDS
            or self.origin in punctuation
            or self.type_of_word == WordTypeEnum.ENGLISH
        ):
            return self.origin

        old_word = self._rus_dict.get(self.origin.lower())

        if not old_word:
            old_word = self.__simplificate_translate_to_old_style()

        # Применение карты заглавных
        return CaseOfWord.apply_case_map_to_word(old_word, self._case_map)

    @classmethod
    def from_text(cls, text: str, ru_dict: dict) -> List["WordPresent"]:
        """
        Метод для преобразования текста в набор объектов WordPresent.
        """

        # pattern = r"(\w+|[^\w\s])"
        pattern = r"((?:https?|ftp)://[^\s]+|\w+|[^\w\s])"  # Repair links

        tokens = re.findall(pattern, text)

        return [cls(token, ru_dict) for token in tokens if token.strip()]

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
        result = []
        for word in words:
            if word.type_of_word == WordTypeEnum.ENGLISH:
                if not result:
                    result.append(word.origin)
                    continue
                result.append(" " + word.origin)
                continue

            current_word = word.old

            if not result or word.origin in punctuation:
                result.append(current_word)
            else:
                result.append(" " + current_word)

        return "".join(result)


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

    def _get_dict_url(self) -> str:
        url_dict = self.get_setting("url_of_modern_retro_dict")
        if not url_dict:
            url_dict = DEFAULT_DICT_ADDRESS
        return url_dict

    def _get_path_to_dict(self) -> Path:
        url_dict = self._get_dict_url()
        return Path(get_cache_dir() + url_dict)

    def _download_a_dict(self, url: str, path_to_dict: str) -> None:
        resp = requests.get(url)
        if resp.status_code != 200:
            raise Exception("bad status")

        write_file(str(path_to_dict), resp.text)
        rus_dict = json.loads(resp.text)

        if not rus_dict:
            raise Exception()

        self.rus_dict = rus_dict

    def _check_rus_dict(self) -> None:
        url_dict = self._get_dict_url()
        path_to_dict = self._get_path_to_dict()

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
            self._download_a_dict(url_dict, str(path_to_dict))
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

    def _show_error(self, title: str, error_message: str) -> None:
        """
        Метод для показа ошибок через alert окна.
        """
        current_fragment = get_last_fragment()
        if not current_fragment:
            log("Cannot show dialog, no current fragment.")
            return

        activity = current_fragment.getParentActivity()
        if not activity:
            log("Cannot show dialog, no parent activity.")
            return

        builder = AlertDialogBuilder(activity)
        builder.set_title(title)
        builder.set_message(error_message)

        def on_btn_click(bld: AlertDialogBuilder, which: int):
            bld.dismiss()

        builder.set_negative_button("Ок", on_btn_click)

        builder.show()

    def _on_change_url_of_source_dictionary(self, new_value: str):
        try:
            if new_value.split(".")[-1] != "json":
                raise Exception("Its not a json file!")
            parsed = urlparse(new_value)

            if not all([parsed.scheme, parsed.netloc]):
                raise Exception("Invalid url!")

            resp = requests.get(new_value)
            if not resp.ok:
                raise Exception("Not access to resource!")

        except Exception as e:
            self.set_setting("url_of_modern_retro_dict", DEFAULT_DICT_ADDRESS)
            self._show_error("Ошибка при изменении URL!", f"Подробнее: {e}")
            return

        delete_file(str(Path(get_cache_dir() + DEFAULT_DICT_ADDRESS.split("/")[-1])))

        path_to_dict = Path(get_cache_dir() + new_value.split("/")[-1])

        try:
            self._download_a_dict(new_value, str(path_to_dict))
        except Exception as e:
            self._show_error("Ошибка при загрузке нового словаря!", f"Подробнее: {e}")

    def _update_dictionary_of_words(self, view):
        try:
            dict_url = self._get_dict_url()
            if not dict_url:
                dict_url = DEFAULT_DICT_ADDRESS

            path_to_dict = self._get_path_to_dict()

            if path_to_dict.exists():
                delete_file(str(path_to_dict))

            self.rus_dict = None

            self._download_a_dict(dict_url, str(path_to_dict))

            current_fragment = get_last_fragment()

            BulletinHelper.show_success("Словарь успешно обновлён!", current_fragment)
        except Exception as e:
            current_fragment = get_last_fragment()
            BulletinHelper.show_error(
                f"Случилась ошибка при обновлении словаря:\n{e}", current_fragment
            )

    def create_settings(self):
        return [
            Header("Main settings"),
            Switch(key="translator_enabled", text="Enable a translator", default=True),
            Input(
                key="url_of_modern_retro_dict",
                text="URL address of dict Modern-Old Russian",
                default=DEFAULT_DICT_ADDRESS,
                on_change=self._on_change_url_of_source_dictionary,
                subtext='Need a direct link to json file. Format of file is a "modern_word": "old_word"',
            ),
            Divider(),
            Text(
                "Обновить словарь",
                accent=True,
                on_click=self._update_dictionary_of_words,
            ),
        ]
