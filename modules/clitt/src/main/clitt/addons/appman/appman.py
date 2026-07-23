#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Clitt
@package: clitt.addons.appman
   @file: appman.py
@created: Tue, 4 May 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from clitt.addons.appman.appman_enums import AppExtension, AppType
from clitt.core.term.terminal import Terminal
from clitt.core.tui.minput.input_validator import InputValidator
from clitt.core.tui.minput.minput import MenuInput, minput
from hspylib.core.enums.charset import Charset
from hspylib.core.enums.http_code import HttpCode
from hspylib.core.metaclass.singleton import Singleton
from hspylib.core.namespace import Namespace
from hspylib.core.preconditions import check_argument
from hspylib.core.tools.commons import parent_path, syserr, sysout
from hspylib.core.tools.text_tools import camelcase, ensure_endswith
from hspylib.modules.application.application import Application
from hspylib.modules.application.exit_status import ExitStatus
from hspylib.modules.application.version import Version
from hspylib.modules.fetch.fetch import get
from textwrap import dedent
from typing import List

import os
import stat
import urllib3

HERE = parent_path(__file__)

INITIAL_REVISION = Version.initial()

WELCOME_MESSAGE = f"My Application v{INITIAL_REVISION}"


class AppManager(metaclass=Singleton):
    """HsPyLib application manager that helps creating HsPyLib based applications and widgets."""

    # The directory containing all template files
    TEMPLATES = HERE / "templates"

    # The general gradle properties
    GRADLE_PROPS = dedent("""
        app_name    = '{}'
        app_version = '{}'

        pythonVersion=3

        author="<Author>")
        mailTo="<MailTo")
        siteUrl="<SiteUrl>")
    """)

    @staticmethod
    def prompt() -> Namespace:
        """Prompt for the application info."""
        # fmt: off
        form_fields = MenuInput.builder() \
            .field() \
                .label('App Name') \
                .validator(InputValidator.words()) \
                .min_max_length(1, 40) \
                .value('my_app') \
                .build() \
            .field() \
                .label('App Type') \
                .itype('select') \
                .value(f"{AppType.APP}|{AppType.QT_APP}|{AppType.WIDGET}") \
                .build() \
            .field() \
                .label('Dest Dir') \
                .validator(InputValidator.anything()) \
                .min_max_length(3, 80) \
                .value(os.getenv('HOME', os.getcwd())) \
                .build() \
            .field() \
                .label('Initialize gradle') \
                .itype('checkbox') \
                .value(True) \
                .build() \
            .field() \
                .label('Initialize git') \
                .itype('checkbox') \
                .value(True) \
                .build() \
            .build()
        # fmt: on
        return minput(form_fields)

    def __init__(self, parent_app: Application) -> None:
        self._parent_app = parent_app
        self._app_name = None
        self._app_dir = None
        self._init_gradle_flag = False
        self._init_git_flag = False

    def create(
        self,
        app_name: str,
        app_type: AppType,
        app_ext: List[AppExtension],
        dest_dir: str,
    ) -> None:
        """Create the application based on the parameters.
        :param app_name the application name.
        :param app_type the application type (qt-app, widgets, ...)
        :param app_ext the application extensions (gradle, git, ...).
        :param dest_dir the project destination directory (dest_dir/app_name).
        """
        sysout(f'Creating "{app_name}" at {dest_dir}')
        try:
            check_argument(
                os.path.exists(dest_dir), "Destination not found: {}", dest_dir
            )
            self._app_name = app_name
            if app_type == AppType.APP:
                self._app_dir = f"{dest_dir}/{app_name}"
                self._create_app(app_name, app_ext)
            elif app_type == AppType.WIDGET:
                self._app_dir = f"{dest_dir}"
                self._create_widget(app_name)
            elif app_type == AppType.QT_APP:
                self._app_dir = f"{dest_dir}/{app_name}"
                self._create_qt_app(app_name, app_ext)
            else:
                raise TypeError(f"Unsupported application type: {app_type}")
        except OSError as err:
            syserr(f'Could not create application "{app_name}"!\n  => {str(err)}')
            self._parent_app.exit(ExitStatus.FAILED.val)

        sysout(f"Successfully created the {app_type.value} {app_name}")

    def _create_app(self, app_name: str, app_ext: List[AppExtension]) -> None:
        """Create a Simple HsPyLib application.
        :param app_name the application name.
        :param app_ext the application extensions (gradle, git, ...).
        """
        sysout(f"Application: {app_name}")
        self._create_base_app_struct(app_name)
        self._mkfile(
            f"src/main/{self._app_name}/__main__.py",
            (self.TEMPLATES / "main.py.tpl")
            .read_text()
            .replace("%APP_NAME%", self._app_name),
        )
        self._apply_extensions(app_name, app_ext)

    def _create_qt_app(self, app_name: str, app_ext: List[AppExtension]) -> None:
        """Create an HsPyLib QT application.
        :param app_name the application name.
        :param app_ext the application extensions (gradle, git, ...).
        """
        sysout(f"QT Application: {app_name}")
        self._create_base_app_struct(app_name)
        self._mkdir(f"src/main/{self._app_name}/resources/forms")
        self._mkfile(
            f"src/main/{self._app_name}/resources/forms/main_qt_view.ui",
            (self.TEMPLATES / "main_qt_view.ui.tpl").read_text(),
        )
        self._mkdir(f"src/main/{self._app_name}/view")
        self._mkfile(
            f"src/main/{self._app_name}/view/main_qt_view.py",
            (self.TEMPLATES / "main_qt_view.py.tpl")
            .read_text()
            .replace("%APP_NAME%", self._app_name),
        )
        self._mkfile(
            f"src/main/{self._app_name}/__main__.py",
            (self.TEMPLATES / "main_qt.py.tpl")
            .read_text()
            .replace("%APP_NAME%", self._app_name),
        )
        self._apply_extensions(app_name, app_ext)

    def _create_widget(self, app_name: str) -> None:
        """Create an HsPyLib Widget application.
        :param app_name the application name.
        """
        widget_name = camelcase(app_name).replace("_", "").replace(" ", "")
        sysout(f"Widget: {widget_name}")
        self._mkfile(
            f"widget_{app_name.lower()}.py",
            (self.TEMPLATES / "widget.py.tpl")
            .read_text()
            .replace("_WIDGET_NAME_", f"{camelcase(app_name, capitalized=True)}"),
        )

    def _create_base_app_struct(self, app_name: str) -> None:
        """Create a base HsPyLib application structure and files.
        :param app_name the application name.
        """
        self._mkdir()
        self._mkfile("README.md", f"# {app_name}")
        self._mkfile("MANIFEST.in")
        self._mkdir("src")
        self._mkdir("src/test")
        self._mkfile(
            "src/test/test_main.py", (self.TEMPLATES / "test_main.py.tpl").read_text()
        )
        self._mkdir("src/test/resources")
        self._mkfile(
            "src/test/resources/application-test.properties",
            "# Main test application property file",
        )
        self._mkdir("src/main")
        self._mkdir(f"src/main/{self._app_name}")
        self._mkfile(
            f"src/main/{self._app_name}/__classpath__.py",
            (self.TEMPLATES / "classpath.py.tpl").read_text(),
        )
        self._mkfile(f"src/main/{self._app_name}/.version", str(INITIAL_REVISION))
        self._mkfile(f"src/main/{self._app_name}/welcome.txt", WELCOME_MESSAGE)
        self._mkdir(f"src/main/{self._app_name}/resources")
        self._mkfile(
            f"src/main/{self._app_name}/resources/application.properties",
            "# Main application property file",
        )
        self._mkfile(
            ".env", "# Type in here the environment variables your app requires"
        )
        self._mkfile(
            "run.sh",
            (self.TEMPLATES / "run.sh.tpl")
            .read_text()
            .replace("%APP_NAME%", self._app_name),
        )
        self._chmod("run.sh")

    def _mkdir(self, folder_name: str = "") -> None:
        """Create a directory from the destination path, or the destination path itself.
        :param folder_name the directory to be created.
        """
        dir_path = f"{self._app_dir}/{folder_name}"
        sysout(f"  |- {dir_path}")
        os.mkdir(dir_path)

    def _mkfile(self, file_name: str, file_content: str = "") -> None:
        """Create a file from the destination path with the specified content.
        :param file_name the file name.
        :param file_content the text based content of the file.
        """
        file_path = f"{self._app_dir}/{file_name}"
        sysout(f"  |- {file_path}")
        with open(f"{file_path}", "w", encoding=Charset.UTF_8.val) as fh:
            fh.write(ensure_endswith(file_content, os.linesep))

    def _chmod(self, file_name: str) -> None:
        """Give execute permissions to the file.
        :param file_name the file name
        """
        file_path = f"{self._app_dir}/{file_name}"
        st = os.stat(file_path)
        os.chmod(file_path, st.st_mode | stat.S_IEXEC)

    def _apply_extensions(self, app_name: str, app_ext: List[AppExtension]) -> None:
        """Apply the selected extensions to the app.
        :param app_name the application name.
        :param app_ext the application extensions (gradle, git, ...).
        """
        result = True

        if result and AppExtension.GIT in app_ext:
            sysout("Initializing git repository")
            result &= self._init_git()
        if result and AppExtension.GRADLE in app_ext:
            sysout("Applying gradle extensions")
            result &= self._init_gradle(app_name)

        if result:
            sysout("All app extensions successfully applied!")
        else:
            syserr("Failed to apply app extensions!")

    def _init_gradle(self, app_name: str) -> bool:
        """Initialize the as a gradle project.
        :param app_name the application name.
        """
        sysout(
            f'Initializing "{app_name}" gradle project [press ENTER to continue] ...'
        )
        output, err_out, exit_code = Terminal.shell_exec(
            f"gradle init --project-name {app_name} --type basic --dsl groovy",
            cwd=self._app_dir,
        )
        sysout(f"Gradle execution result: {exit_code}%EOL%{output}{err_out}%EOL%")

        if exit_code == ExitStatus.SUCCESS:
            sysout("Downloading gradle extensions ...")
            self._download_gradle_ext("badges.gradle")
            self._download_gradle_ext("build-info.gradle")
            self._download_gradle_ext("dependencies.gradle")
            self._download_gradle_ext("docgen.gradle")
            self._download_gradle_ext("docker.gradle")
            self._download_gradle_ext("pypi-publish.gradle")
            self._download_gradle_ext("python.gradle")
            sysout("Creating gradle files")
            self._mkfile(
                "gradle.properties",
                self.GRADLE_PROPS.format(self._app_name, INITIAL_REVISION).strip(),
            )
            self._mkfile(
                "build.gradle",
                (self.TEMPLATES / "build.gradle.tpl")
                .read_text()
                .replace("%APP_NAME%", self._app_name),
            )
            self._mkfile(
                "dependencies.hspd",
                (self.TEMPLATES / "dependencies.hspd.tpl").read_text(),
            )
            sysout("Building gradle project, please wait ...")
            output, err_out, exit_code = Terminal.shell_exec(
                "./gradlew buildOnly", cwd=self._app_dir
            )
            sysout(f"Gradle execution result: {output}{err_out}")

        return exit_code == ExitStatus.SUCCESS

    def _init_git(self) -> bool:
        """Initialize a git repository for the project."""
        self._mkfile(".gitignore", (self.TEMPLATES / "gitignore.tpl").read_text())
        sysout("Initializing git repository ...")
        output, err_out, exit_code = Terminal.shell_exec("git init", cwd=self._app_dir)
        sysout(f"Git init result: {exit_code}%EOL%{output}{err_out}%EOL%")
        if exit_code:
            sysout("Creating first commit")
            Terminal.shell_exec("git add .", cwd=self._app_dir)
            output, err_out, exit_code = Terminal.shell_exec(
                'git commit -m "First commit [@HsPyLib]"', cwd=self._app_dir
            )
            sysout(f"Git commit result: {exit_code}%EOL%{output}{err_out}%EOL%")

        return exit_code == ExitStatus.SUCCESS

    def _download_gradle_ext(self, gradle_ext: str) -> None:
        """Download a gradle extension from the HsPyLib repository.
        :param gradle_ext the HsPyLib gradle extension to download.
        """
        urllib3.disable_warnings()  # Disable this warning because we trust our project repo
        resp = get(
            f"https://raw.githubusercontent.com/yorevs/hspylib/master/gradle/{gradle_ext}"
        )
        check_argument(
            resp.status_code == HttpCode.OK,
            "Unable to download extension: '{}'",
            gradle_ext,
        )
        self._mkfile(f"gradle/{gradle_ext}", resp.body)
