1.0.2
-----------------------------

- Updated dependency on `robocorp-tasks` to `>=1,<3`.

1.0.1
-----------------------------

- Updated dependency on `robocorp-tasks` to `^1`.

0.4.4
-----------------------------

- Updated dependency on `robocorp-tasks` to `^0.4`.

0.4.3
-----------------------------

- Updated dependency on `robocorp-tasks` to `^0.3`.

0.4.2
-----------------------------

- Updated dependency on `robocorp-tasks` to `0.3.0`.


0.4.1
-----------------------------

- Added more information in thrown errors

0.4.0
-----------------------------

- New APIs to handle managed instances through the following APIs:
    - `configure()`: configures the default settings used to create the browser.
        - must be called prior to actually calling other APIs.
    - `page()`: gets the current page (creates if needed)
    - `browser()`: gets the current browser (creates if needed)
    - `playwright()`: gets the playwright instance (creates if needed)
    - `context()`: gets the current browser context (creates if needed)
    - `screenshot()`: takes a screenshot and puts contents in the log
- Now requires `robocorp-tasks` and `robocorp-log`.
- The version is now available in `robocorp.browser.__version__`.