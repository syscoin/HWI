# Syscoin Hardware Wallet Interface

[![Build Status](https://travis-ci.org/syscoin/HWI.svg?branch=master)](https://travis-ci.org/syscoin/HWI)

The Syscoin Hardware Wallet Interface is a Python library and command line tool for interacting with hardware wallets.
It provides a standard way for software to work with hardware wallets without needing to implement device specific drivers.
Python software can use the provided library (`hwilib`). Software in other languages can execute the `hwi` tool.

## Prerequisites

Python 3 is required. The libraries and [udev rules](hwilib/udev/README.md) for each device must also be installed. Some libraries will need to be installed

For Ubuntu/Debian:
```
sudo apt install libusb-1.0-0-dev libudev-dev
```

For macOS:
```
brew install libusb
```

This project uses the [Poetry](https://github.com/sdispater/poetry) dependency manager.
Once HWI's source has been downloaded with git clone, it and its dependencies can be installed via poetry by execting the following in the root source directory:

```
poetry install
```

Pip can also be used to install all of the dependencies (in virtualenv or system) required for operation and development. See `pyproject.toml` for all dependencies. Dependencies under `[tool.poetry.dependecies]` are user dependencies, and `[tool.poetry.dev-dependencies]` for development based dependencies.

## Install

```
git clone https://github.com/syscoin/HWI.git
cd HWI
```

## Usage

To use, first enumerate all devices and find the one that you want to use with

```
./hwi.py enumerate
```

Once the device type and device path is known, issue commands to it like so:

```
./hwi.py -t <type> -d <path> <command> <command args>
```

All output will be in JSON form and sent to `stdout`.
Additional information or prompts will be sent to `stderr` and will not necessarily be in JSON.
This additional information is for debugging purposes.

## Device Support

The below table lists what devices and features are supported for each device.

Please also see [docs](docs/) for additional information about each device.

| Feature \ Device | Ledger Nano X | Ledger Nano S | Trezor One | Trezor Model T | Digital BitBox | KeepKey | Coldcard |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Support Planned | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Implemented | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| xpub retrieval | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Message Signing | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Device Setup | N/A | N/A | Yes | Yes | Yes | Yes | N/A |
| Device Wipe | N/A | N/A | Yes | Yes | Yes | Yes | N/A |
| Device Recovery | N/A | N/A | Yes | Yes | N/A | Yes | N/A |
| Device Backup | N/A | N/A | N/A | N/A | Yes | N/A | Yes |
| P2PKH Inputs | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| P2SH-P2WPKH Inputs | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| P2WPKH Inputs | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| P2SH Multisig Inputs | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| P2SH-P2WSH Multisig Inputs | Yes | Yes | Yes | Yes | Yes | No | Yes |
| P2WSH Multisig Inputs | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Bare Multisig Inputs | Yes | Yes | N/A | N/A | Yes | N/A | N/A |
| Arbitrary scriptPubKey Inputs | Yes | Yes | N/A | N/A | Yes | N/A | N/A |
| Arbitrary redeemScript Inputs | Yes | Yes | N/A | N/A | Yes | N/A | N/A |
| Arbitrary witnessScript Inputs | Yes | Yes | N/A | N/A | Yes | N/A | N/A |
| Non-wallet inputs | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Mixed Segwit and Non-Segwit Inputs | N/A | N/A | Yes | N/A | Yes | Yes | Yes |
| Display on device screen | Yes | Yes | Yes | Yes | N/A | Yes | Yes |

## Using with Syscoin Core

See [Using Syscoin Core with Hardware Wallets](docs/syscoin-core-usage.md).

## License

This project is available under the MIT License, Copyright Jagdeep Sidhu && Andrew Chow
