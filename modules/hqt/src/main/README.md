<img src="https://iili.io/HYBJFA7.png" width="64" height="64" align="right" />

# HomeSetup Python Library
>
> Because your Python code is not JUST a script !

[![PyPi](https://badgen.net/badge/icon/python?icon=pypi&label)](https://pypi.org/project/hspylib)
[![Gitter](https://badgen.net/badge/icon/gitter?icon=gitter&label)](https://gitter.im/hspylib/community)
[![Donate](https://badgen.net/badge/paypal/donate/yellow)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=J5CDEFLF6M3H4)
[![License](https://badgen.net/badge/license/MIT/gray)](LICENSE.md)
[![Release](https://badgen.net/badge/release/v0.9.45/gray)](docs/CHANGELOG.md#unreleased)
[![build-and-test](https://github.com/yorevs/hspylib/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/yorevs/hspylib/actions/workflows/build-and-test.yml)

HsPyLib is not just a Python library; it's a gateway to elevating your programming experience to new heights. Built on
established principles like **SOLID**, **DRY** (Don't Repeat Yourself), **KISS** (Keep It Simple, Stupid), and **YAGNI**
(You Ain’t Gonna Need It), HsPyLib offers a wealth of frameworks and features. It empowers you to craft sophisticated
Python3 applications, adhering to the philosophy that code should not merely be a simple script - it should be a part
of the 'PYCSNBASS' (Python Code Should Not Be A Simple Script) mindset.

> This project is a part of the [HomeSetup](https://github.com/yorevs/homesetup) project.

## Key Features

- Seamless installation process.
- Application manager offering a helpful scaffold for Python applications.
- Widgets manager for running both 'built-in' and custom Python widgets.
- Improved TUI (Text User Interface) helpers and input methods to enhance your User Experience with terminal applications.
- CRUD (Create, Read, Update, Delete) framework aiding with databases, repositories, and services.
- HTTP request helpers for simplified communication.
- Support for enabling Properties and AppConfigs using popular extensions like .properties, toml, yml, and more.
- Code rigorously tested and consistently adhering to Pylint standards.
- Utilizes the Gradle build system with numerous extensions.
- Diverse set of demos to facilitate a deeper understanding of the library.
- AI model integrations (currently supporting OpenAI).

> Create beautiful menu-select inputs

```python
class SelectableItem:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def __str__(self):
        return f"Name: {self.name} Value: {self.value}"

    def __repr__(self):
        return str(self)


if __name__ == "__main__":
    quantity = 22
    digits = len(str(quantity))
    it = [SelectableItem(f"Item-{n:>0{digits}}", f"Value-{n:>0{digits}}") for n in range(1, quantity)]
    sel = mselect(it)
    print(str(sel))
```

![MenuSelect](https://iili.io/HYBFh74.png "MenuSelect")

> And create beautiful menu-choose inputs

```python
class ChooseableItem:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def __str__(self):
        return f"Name: {self.name} Value: {self.value}"

    def __repr__(self):
        return str(self)


if __name__ == "__main__":
    quantity = 22
    digits = len(str(quantity))
    it = [ChooseableItem(f"Item-{n:>0{digits}}", f"Value-{n:>0{digits}}") for n in range(1, quantity)]
    sel = mchoose(it, [n % 2 == 0 for n in range(1, quantity)])
    print(str(sel))
```

![MenuChoose](https://iili.io/HYBFwp2.png "MenuChoose")

> And also, create beautiful form inputs

```python
from clitt.core.tui.minput.input_validator import InputValidator
from clitt.core.tui.minput.minput import MenuInput, minput

if __name__ == "__main__":
    # fmt: off
    form_fields = MenuInput.builder() \
        .field() \
            .label('letters') \
            .validator(InputValidator.letters()) \
            .build() \
        .field() \
            .label('word') \
            .validator(InputValidator.words()) \
            .build() \
        .field() \
            .label('number') \
            .validator(InputValidator.numbers()) \
            .min_max_length(1, 4) \
            .build() \
        .field() \
            .label('masked') \
            .itype('masked') \
            .value('|##::##::## @@') \
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
            .validator(InputValidator.anything()) \
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
    print(result.__dict__ if result else "None")
```

![MenuInput](https://iili.io/HYBFVrG.png "MenuInput")

> Or even, create nice dashboards:

```python
if __name__ == "__main__":
    # fmt: off
    dashboard_items = MenuDashBoard.builder() \
        .item() \
            .icon(DashboardIcons.POWER) \
            .tooltip('Do something') \
            .on_trigger(lambda: print('Something')) \
            .build() \
        .item() \
            .icon(DashboardIcons.MOVIE) \
            .tooltip('Another something') \
            .on_trigger(lambda: print('Another')) \
            .build() \
        .item() \
            .icon(DashboardIcons.NOTIFICATION) \
            .tooltip('Notify something') \
            .on_trigger(lambda: print('Notification')) \
            .build() \
        .item() \
            .icon(DashboardIcons.LIST) \
            .tooltip('List everything') \
            .on_trigger(lambda: print('List')) \
            .build() \
        .item() \
            .icon(DashboardIcons.DATABASE) \
            .tooltip('Database console') \
            .on_trigger(lambda: print('Database')) \
            .build() \
        .item() \
            .icon(DashboardIcons.EXIT) \
            .tooltip('Exit application') \
            .on_trigger(lambda: print('Exit')) \
            .build() \
        .build()
    # fmt: on

    result = mdashboard(dashboard_items)
```

![MenuDashboard](https://iili.io/HYBFX2f.png "MenuDashboard")

> And even more, create beautiful menus !

```bash
if __name__ == "__main__":
    # fmt: off
    main_menu = TUIMenuFactory \
        .create_main_menu('TUI Main Menu', tooltip='Test Terminal UI Menus') \
            .with_item('Sub-Menu-1') \
                .with_action("DO IT 1", "Let's do it") \
                    .on_trigger(lambda x: print("ACTION 1", x)) \
                .with_view("Just a View 1", "Show the view 1") \
                    .on_render("MY BEAUTIFUL VIEW 1") \
                .with_action("Back", "Back to the previous menu") \
                    .on_trigger(TUIMenuUi.back) \
                .then() \
            .with_item('Sub-Menu-2') \
                .with_action("DO IT 2", "Let's do it too") \
                    .on_trigger(lambda x: print("ACTION 2", x)) \
                .with_view("Just a View 2", "Show the view 2") \
                    .on_render("MY BEAUTIFUL VIEW 2") \
                .with_action("Back", "Back to the previous menu") \
                    .on_trigger(TUIMenuUi.back) \
                .then() \
            .then() \
        .build()
    # fmt: on

    TUIMenuUi(main_menu, "TUI Main Menu").execute()
```

![Menus](https://iili.io/JAGQJkJ.png "Menus")

## PyPi Modules

- [A CLI Terminal](https://pypi.org/project/hspylib-clitt) tools.
- [Datasource](https://pypi.org/project/hspylib-datasource) framework.
- [A Firebase](https://pypi.org/project/hspylib-firebase) integration tool.
- [A PyQt](https://pypi.org/project/hspylib-hqt) application framework.
- [Core](https://pypi.org/project/hspylib) HomeSetup library.
- [A Kafka manager](https://pypi.org/project/hspylib-kafman) application tool.
- [A System Settings](https://pypi.org/project/hspylib-kafman) application tool.
- [A Vault](https://pypi.org/project/hspylib-vault) application tool.

## Installation

### Requirements

#### Python

- Python 3.10 and higher

#### Operating Systems

- Darwin
  + High Sierra and higher
- Linux
  + Ubuntu 16 and higher
  + CentOS 7 and higher
  + Fedora 31 and higher

You may want to install HsPyLib on other OS's and it will probably work, but there are no guarantees that it
**WILL ACTUALLY WORK**.

#### Required software

The following software are required:

- Git (To clone the github repository)
- Gradle (To build the HsPyLib project)

There are some python dependencies, but they will be automatically downloaded when the build runs.

### PyPi

To install HsPyLib from PyPi issue the command:

`# python3 -m pip install hspylib`

To upgrade HsPyLib use the command:

`# python3 -m pip install hspylib --upgrade`

Additional modules that can also be installed:

- [CLItt](https://pypi.org/project/hspylib-clitt) : `# python3 -m pip install hspylib-clitt` to install HsPyLib CLI terminal tools.
- [Firebase](https://pypi.org/project/hspylib-firebase) : `# python3 -m pip install hspylib-firebase` to install HsPyLib Firebase application.
- [Vault](https://pypi.org/project/hspylib-vault) : `# python3 -m pip install hspylib-vault` to install HsPyLib Vault application.
- [Kafman](https://pypi.org/project/hspylib-kafman) : `# python3 -m pip install hspylib-kafman` to install Kafka manager.
- [Datasource](https://pypi.org/project/hspylib-datasource) : `# python3 -m pip install hspylib-datasource` to install datasource helpers.
- [HQT](https://pypi.org/project/hspylib-hqt) : `# python3 -m pip install hspylib-hqt` to install HsPyLib PyQt framework.

### GitHub

To clone HsPyLib into your local machine type the command:

`# git clone https://github.com/yorevs/hspylib.git`

## Documentation

The API documentation can be found [here](docs/api/index.html)

## Support

> Your support and contributions are greatly appreciated in helping us improve and enhance HomeSetup. Together, we can
make it even better!

You can support HomeSetup by [donating](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=J5CDEFLF6M3H4)
or contributing code. Feel free to contact me for further details. When making code contributions, please make sure to
review our [guidelines](docs/CONTRIBUTING.md) and adhere to our [code of conduct](docs/CODE_OF_CONDUCT.md).

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/yorevs)

You can also sponsor it by using our [GitHub Sponsors](https://github.com/sponsors/yorevs) page.

This project is already supported by:

<a href="https://www.jetbrains.com/community/opensource/?utm_campaign=opensource&utm_content=approved&utm_medium=email&utm_source=newsletter&utm_term=jblogo#support">
  <img src="https://resources.jetbrains.com/storage/products/company/brand/logos/jb_beam.png" width="120" height="120">
</a>

Thank you <3 !!

## Known Issues

- [In-Progress] We are aware that there is a problems when using python@3.12 and we are already working on a fix.

## Contacts

- Documentation: [API](docs/api/index.html)
- License: [MIT](LICENSE.md)
- Issue tracker: [HSPyLib-Issues](https://github.com/yorevs/hspylib/issues)
- Official chat: [HSPyLib](https://gitter.im/hspylib/community)
- Contact: [yorevs](https://www.reddit.com/user/yorevs)
- Mailto: [yorevs](mailto:yorevs@hotmail.com)
