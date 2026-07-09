#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   @package: clitt.addons.setman
      @file: settings.py
   @created: Thu, 04 Jul 2023
    @author: "<B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: "https://github.com/yorevs/hspylib")
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
import csv
import logging as log
import os
import uuid
from functools import lru_cache
from typing import Any, List, Optional, Tuple

from datasource.identity import Identity
from hspylib.core.preconditions import check_argument, check_not_none
from hspylib.core.tools.commons import dirname, file_is_not_empty, touch_file
from hspylib.core.tools.text_tools import ensure_endswith
from hspylib.core.zoned_datetime import now

from setman.core.setman_enums import SettingsType
from setman.settings.settings_config import SettingsConfig
from setman.settings.settings_entry import SettingsEntry
from setman.settings.settings_service import SettingsService


class Settings:
    """Class to provide settings interactions."""

    HEADERS = ["uuid", "name", "prefix", "value", "settings type", "modified"]

    def __init__(self, configs: SettingsConfig, frozen: bool = False) -> None:
        self._configs = configs
        self._frozen = frozen
        self._service = SettingsService(self.configs)
        if not file_is_not_empty(self.configs.database):
            self._create_db()
        self._limit = 500
        self._offset = 0

    def __str__(self):
        entries = f",{os.linesep}  ".join(list(map(str, self.search())))
        return f"Settings: [{os.linesep + '  ' if entries else ''}" f"{entries}" f"{os.linesep if entries else ''}]"

    def __repr__(self):
        return str(self)

    def __getitem__(self, name: str) -> SettingsEntry:
        return self.get(name)

    def __setitem__(self, name: str, item: Tuple[str, Any, SettingsType]) -> None:
        self.put(name, item[0], item[1], item[2])

    @property
    def configs(self) -> SettingsConfig:
        return self._configs

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def offset(self) -> int:
        return self._offset

    @offset.setter
    def offset(self, value: int) -> None:
        self._offset = value

    @property
    def frozen(self) -> bool:
        return self._frozen

    @frozen.setter
    def frozen(self, value: bool) -> None:
        self._frozen = value

    @lru_cache(maxsize=500)
    def get(self, name: str) -> Optional[SettingsEntry]:
        """Get setting matching the specified name.
        :param name the settings name to get.
        """
        return self._service.get_by_name(name) if name else None

    def put(
        self,
        name: str | None = None,
        prefix: str = '',
        value: Any | None = None,
        stype: SettingsType = SettingsType.PROPERTY,
    ) -> Tuple[Optional[SettingsEntry], Optional[SettingsEntry]]:
        """Upsert the specified setting.
        :param name: The settings name.
        :param prefix: The settings prefix.
        :param value: The settings value.
        :param stype: The settings type.
        :return: A tuple containing the existing setting (if found) and the updated (or new) one.
        """
        if (found := self._service.get_by_name(name)) and self._frozen:
            log.debug("Setting preserved, and not overwritten: '%s'", found.name)
            return None, None
        entry = found or SettingsEntry(Identity(SettingsEntry.SetmanId(uuid.uuid4().hex)), name, prefix, value, stype)
        if any(a is None for a in [name, value, stype]):
            if not (entry := SettingsEntry.prompt(entry)):
                return None, None
        else:
            entry.prefix = prefix
            entry.stype = stype.val
            entry.value = value
        entry.modified = now()
        self._service.save(entry)
        log.debug("Setting saved: '%s'", entry.name)
        self._clear_caches()

        return found, entry

    def remove(self, name: str) -> Optional[SettingsEntry]:
        """Delete the specified setting.
        :param name: The settings name to delete.
        :return: The deleted setting if found, otherwise None.
        """
        if name:
            found = self._service.get_by_name(name)
            if found:
                self._service.remove(found)
                self._clear_caches()
                return found
        return None

    @lru_cache(maxsize=500)
    def search(self, name: str | None = None, stype: SettingsType | None = None) -> List[SettingsEntry]:
        """Search all settings matching criteria.
        :param name: The settings name to filter.
        :param stype: The settings type to filter.
        :return: A list of matching settings entries.
        """
        return self._service.search(name, stype, self.limit, self.offset)

    def clear(self, name: str | None = None, stype: SettingsType | None = None) -> None:
        """Clear settings matching filters.
        :param name: The settings name to filter.
        :param stype: The settings type to filter.
        """
        self._service.clear(name, stype)
        self._clear_caches()

    def count(self) -> int:
        """Return the number of existing settings.
        :return: The count of existing settings.
        """
        return self._service.count()

    def import_csv(self, filepath: str) -> int:
        """Upsert settings from a CSV file into the database.
        :param filepath: The path of the CSV file to be imported.
        :return: The number of records upserted.
        """
        count, csv_file = 0, ensure_endswith(filepath, ".csv")
        check_argument(os.path.exists(filepath), "CSV file does not exist: " + csv_file)
        with open(csv_file, encoding="UTF8") as f_csv:
            csv_reader = csv.reader(f_csv, delimiter=",")
            for row in csv_reader:
                if row == self.HEADERS:
                    continue
                uid, name, prefix, value, stype = (
                    str(row[0]),
                    str(row[1]),
                    str(row[2]),
                    str(row[3]),
                    SettingsType.of_value(row[4]),
                )
                found = self._service.get_by_name(name)
                if found and self._frozen:
                    continue
                entry = SettingsEntry(Identity(SettingsEntry.SetmanId(uid)), name, prefix, value, stype)
                self._service.save(entry)
                count += 1
            self._clear_caches()
            return count

    def export_csv(self, filepath: str, name: str = None, stype: SettingsType = None) -> int:
        """Export settings from a CSV file into the database.
        :param filepath: The path of the CSV file to be exported.
        :param name: The settings name to filter.
        :param stype: The settings type to filter.
        :return: The number of settings exported.
        """
        dest_dir, csv_file = dirname(filepath), ensure_endswith(filepath, ".csv")
        check_argument(os.path.exists(dest_dir), "Destination dir does not exist: " + dest_dir)
        settings = self.search(name, stype)
        with open(csv_file, "w", encoding="UTF8") as f_csv:
            writer = csv.writer(f_csv, delimiter=",")
            writer.writerow(self.HEADERS)
            writer.writerows(list(map(lambda s: s.values, settings)))
            return len(settings)

    def as_environ(self, name: str | None) -> List[str]:
        """Return all settings formatted as bash export environment variables.
        :param name: The settings name to filter.
        :return: A list of settings formatted as environment variable exports.
        """
        data = self.search(name, SettingsType.ENVIRONMENT)
        return list(map(lambda s: s.to_env_export(), data))

    def _create_db(self) -> bool:
        """Create the settings SQLite DB file.
        :return: True if the database was created successfully, False otherwise.
        """
        check_not_none(
            self.configs.database, "Missing database property: 'hhs.settings.database'!")
        check_not_none(
            self.configs.encoded_db, "Missing encode_db property: 'hhs.settings.encode.database'!")
        touch_file(self.configs.database)
        self._service.create_db()
        log.info("Settings file has been created")
        return os.path.exists(self.configs.database)

    def _clear_caches(self) -> None:
        """Remove all lru_caches."""
        self.get.cache_clear()
        self.search.cache_clear()
