#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.schema
   @file: schema_registry.py
@created: Thu, 5 Aug 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from hspylib.core.enums.http_code import HttpCode
from hspylib.core.enums.http_method import HttpMethod
from hspylib.core.preconditions import check_not_none, check_state
from hspylib.modules.fetch.fetch import fetch, is_reachable
from hspylib.modules.fetch.http_response import HttpResponse
from kafman.core.exception.exceptions import SchemaRegistryError
from kafman.core.schema.registry_subject import RegistrySubject
from requests import exceptions as ex
from typing import Any, Dict, List, Optional, Set, Tuple

import json
import logging as log


class SchemaRegistry:
    """This class is used to manage and hold information about the schema registry server"""

    def __init__(self, url: Optional[str] = None):
        self._url = url or "localhost:8081"
        self._valid = False
        self._schema_types: List[str] = []
        self._subjects: List[str] = []

    def is_valid(self) -> bool:
        """Whether the schema registry was validated or not"""
        return self._valid

    def url(self) -> Optional[str]:
        """Return the schema registry url"""
        return self._url

    def set_url(self, url: str, validate_url: bool = True) -> bool:
        """Set the schema registry url"""
        self._url = url
        if validate_url and is_reachable(url):
            self._valid = True
        else:
            self._valid = False
        return self._valid

    def invalidate(self) -> None:
        """Invalidate the last schema registry validation"""
        self._valid = False

    def get_schema_types(self) -> List[str]:
        """Return the schema types supported by the server"""
        return self._schema_types

    def get_subjects(self) -> List[str]:
        """Return the subjects currently registered at the server"""
        return self._subjects

    def register(
        self, subject: str, schema_content: str, schema_type: str = "AVRO"
    ) -> None:
        """Register a new version of a schema under the registry subject"""
        schema_payload = json.dumps(
            {"schema": schema_content, "schemaType": schema_type.upper()}
        )
        self._make_request(
            url=f"{self._url}/subjects/{subject}/versions",
            method=HttpMethod.POST,
            headers=[{"Content-Type": "application/vnd.schemaregistry.v1+json"}],
            body=schema_payload,
        )
        if subject not in self._subjects:
            self._subjects.append(subject)
        log.debug("Schema subject successfully registered: %s", subject)

    def deregister(self, subjects: Set[RegistrySubject]) -> None:
        """Deregister the list of subjects from the registry server"""
        for subject in subjects:
            # Invoke delete subject
            self._make_request(
                url=f"{self._url}/subjects/{subject.subject}/versions/{subject.version}",
                method=HttpMethod.DELETE,
            )
        log.debug("Schema subject successfully deregistered: %s", str(subjects))

    def fetch_server_info(self) -> Tuple[List[str], List[str]]:
        """Fetch information about the selected schema registry server"""

        # Fetch server supported schema types
        response = self._make_request(
            url=f"{self._url}/schemas/types",
            expected_codes=[HttpCode.OK, HttpCode.NOT_FOUND],
        )
        self._schema_types = json.loads(response.body or "[]")
        # Fetch current registered subjects
        response = self._make_request(url=f"{self._url}/subjects")
        self._subjects = json.loads(response.body or "[]")

        return self._schema_types, self._subjects

    def fetch_subject_versions(self) -> List[RegistrySubject]:
        """Fetch information about the schema registry existing subjects"""
        subjects = []
        if self._subjects:
            # Loop through recorded subjects
            for subject_name in self._subjects:
                # Fetch all subject versions
                response = self._make_request(
                    url=f"{self._url}/subjects/{subject_name}/versions"
                )
                all_versions = json.loads(response.body or "[]")
                check_state(isinstance(all_versions, list))
                for v in all_versions:
                    # Fetch information about the subject version
                    subject_response = self._make_request(
                        url=f"{self._url}/subjects/{subject_name}/versions/{v}"
                    )
                    check_not_none(subject_response)
                    subject = json.loads(subject_response.body or "{}")
                    subjects.append(
                        RegistrySubject(
                            (
                                subject["schemaType"]
                                if "schemaType" in subject
                                else "AVRO"
                            ),
                            subject["subject"],
                            subject["id"],
                            subject["version"],
                            json.loads(subject["schema"]),
                        )
                    )

        return subjects

    def _make_request(
        self,
        url: str,
        method: HttpMethod = HttpMethod.GET,
        headers: Optional[List[Dict[str, str]]] = None,
        body: Optional[Any] = None,
        expected_codes: Optional[List[HttpCode]] = None,
    ) -> HttpResponse:
        """Make a request from the registry server"""

        if self._valid:
            try:
                if not expected_codes:
                    expected_codes = [HttpCode.OK]
                log.debug(
                    "Making request to: %s and expecting codes: %s",
                    url,
                    str(expected_codes),
                )
                response = fetch(url=url, method=method, headers=headers, body=body)
                check_not_none(response)
                if response.status_code not in expected_codes:
                    raise SchemaRegistryError(
                        f"Request failed. Expecting {str(expected_codes)} but received: {response.status_code}"
                        + f"\n\t=> {response.body}"
                    )
                return response
            except (
                ex.ConnectTimeout,
                ex.ConnectionError,
                ex.ReadTimeout,
                ex.InvalidURL,
            ) as err:
                raise SchemaRegistryError(
                    f"Unable to fetch from {self._url}\n => {str(err)}"
                ) from err

        raise SchemaRegistryError(f"Schema registry server {url} is not valid")
