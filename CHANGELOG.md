# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.html).

## [1.0.0] - 2025-08-27

### Added
- Created a standalone Windows executable (`.exe`).
- Developed a modern GUI using CustomTkinter for entering configuration.
- Added a real-time logging panel to display script progress and errors.
- Implemented a "Stop" button to gracefully cancel running operations.
- Configuration is now saved to and loaded from a `config.json` file.
- The application window now starts maximized for better usability.

### Changed
- Refactored standalone worker scripts (`download_history.py`, `process_data.py`) into importable functions.
- Replaced fragile `subprocess` calls with direct, in-process function calls, eliminating the "duplicate window" bug.
- Improved the download logic to use a robust state file (`state.json`) to track initial download completion, allowing for proper resuming of interrupted downloads.

### Fixed
- Resolved `ModuleNotFoundError` for `tkinter` in certain Python environments.
- Corrected PyInstaller build errors related to path separators and missing assets.
- Fixed a logical flaw where the script would incorrectly report "Already up to date" on an incomplete initial download.