import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import List

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.icons.font_awesome.form_icons import FormIcons
from clitt.core.term.commons import Direction
from clitt.core.term.terminal import Terminal
from clitt.core.tui.minput import minput_utils as mu
from clitt.core.tui.minput.access_type import AccessType
from clitt.core.tui.minput.form_field import FormField
from clitt.core.tui.minput.input_type import InputType
from clitt.core.tui.minput.input_validator import InputValidator
from clitt.core.tui.minput.menu_input import MenuInput
from hspylib.core.exception.exceptions import InvalidInputError
from hspylib.modules.cli.keyboard import Keyboard
from unittest.mock import patch


def _always_valid(_: FormField) -> bool:
    return True


class _FakeColor:
    def __init__(self, placeholder: str = "", code: str = ""):
        self.placeholder = placeholder
        self.code = code


class _FakeCursor:
    def __init__(self):
        self.moves: List[tuple[int, int]] = []
        self.erases: List[Direction] = []
        self.writes: List[tuple[str, str]] = []

    def move_to(self, row: int, col: int) -> None:
        self.moves.append((row, col))

    def erase(self, direction: Direction) -> None:
        self.erases.append(direction)

    def write(self, text: str, end: str = "") -> None:
        self.writes.append((text, end))

    def save(self) -> None:  # pragma: no cover - behaviour unused in tests
        pass

    def restore(self) -> None:  # pragma: no cover - behaviour unused in tests
        pass

    def track(self) -> tuple[int, int]:  # pragma: no cover - behaviour unused in tests
        return self.moves[-1] if self.moves else (0, 0)

    def end(self) -> None:  # pragma: no cover - behaviour unused in tests
        pass

    def reset_mode(self) -> None:  # pragma: no cover - behaviour unused in tests
        pass

    def writeln(self, obj: str = "", markdown: bool = False) -> None:  # pragma: no cover
        self.writes.append((obj, "\n"))


class _FakeScreen:
    def __init__(self):
        self.cursor = _FakeCursor()
        self.preferences = SimpleNamespace(
            title_color=_FakeColor(),
            sel_bg_color=_FakeColor(),
            navbar_color=_FakeColor(),
            highlight_color=_FakeColor(code=""),
            text_color=_FakeColor(code=""),
            selected_icon="",
            unselected_icon="",
        )
        self.lines = 24
        self.columns = 80

    def add_watcher(self, callback):  # pragma: no cover - behaviour unused in tests
        pass

    def clear(self) -> None:  # pragma: no cover - behaviour unused in tests
        pass


class _FakeTerminal:
    def __init__(self):
        self.screen = _FakeScreen()

    def echo(self, obj: str = "", end: str = "", markdown: bool = False) -> None:
        self.screen.cursor.write(str(obj), end=end)


class TestMenuInputInteractions(unittest.TestCase):
    def setUp(self) -> None:
        self._original_terminal = Terminal.INSTANCE
        self.fake_terminal = _FakeTerminal()
        Terminal.INSTANCE = self.fake_terminal

    def tearDown(self) -> None:
        Terminal.INSTANCE = self._original_terminal

    def _build_fields(self) -> List[FormField]:
        return [
            FormField(
                "Number",
                "number",
                InputType.TEXT,
                min_length=0,
                max_length=5,
                value="",
                input_validator=InputValidator.numbers(),
                field_validator=_always_valid,
            ),
            FormField(
                "Secret",
                "secret",
                InputType.PASSWORD,
                min_length=0,
                max_length=6,
                value="",
                input_validator=InputValidator.anything(),
                field_validator=_always_valid,
            ),
            FormField(
                "Confirm",
                "confirm",
                InputType.CHECKBOX,
                min_length=0,
                max_length=1,
                value=False,
                input_validator=InputValidator.anything(),
                field_validator=_always_valid,
            ),
            FormField(
                "Choice",
                "choice",
                InputType.SELECT,
                min_length=1,
                max_length=10,
                value="alpha|<beta>|gamma",
                input_validator=InputValidator.anything(),
                field_validator=_always_valid,
            ),
            FormField(
                "Code",
                "code",
                InputType.MASKED,
                min_length=0,
                max_length=5,
                value="12|##-##",
                input_validator=InputValidator.masked(),
                field_validator=_always_valid,
            ),
        ]

    def _create_menu(self, extra_fields: List[FormField] | None = None) -> MenuInput:
        fields = self._build_fields()
        if extra_fields:
            fields.extend(extra_fields)
        menu = MenuInput("Synthetic Form", fields)
        menu._terminal = self.fake_terminal
        return menu

    def test_handle_input_updates_field_values_by_type(self) -> None:
        menu = self._create_menu()
        number, secret, confirm, choice, code = menu.fields

        with patch.object(Keyboard, "wait_keystroke", side_effect=[Keyboard.VK_NONE] * 4):
            menu.cur_field = number
            menu._handle_input(Keyboard.VK_ONE)
            self.assertEqual("1", number.value)

            menu.cur_field = secret
            menu._handle_input(Keyboard.VK_a)
            self.assertEqual("a", secret.value)

        menu.cur_field = confirm
        menu._handle_input(Keyboard.VK_SPACE)
        self.assertTrue(confirm.value)

        previous_choice = str(choice.value)
        with patch.object(mu, "toggle_selected", return_value="alpha|beta|<gamma>") as toggle_selected:
            menu.cur_field = choice
            menu._handle_input(Keyboard.VK_SPACE)
            toggle_selected.assert_called_once_with(previous_choice)
            self.assertEqual("alpha|beta|<gamma>", choice.value)

        code.value = "12|##-##"
        with patch.object(mu, "append_masked", return_value="123|##-##") as append_masked:
            menu.cur_field = code
            menu._handle_input(Keyboard.VK_THREE)
            append_masked.assert_called_once_with("12", "##-##", Keyboard.VK_THREE.value)
            self.assertEqual("123|##-##", code.value)

    def test_handle_input_reports_validation_errors(self) -> None:
        menu = self._create_menu()
        number = menu.fields[0]
        menu.cur_field = number

        error_messages: list[str] = []

        with patch.object(Keyboard, "wait_keystroke", return_value=Keyboard.VK_NONE), \
            patch("clitt.core.tui.minput.menu_input.Terminal.set_enable_echo") as mock_echo, \
            patch("clitt.core.tui.minput.menu_input.Terminal.set_show_cursor") as mock_cursor, \
            patch("clitt.core.tui.minput.menu_input.sleep"), \
            patch("clitt.core.tui.minput.menu_input.mu.mi_print_err", side_effect=lambda _screen, msg: error_messages.append(msg)):

            menu._handle_input(Keyboard.VK_a)

        self.assertEqual("", number.value)
        self.assertGreater(len(self.fake_terminal.screen.cursor.moves), 0)
        self.assertIn("Input 'a' is not valid", error_messages[0])
        self.assertEqual(2, mock_echo.call_count)
        mock_cursor.assert_any_call(False)

        code = menu.fields[-1]
        menu.cur_field = code
        with patch.object(mu, "append_masked", side_effect=InvalidInputError("bad masked input")), \
            patch("clitt.core.tui.minput.menu_input.Terminal.set_enable_echo"), \
            patch("clitt.core.tui.minput.menu_input.Terminal.set_show_cursor"), \
            patch("clitt.core.tui.minput.menu_input.sleep"), \
            patch("clitt.core.tui.minput.menu_input.mu.mi_print_err") as mock_err:

            menu._handle_input(Keyboard.VK_ONE)

        mock_err.assert_called_with(self.fake_terminal.screen, f"{FormIcons.ARROW_LEFT} bad masked input")

    def test_handle_backspace_respects_field_rules(self) -> None:
        menu = self._create_menu()
        number, _, _, _, code = menu.fields

        number.value = "123"
        menu.cur_field = number
        menu._handle_backspace()
        self.assertEqual("12", number.value)

        code.value = "12|##-##"
        menu.cur_field = code
        menu._handle_backspace()
        self.assertEqual("1|##-##", code.value)

        readonly = FormField(
            "ReadOnly",
            "read_only",
            InputType.TEXT,
            access_type=AccessType.READ_ONLY,
            value="fixed",
            input_validator=InputValidator.anything(),
            field_validator=_always_valid,
        )
        menu.fields.append(readonly)
        menu.positions.append((0, 0))
        menu.cur_field = readonly

        with patch("clitt.core.tui.minput.menu_input.Terminal.set_enable_echo"), \
            patch("clitt.core.tui.minput.menu_input.Terminal.set_show_cursor"), \
            patch("clitt.core.tui.minput.menu_input.sleep"), \
            patch("clitt.core.tui.minput.menu_input.mu.mi_print_err") as mock_err:

            menu._handle_backspace()

        mock_err.assert_called_with(self.fake_terminal.screen, f"{FormIcons.ARROW_LEFT} This field is read only !")

    def test_handle_enter_validates_and_normalizes_fields(self) -> None:
        menu = self._create_menu()
        number, secret, confirm, choice, code = menu.fields

        number.value = "12345"
        secret.value = "pwd"
        confirm.value = True
        choice.value = "first|<second>|third"
        code.value = "123|###"

        with patch("clitt.core.tui.minput.menu_input.mu.get_selected", wraps=mu.get_selected) as mock_selected:
            result = menu._handle_enter()

        self.assertEqual(Keyboard.VK_ENTER, result)
        self.assertTrue(menu._done)
        self.assertEqual(True, bool(confirm.value))
        self.assertEqual("second", choice.value)
        self.assertEqual("123", code.value)
        mock_selected.assert_called_once()

    def test_handle_enter_reports_invalid_field(self) -> None:
        invalid_field = FormField(
            "Invalid",
            "invalid",
            InputType.TEXT,
            value="bad",
            input_validator=InputValidator.anything(),
            field_validator=lambda _: False,
        )
        menu = MenuInput("Invalid Form", [invalid_field])
        menu._terminal = self.fake_terminal

        with patch("clitt.core.tui.minput.menu_input.Terminal.set_enable_echo"), \
            patch("clitt.core.tui.minput.menu_input.Terminal.set_show_cursor"), \
            patch("clitt.core.tui.minput.menu_input.sleep"), \
            patch("clitt.core.tui.minput.menu_input.mu.mi_print_err") as mock_err:

            result = menu._handle_enter()

        self.assertIsNone(result)
        self.assertFalse(menu._done)
        self.assertEqual(0, menu.tab_index)
        mock_err.assert_called_with(menu.screen, f"{FormIcons.ARROW_LEFT} Form field is not valid: {invalid_field}")

    def test_builder_chaining_produces_expected_configuration(self) -> None:
        builder = MenuInput.builder()
        builder.field().label("First Name").value("Alice").build()
        builder.field().label("Agree").itype("checkbox").value(True).build()
        fields = builder.build()

        self.assertEqual("first_name", fields[0].dest)
        self.assertEqual("Alice", fields[0].value)
        self.assertIsNone(fields[0].tooltip)
        self.assertTrue(fields[1].value)

        menu = MenuInput("Builder Form", fields)
        menu._terminal = self.fake_terminal
        fields[0]._tooltip = "Provide your first name"
        menu.cur_field = fields[0]
        navbar_with_tooltip = menu.navbar()
        self.assertIn("Provide your first name", navbar_with_tooltip)

        menu.cur_field = fields[1]
        navbar_with_default = menu.navbar()
        self.assertIn("the agree", navbar_with_default)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMenuInputInteractions)
    unittest.TextTestRunner(verbosity=2, failfast=True, stream=sys.stdout).run(suite)
