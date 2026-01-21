#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   @package: demo.cli.tui.minput
      @file: menu_input_demo.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
from clitt.core.tui.minput.input_validator import InputValidator
from clitt.core.tui.minput.minput import MenuInput, minput

if __name__ == "__main__":
    # fmt: off
    form_fields = MenuInput.builder() \
        .field() \
            .label('letters') \
            .tooltip("Just Letters") \
            .validator(InputValidator.letters()) \
            .build() \
        .field() \
            .label('word') \
            .tooltip("Just a Word") \
            .validator(InputValidator.words()) \
            .build() \
        .field() \
            .label('number') \
            .tooltip("Just Numbers") \
            .validator(InputValidator.numbers(), lambda f: int(f.value) > 80) \
            .min_max_length(1, 4) \
            .build() \
        .field() \
            .label('anything') \
            .tooltip("This can be anything") \
            .build() \
        .field() \
            .label('masked') \
            .itype('masked') \
            .value('|##::##::%% @@') \
            .build() \
        .field() \
            .label('selectable') \
            .itype('select') \
            .value('one|two|three') \
            .build() \
        .field() \
            .label('checkbox') \
            .itype('checkbox') \
            .build() \
        .field() \
            .label('password') \
            .itype('password') \
            .min_max_length(4, 8) \
            .build() \
        .field() \
            .label('read-only') \
            .access_type('read-only') \
            .value('READ-ONLY') \
            .build() \
        .build()
    # fmt: on

    result = minput(form_fields)
    print(result if result else "None")
