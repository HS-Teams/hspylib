#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: demo.qtdemos.calculator.views
   @file: main_qt_view.py
@created: Tue, 4 May 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from calculator.core.operations import Operations
from calculator.views.blink_lcd_thread import BlinkLcdThread
from hqt.views.qt_view import QtView
from hspylib.core.config.app_config import AppConfigs
from pathlib import Path
from PyQt6.QtCore import Qt

import logging as log


class MainQtView(QtView):
    UI_FILE = "qt_calculator.ui"
    RESOURCES_DIR = Path(__file__).parents[1] / "resources"
    FORMS_DIR = RESOURCES_DIR / "forms"

    def __init__(self):
        super().__init__(self.UI_FILE, str(self.FORMS_DIR))
        self._configs = AppConfigs(self.RESOURCES_DIR)
        self._dec_sep = self._configs["decimal.separator"]
        self._min_digits = int(self._configs["min.digits"])
        self._max_digits = int(self._configs["max.digits"])
        self._waiting_operand = self.waiting_operand2 = True
        self._operand = self._operand2 = self._last_operand = None
        self._memory_rec = None
        self._keymap = None
        self._display_text = ""
        self._op = Operations.NO_OP
        self._setup_keymap()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Connect signals and startup components"""
        self.ui.btnAC.clicked.connect(self._btn_escape_clicked)
        self.ui.btnSignal.clicked.connect(self._btn_period_clicked)
        self.ui.btnPercent.clicked.connect(self._btn_percent_clicked)
        self.ui.btnDivision.clicked.connect(self._btn_slash_clicked)
        self.ui.btn7.clicked.connect(self._btn7_clicked)
        self.ui.btn8.clicked.connect(self._btn8_clicked)
        self.ui.btn9.clicked.connect(self._btn9_clicked)
        self.ui.btnMultiplication.clicked.connect(self._btn_asterisk_clicked)
        self.ui.btn4.clicked.connect(self._btn4_clicked)
        self.ui.btn5.clicked.connect(self._btn5_clicked)
        self.ui.btn6.clicked.connect(self._btn6_clicked)
        self.ui.btnMinus.clicked.connect(self._btn_minus_clicked)
        self.ui.btn1.clicked.connect(self._btn1_clicked)
        self.ui.btn2.clicked.connect(self._btn2_clicked)
        self.ui.btn3.clicked.connect(self._btn3_clicked)
        self.ui.btnPlus.clicked.connect(self._btn_plus_clicked)
        self.ui.btn0.clicked.connect(self._btn0_clicked)
        self.ui.btnDecimal.clicked.connect(self._btn_comma_clicked)
        self.ui.btnDecimal.setText(self._dec_sep)
        self.ui.btnEqual.clicked.connect(self._btn_equal_clicked)
        self.ui.frameMain.keyPressed.connect(self._key_pressed)

    def _setup_keymap(self) -> None:
        """Setup the main frame key map callbacks."""
        self._keymap = {
            Qt.Key.Key_0: self._btn0_clicked,
            Qt.Key.Key_1: self._btn1_clicked,
            Qt.Key.Key_2: self._btn2_clicked,
            Qt.Key.Key_3: self._btn3_clicked,
            Qt.Key.Key_4: self._btn4_clicked,
            Qt.Key.Key_5: self._btn5_clicked,
            Qt.Key.Key_6: self._btn6_clicked,
            Qt.Key.Key_7: self._btn7_clicked,
            Qt.Key.Key_8: self._btn8_clicked,
            Qt.Key.Key_9: self._btn9_clicked,
            Qt.Key.Key_Plus: self._btn_plus_clicked,
            Qt.Key.Key_Minus: self._btn_minus_clicked,
            Qt.Key.Key_Slash: self._btn_slash_clicked,
            Qt.Key.Key_Asterisk: self._btn_asterisk_clicked,
            Qt.Key.Key_Percent: self._btn_percent_clicked,
            Qt.Key.Key_Equal: self._btn_equal_clicked,
            Qt.Key.Key_Return: self._btn_equal_clicked,
            Qt.Key.Key_Backspace: self._btn_backspace_clicked,
            Qt.Key.Key_Period: self._btn_period_clicked,
            Qt.Key.Key_Comma: self._btn_period_clicked,
            Qt.Key.Key_Escape: self._btn_escape_clicked,
        }

    def _key_pressed(self, key: Qt.Key) -> None:
        """Invoked when a key is pressed under the main frame."""
        if callback := self._keymap.get(key):
            callback()

    def _display(self, value: str = "0") -> None:
        """Display the specified value."""
        future_digits = len(str(value)) if value else 0
        digits = self.ui.lcdDisplay.digitCount()
        if future_digits > digits:
            self.ui.lcdDisplay.setDigitCount(min(future_digits, self._max_digits))
        elif future_digits <= digits:
            self.ui.lcdDisplay.setDigitCount(max(future_digits, self._min_digits))
        self.ui.lcdDisplay.display(value)

    def _blink_lcd(self) -> None:
        """Blink the displayed LCD value."""
        blink = BlinkLcdThread(
            self.ui.lcdDisplay, float(self._configs["lcd.blink.delay"])
        )
        blink.start()
        self._display_text = ""

    def _soft_reset(self) -> None:
        """Reset the calculator."""
        self._waiting_operand = True
        self.waiting_operand2 = True
        self._last_operand = self._operand2
        self._operand = 0
        self._operand2 = 0
        self._memory_rec = 0
        self._display_text = ""

    def _append_digit(self, digit: int) -> None:
        self.ui.btnAC.setText("C")
        if not self._display_text or self._display_text == "0":
            self._display_text = str(digit)
        else:
            self._display_text += str(digit)
        self._display(self._display_text)

    def _btn_backspace_clicked(self) -> None:
        if self._display_text:
            if len(self._display_text) <= 1:
                self._btn_escape_clicked()
            else:
                self._display_text = self._display_text[:-1]
                self._display(self._display_text)

    def _calculate(self) -> None:
        result = 0
        if not self._op or not self._operand:
            return

        if self._op == Operations.SUM:
            result = self._operand + self._operand2
        elif self._op == Operations.SUBTRACTION:
            result = self._operand - self._operand2
        elif self._op == Operations.MULTIPLICATION:
            result = self._operand * self._operand2
        elif self._op == Operations.DIVISION:
            if self._operand2 == 0:
                result = "oo"
            else:
                result = self._operand / self._operand2
        self._display(result)
        self._memory_rec = 0

    def _change_op(self, op: Operations) -> None:
        self._op = op
        if self._waiting_operand:
            self._operand = self.ui.lcdDisplay.value()
            self._memory_rec = self._operand
            self._waiting_operand = False
        elif self.waiting_operand2:
            self._operand2 = self.ui.lcdDisplay.value()
            self.waiting_operand2 = False
        if not self._waiting_operand and not self.waiting_operand2:
            self._calculate()
            self._operand = self.ui.lcdDisplay.value()
            self.waiting_operand2 = True
        self._blink_lcd()

    def _btn_equal_clicked(self) -> None:
        log.debug("Clicked: =")
        if self._waiting_operand:
            self._operand = self.ui.lcdDisplay.value()
            self._operand2 = self._last_operand if self._last_operand else None
        elif self.waiting_operand2:
            self._operand2 = self.ui.lcdDisplay.value()
        if self._operand and self._operand2:
            self._calculate()
        self._soft_reset()
        self._blink_lcd()

    def _btn_escape_clicked(self) -> None:
        log.debug("Clicked: AC")
        if self._memory_rec:
            self._memory_rec = 0
        else:
            self.ui.lcdDisplay.setDigitCount(self._min_digits)
            self._display()
            self._soft_reset()
            self.ui.btnAC.setText("AC")
        self._display_text = ""
        self._blink_lcd()

    def _btn_period_clicked(self) -> None:
        log.debug("Clicked: +-")
        self._display(self.ui.lcdDisplay.value() * -1)
        self._display_text = str(self.ui.lcdDisplay.value())

    def _btn_percent_clicked(self) -> None:
        log.debug("Clicked: %")
        if not self._memory_rec:
            self._display(self.ui.lcdDisplay.value() / 100)
            self._display_text = ""
        else:
            operand1 = self._memory_rec
            operand2 = self.ui.lcdDisplay.value()
            self._display(operand1 * (operand2 / 100))
            self._display_text = str(self.ui.lcdDisplay.value())
            self._memory_rec = self.ui.lcdDisplay.value()

    def _btn_slash_clicked(self) -> None:
        log.debug("Clicked: /")
        self._change_op(Operations.DIVISION)

    def _btn7_clicked(self) -> None:
        log.debug("Clicked: 7")
        self._append_digit(7)

    def _btn8_clicked(self) -> None:
        log.debug("Clicked: 8")
        self._append_digit(8)

    def _btn9_clicked(self) -> None:
        log.debug("Clicked: 9")
        self._append_digit(9)

    def _btn_asterisk_clicked(self) -> None:
        log.debug("Clicked: x")
        self._change_op(Operations.MULTIPLICATION)

    def _btn4_clicked(self) -> None:
        log.debug("Clicked: 4")
        self._append_digit(4)

    def _btn5_clicked(self) -> None:
        log.debug("Clicked: 5")
        self._append_digit(5)

    def _btn6_clicked(self) -> None:
        log.debug("Clicked: 6")
        self._append_digit(6)

    def _btn_minus_clicked(self) -> None:
        log.debug("Clicked: -")
        self._change_op(Operations.SUBTRACTION)

    def _btn1_clicked(self) -> None:
        log.debug("Clicked: 1")
        self._append_digit(1)

    def _btn2_clicked(self) -> None:
        log.debug("Clicked: 2")
        self._append_digit(2)

    def _btn3_clicked(self) -> None:
        log.debug("Clicked: 3")
        self._append_digit(3)

    def _btn_plus_clicked(self) -> None:
        log.debug("Clicked: +")
        self._change_op(Operations.SUM)

    def _btn0_clicked(self) -> None:
        log.debug("Clicked: 0")
        self._append_digit(0)

    def _btn_comma_clicked(self) -> None:
        log.debug("Clicked: ,")
        if self._dec_sep not in self._display_text:
            self._display_text += (
                self._dec_sep if self._display_text else "0" + self._dec_sep
            )
        self._display(self._display_text)
