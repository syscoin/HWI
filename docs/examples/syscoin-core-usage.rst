Using Syscoin Core with Hardware Wallets
****************************************

This approach is fairly manual, requires the command line, and Syscoin Core >=4.4.2.

Note: For this guide, code lines prefixed with ``$`` means that the command is typed in the terminal. Lines without ``$`` are output of the commands.

Disclaimer
==========

We are not liable for any coins that may be lost through this method. The software mentioned may have bugs. Use at your own risk.

Software
--------

Syscoin Core
^^^^^^^^^^^^

This method of using hardware wallets uses Syscoin Core as the wallet for monitoring the blockchain. It allows a user to use their own full node instead of relying on an SPV wallet or vendor provided software.

HWI works with Syscoin Core >=4.3.0.
However this guide will require Syscoin Core >=4.4.2 as it uses Descriptor Wallets.

Setup
=====

Clone Syscoin Core and build it. Clone HWI.

::

    $ git clone https://github.com/syscoin/syscoin.git
    $ cd syscoin
    $ ./autogen.sh
    $ ./configure
    $ make
    $ src/syscoind -daemon -addresstype=bech32 -changetype=bech32
    $ cd ..
    $ git clone https://github.com/syscoin/HWI.git
    $ cd HWI
    $ python3 setup.py install

You may need some dependencies, on ubuntu install ``libudev-dev`` and ``libusb-1.0-0-dev``

Now we need to find our hardware wallet. We do this using::

    $ ./hwi.py enumerate
    [{"type": "ledger", "model": "ledger_nano_s_plus", "label": null, "path": "DevSrvsID:4294983427", "fingerprint": "c04584f8", "needs_pin_sent": false, "needs_passphrase_sent": false}]

For this example, we will use the Coldcard. As we can see, the device path is ``0003:0005:00``. The fingerprint of the master key is ``c04584f8``. Now that we have the device, we can issue commands to it. So now we want to get some keys and import them into Core.
We will be fetching keys at the BIP 84 default. If ``--path`` and ``--internal`` are not
specified, both receiving and change address descriptors are generated.

::

    $ ./hwi.py -f c04584f8 getkeypool 0 1000
    [{"desc": "wpkh([c04584f8/84h/57h/0h]xpub6CbVv9x2j42AWb1RrkewKtu5FEgwMaJpj5WQNviJzT86imJcwXDVsXVvES2523dYVt2Yf9egTqeopes7jfH7oT2nkLtQqE1fByKxzf6fbNV/0/*)#la4zw75u", "range": [0, 1000], "timestamp": "now", "internal": false, "keypool": true, "active": true, "watchonly": true}, {"desc": "wpkh([c04584f8/84h/57h/0h]xpub6CbVv9x2j42AWb1RrkewKtu5FEgwMaJpj5WQNviJzT86imJcwXDVsXVvES2523dYVt2Yf9egTqeopes7jfH7oT2nkLtQqE1fByKxzf6fbNV/1/*)#wfsrntyy", "range": [0, 1000], "timestamp": "now", "internal": true, "keypool": true, "active": true, "watchonly": true}]

We now create a new Syscoin Core Descriptor Wallet and import the keys into Syscoin Core. The output is formatted properly for Syscoin Core so it can be copy and pasted.

::

    $ ../syscoin/src/syscoin-cli -named createwallet wallet_name=ledger disable_private_keys=true descriptors=true
    {
      "name": "ledger",
      "warning": ""
    }
    $ ../syscoin/src/syscoin-cli -rpcwallet=ledger importdescriptors '[{"desc": "wpkh([c04584f8/84h/57h/0h]xpub6CbVv9x2j42AWb1RrkewKtu5FEgwMaJpj5WQNviJzT86imJcwXDVsXVvES2523dYVt2Yf9egTqeopes7jfH7oT2nkLtQqE1fByKxzf6fbNV/0/*)#la4zw75u", "range": [0, 1000], "timestamp": "now", "internal": false, "keypool": true, "active": true, "watchonly": true}, {"desc": "wpkh([c04584f8/84h/57h/0h]xpub6CbVv9x2j42AWb1RrkewKtu5FEgwMaJpj5WQNviJzT86imJcwXDVsXVvES2523dYVt2Yf9egTqeopes7jfH7oT2nkLtQqE1fByKxzf6fbNV/1/*)#wfsrntyy", "range": [0, 1000], "timestamp": "now", "internal": true, "keypool": true, "active": true, "watchonly": true}]'
    [
      {
        "success": true
      },
      {
        "success": true
      }
    ]

The Syscoin Core wallet is now setup to watch two thousand keys (1000 normal, 1000 change) from your hardware wallet and you can use it to track your balances and create transactions. The transactions will need to be signed through HWI.

If the wallet was previously used, you will need to rescan the blockchain. You can either do this using the ``rescanblockchain`` command or editing the ``timestamp`` in the ``importdescriptors`` command.
Here are some examples (``<blockheight>`` refers to a block height before the wallet was created).

::

    $ ../syscoin/src/syscoin-cli rescanblockchain <blockheight>
    $ ../syscoin/src/syscoin-cli rescanblockchain 500000 # Rescan from block 500000

    $ ../syscoin/src/syscoin-cli -rpcwallet=ledger importdescriptors '[{"desc": "wpkh([c04584f8/84h/57h/0h]xpub6CbVv9x2j42AWb1RrkewKtu5FEgwMaJpj5WQNviJzT86imJcwXDVsXVvES2523dYVt2Yf9egTqeopes7jfH7oT2nkLtQqE1fByKxzf6fbNV/0/*)#la4zw75u", "range": [0, 1000], "timestamp": <blockheight>, "internal": false, "keypool": true, "active": true, "watchonly": true}, {"desc": "wpkh([c04584f8/84h/57h/0h]xpub6CbVv9x2j42AWb1RrkewKtu5FEgwMaJpj5WQNviJzT86imJcwXDVsXVvES2523dYVt2Yf9egTqeopes7jfH7oT2nkLtQqE1fByKxzf6fbNV/1/*)#wfsrntyy", "range": [0, 1000], "timestamp": <blockheight>, "internal": true, "keypool": true, "active": true, "watchonly": true}]'
    $ ../syscoin/src/syscoin-cli -rpcwallet=ledger importdescriptors '[{"desc": "wpkh([c04584f8/84h/57h/0h]xpub6CbVv9x2j42AWb1RrkewKtu5FEgwMaJpj5WQNviJzT86imJcwXDVsXVvES2523dYVt2Yf9egTqeopes7jfH7oT2nkLtQqE1fByKxzf6fbNV/0/*)#la4zw75u", "range": [0, 1000], "timestamp": "500000", "internal": false, "keypool": true, "active": true, "watchonly": true}, {"desc": "wpkh([c04584f8/84h/57h/0h]xpub6CbVv9x2j42AWb1RrkewKtu5FEgwMaJpj5WQNviJzT86imJcwXDVsXVvES2523dYVt2Yf9egTqeopes7jfH7oT2nkLtQqE1fByKxzf6fbNV/1/*)#wfsrntyy", "range": [0, 1000], "timestamp": "500000", "internal": true, "keypool": true, "active": true, "watchonly": true}]' # Imports and rescans from block 500000

Usage
=====

Usage of this primarily involves Syscoin Core. Currently the GUI only supports generating new receive addresses (once all of the keys are imported) so this guide will only cover the command line.

Receiving
---------

From the folder containing ``syscoin`` and ``HWI``, go into ``syscoin``. We will be doing most of the commands here.

::

    $ cd syscoin

To get a new address, use ``getnewaddress`` as you normally would

::

    $ src/syscoin-cli -rpcwallet=ledger getnewaddress
    sys1qvmnd8x2c59zfmkast45gc7k356mdm6jr20mgzh

This address belongs to your hardware wallet. You can check this by doing ``getaddressinfo``::

    $ src/syscoin-cli -rpcwallet=ledger getaddressinfo sys1qvmnd8x2c59zfmkast45gc7k356mdm6jr20mgzh
    {
      "address": "sys1qvmnd8x2c59zfmkast45gc7k356mdm6jr20mgzh",
      "scriptPubKey": "001466e6d39958a1449ddbb05d688c7ad1a6b6ddea43",
      "ismine": true,
      "solvable": true,
      "desc": "wpkh([c04584f8/84'/57'/0'/0/0]020815f579ead84a2889b1181270e60d8aea86ed33f0910465c7b7bb4df9468660)#ky5qntkj",
      "parent_desc": "wpkh([c04584f8/84'/57'/0']xpub6CbVv9x2j42AWb1RrkewKtu5FEgwMaJpj5WQNviJzT86imJcwXDVsXVvES2523dYVt2Yf9egTqeopes7jfH7oT2nkLtQqE1fByKxzf6fbNV/0/*)#ldg7anwl",
      "iswatchonly": false,
      "isscript": false,
      "iswitness": true,
      "witness_version": 0,
      "witness_program": "66e6d39958a1449ddbb05d688c7ad1a6b6ddea43",
      "pubkey": "020815f579ead84a2889b1181270e60d8aea86ed33f0910465c7b7bb4df9468660",
      "ischange": false,
      "timestamp": 1600722790,
      "hdkeypath": "m/84'/57'/0'/0/0",
      "hdseedid": "0000000000000000000000000000000000000000",
      "hdmasterfingerprint": "c04584f8",
      "labels": [
        ""
      ]
    }

You can give this out to people as you normally would. When coins are sent to it, you will see them in your Syscoin Core wallet as watch-only.

Sending
=======
.. Todo: Update to Syscoin PSBT
To send Syscoin, we will use ``walletcreatefundedpsbt``. This will create a Partially Signed Syscoin Transaction which is funded by inputs from the wallets (i.e. your watching only inputs selected with Syscoin Core's coin selection algorithm).
This PSBT can be used with HWI to produce a signed PSBT which can then be finalized and broadcast.

For example, suppose I am sending to 0.01 SYS to sys1qwz7u96hxs768mp7dwqv7947lqyv74a37568urm. First I create a funded psbt with BIP 32 derivation paths to be included::

    $ src/syscoin-cli -rpcwallet=ledger walletcreatefundedpsbt '[]' '[{"sys1qwz7u96hxs768mp7dwqv7947lqyv74a37568urm": 0.01}]' 0 '{"includeWatching":true}' true
    {
      "psbt": "cHNidP8BAHECAAAAASCTHvv5pfzAy/U1E0GAxm1girdVOuKC+P9ZM0X2WPj2AAAAAAD9////AkuahwAAAAAAFgAU0E3TVKQZwup+LviIL/+9cPckEyxAQg8AAAAAABYAFHC9wurmh7R9h81wGeLX3wEZ6vY+AAAAAAABAFICAAAAAbLHoztGRND+QNRLdna/d/KF8uQSHMd9JuAIGHgqFDcEAAAAAAD9////ARjdlgAAAAAAFgAUZubTmVihRJ3bsF1ojHrRprbd6kMAAAAAAQEfGN2WAAAAAAAWABRm5tOZWKFEnduwXWiMetGmtt3qQyIGAggV9Xnq2EooibEYEnDmDYrqhu0z8JEEZce3u035RoZgGMBFhPhUAACAOQAAgAAAAIAAAAAAAAAAAAAiAgLlwYRz+zQdf4MnKBE+vZ9148G0zecYIm75HeqQqn/6gxjARYT4VAAAgDkAAIAAAACAAQAAAAEAAAAAAA==",
      "fee": 0.00000141,
      "changepos": 0
    }


Now I take the updated psbt and inspect it with ``decodepsbt``::

    $ src/syscoin-cli decodepsbt "cHNidP8BAHECAAAAASCTHvv5pfzAy/U1E0GAxm1girdVOuKC+P9ZM0X2WPj2AAAAAAD9////AkuahwAAAAAAFgAU0E3TVKQZwup+LviIL/+9cPckEyxAQg8AAAAAABYAFHC9wurmh7R9h81wGeLX3wEZ6vY+AAAAAAABAFICAAAAAbLHoztGRND+QNRLdna/d/KF8uQSHMd9JuAIGHgqFDcEAAAAAAD9////ARjdlgAAAAAAFgAUZubTmVihRJ3bsF1ojHrRprbd6kMAAAAAAQEfGN2WAAAAAAAWABRm5tOZWKFEnduwXWiMetGmtt3qQyIGAggV9Xnq2EooibEYEnDmDYrqhu0z8JEEZce3u035RoZgGMBFhPhUAACAOQAAgAAAAIAAAAAAAAAAAAAiAgLlwYRz+zQdf4MnKBE+vZ9148G0zecYIm75HeqQqn/6gxjARYT4VAAAgDkAAIAAAACAAQAAAAEAAAAAAA=="
    {
      "tx": {
        "txid": "cb8083a9830938ca426f8e2963a8ba4ff65176fbf7afc241e79839866f720add",
        "hash": "cb8083a9830938ca426f8e2963a8ba4ff65176fbf7afc241e79839866f720add",
        "version": 2,
        "size": 113,
        "vsize": 113,
        "weight": 452,
        "locktime": 0,
        "vin": [
          {
            "txid": "f6f858f6453359fff882e23a55b78a606dc680411335f5cbc0fca5f9fb1e9320",
            "vout": 0,
            "scriptSig": {
              "asm": "",
              "hex": ""
            },
            "sequence": 4294967293
          }
        ],
        "vout": [
          {
            "value": 0.08886859,
            "n": 0,
            "scriptPubKey": {
              "asm": "0 d04dd354a419c2ea7e2ef8882fffbd70f724132c",
              "desc": "addr(sys1q6pxax49yr8pw5l3wlzyzllaawrmjgyev2aeqqc)#6vvmfj6x",
              "hex": "0014d04dd354a419c2ea7e2ef8882fffbd70f724132c",
              "address": "sys1q6pxax49yr8pw5l3wlzyzllaawrmjgyev2aeqqc",
              "type": "witness_v0_keyhash"
            }
          },
          {
            "value": 0.01000000,
            "n": 1,
            "scriptPubKey": {
              "asm": "0 70bdc2eae687b47d87cd7019e2d7df0119eaf63e",
              "desc": "addr(sys1qwz7u96hxs768mp7dwqv7947lqyv74a37568urm)#jhr3jcrd",
              "hex": "001470bdc2eae687b47d87cd7019e2d7df0119eaf63e",
              "address": "sys1qwz7u96hxs768mp7dwqv7947lqyv74a37568urm",
              "type": "witness_v0_keyhash"
            }
          }
        ]
      },
      "global_xpubs": [
      ],
      "psbt_version": 0,
      "proprietary": [
      ],
      "unknown": {
      },
      "inputs": [
        {
          "witness_utxo": {
            "amount": 0.09887000,
            "scriptPubKey": {
              "asm": "0 66e6d39958a1449ddbb05d688c7ad1a6b6ddea43",
              "desc": "addr(sys1qvmnd8x2c59zfmkast45gc7k356mdm6jr20mgzh)#tstr6vhd",
              "hex": "001466e6d39958a1449ddbb05d688c7ad1a6b6ddea43",
              "address": "sys1qvmnd8x2c59zfmkast45gc7k356mdm6jr20mgzh",
              "type": "witness_v0_keyhash"
            }
          },
          "non_witness_utxo": {
            "txid": "f6f858f6453359fff882e23a55b78a606dc680411335f5cbc0fca5f9fb1e9320",
            "hash": "f6f858f6453359fff882e23a55b78a606dc680411335f5cbc0fca5f9fb1e9320",
            "version": 2,
            "size": 82,
            "vsize": 82,
            "weight": 328,
            "locktime": 0,
            "vin": [
              {
                "txid": "0437142a781808e0267dc71c12e4f285f277bf76764bd440fed044463ba3c7b2",
                "vout": 0,
                "scriptSig": {
                  "asm": "",
                  "hex": ""
                },
                "sequence": 4294967293
              }
            ],
            "vout": [
              {
                "value": 0.09887000,
                "n": 0,
                "scriptPubKey": {
                  "asm": "0 66e6d39958a1449ddbb05d688c7ad1a6b6ddea43",
                  "desc": "addr(sys1qvmnd8x2c59zfmkast45gc7k356mdm6jr20mgzh)#tstr6vhd",
                  "hex": "001466e6d39958a1449ddbb05d688c7ad1a6b6ddea43",
                  "address": "sys1qvmnd8x2c59zfmkast45gc7k356mdm6jr20mgzh",
                  "type": "witness_v0_keyhash"
                }
              }
            ]
          },
          "bip32_derivs": [
            {
              "pubkey": "020815f579ead84a2889b1181270e60d8aea86ed33f0910465c7b7bb4df9468660",
              "master_fingerprint": "c04584f8",
              "path": "m/84'/57'/0'/0/0"
            }
          ]
        }
      ],
      "outputs": [
        {
          "bip32_derivs": [
            {
              "pubkey": "02e5c18473fb341d7f832728113ebd9f75e3c1b4cde718226ef91dea90aa7ffa83",
              "master_fingerprint": "c04584f8",
              "path": "m/84'/57'/0'/1/1"
            }
          ]
        },
        {
        }
      ],
      "fee": 0.00000141
    }

Once the transaction has been inspected and everything looks good, the transaction can now be signed using HWI.
.. Todo: Update to Syscoin PSBT
::

    $ cd ../HWI
    $ ./hwi.py -f c04584f8 signtx "cHNidP8BAHECAAAAASCTHvv5pfzAy/U1E0GAxm1girdVOuKC+P9ZM0X2WPj2AAAAAAD9////AkuahwAAAAAAFgAU0E3TVKQZwup+LviIL/+9cPckEyxAQg8AAAAAABYAFHC9wurmh7R9h81wGeLX3wEZ6vY+AAAAAAABAFICAAAAAbLHoztGRND+QNRLdna/d/KF8uQSHMd9JuAIGHgqFDcEAAAAAAD9////ARjdlgAAAAAAFgAUZubTmVihRJ3bsF1ojHrRprbd6kMAAAAAAQEfGN2WAAAAAAAWABRm5tOZWKFEnduwXWiMetGmtt3qQyIGAggV9Xnq2EooibEYEnDmDYrqhu0z8JEEZce3u035RoZgGMBFhPhUAACAOQAAgAAAAIAAAAAAAAAAAAAiAgLlwYRz+zQdf4MnKBE+vZ9148G0zecYIm75HeqQqn/6gxjARYT4VAAAgDkAAIAAAACAAQAAAAEAAAAAAA=="

Follow the onscreen instructions, check everything, and approve the transaction. The result will look like::

    {"psbt": "cHNidP8BAHECAAAAASCTHvv5pfzAy/U1E0GAxm1girdVOuKC+P9ZM0X2WPj2AAAAAAD9////AkuahwAAAAAAFgAU0E3TVKQZwup+LviIL/+9cPckEyxAQg8AAAAAABYAFHC9wurmh7R9h81wGeLX3wEZ6vY+AAAAAAABAFICAAAAAbLHoztGRND+QNRLdna/d/KF8uQSHMd9JuAIGHgqFDcEAAAAAAD9////ARjdlgAAAAAAFgAUZubTmVihRJ3bsF1ojHrRprbd6kMAAAAAAQEfGN2WAAAAAAAWABRm5tOZWKFEnduwXWiMetGmtt3qQyICAggV9Xnq2EooibEYEnDmDYrqhu0z8JEEZce3u035RoZgRzBEAiB8BdTSbZpe2+tNY06QYz1KoKhCftM4Q0Ab4PzdCeQIqAIgNCx/p0JinTATQE9fPC6UilftEPKNhkDDSRM1317u2MYBIgYCCBX1eerYSiiJsRgScOYNiuqG7TPwkQRlx7e7TflGhmAYwEWE+FQAAIA5AACAAAAAgAAAAAAAAAAAACICAuXBhHP7NB1/gycoET69n3XjwbTN5xgibvkd6pCqf/qDGMBFhPhUAACAOQAAgAAAAIABAAAAAQAAAAAA", "signed": true}

We can now take the PSBT, finalize it, and broadcast it with Syscoin Core

.. Todo: Update to Syscoin PSBT
::

    $ cd ../syscoin
    $ src/syscoin-cli finalizepsbt cHNidP8BAHECAAAAASCTHvv5pfzAy/U1E0GAxm1girdVOuKC+P9ZM0X2WPj2AAAAAAD9////AkuahwAAAAAAFgAU0E3TVKQZwup+LviIL/+9cPckEyxAQg8AAAAAABYAFHC9wurmh7R9h81wGeLX3wEZ6vY+AAAAAAABAFICAAAAAbLHoztGRND+QNRLdna/d/KF8uQSHMd9JuAIGHgqFDcEAAAAAAD9////ARjdlgAAAAAAFgAUZubTmVihRJ3bsF1ojHrRprbd6kMAAAAAAQEfGN2WAAAAAAAWABRm5tOZWKFEnduwXWiMetGmtt3qQyICAggV9Xnq2EooibEYEnDmDYrqhu0z8JEEZce3u035RoZgRzBEAiB8BdTSbZpe2+tNY06QYz1KoKhCftM4Q0Ab4PzdCeQIqAIgNCx/p0JinTATQE9fPC6UilftEPKNhkDDSRM1317u2MYBIgYCCBX1eerYSiiJsRgScOYNiuqG7TPwkQRlx7e7TflGhmAYwEWE+FQAAIA5AACAAAAAgAAAAAAAAAAAACICAuXBhHP7NB1/gycoET69n3XjwbTN5xgibvkd6pCqf/qDGMBFhPhUAACAOQAAgAAAAIABAAAAAQAAAAAA
    {
      "hex": "0200000000010120931efbf9a5fcc0cbf535134180c66d608ab7553ae282f8ff593345f658f8f60000000000fdffffff024b9a870000000000160014d04dd354a419c2ea7e2ef8882fffbd70f724132c40420f000000000016001470bdc2eae687b47d87cd7019e2d7df0119eaf63e0247304402207c05d4d26d9a5edbeb4d634e90633d4aa0a8427ed33843401be0fcdd09e408a80220342c7fa742629d3013404f5f3c2e948a57ed10f28d8640c3491335df5eeed8c60121020815f579ead84a2889b1181270e60d8aea86ed33f0910465c7b7bb4df946866000000000",
      "complete": true
    }
    $ src/syscoin-cli sendrawtransaction 0200000000010120931efbf9a5fcc0cbf535134180c66d608ab7553ae282f8ff593345f658f8f60000000000fdffffff024b9a870000000000160014d04dd354a419c2ea7e2ef8882fffbd70f724132c40420f000000000016001470bdc2eae687b47d87cd7019e2d7df0119eaf63e0247304402207c05d4d26d9a5edbeb4d634e90633d4aa0a8427ed33843401be0fcdd09e408a80220342c7fa742629d3013404f5f3c2e948a57ed10f28d8640c3491335df5eeed8c60121020815f579ead84a2889b1181270e60d8aea86ed33f0910465c7b7bb4df946866000000000
    cb8083a9830938ca426f8e2963a8ba4ff65176fbf7afc241e79839866f720add

Refilling the keypools
----------------------

Descriptor wallets will constantly generate new addresses from the imported descriptors.
It is not necessary to import additional keys or descriptors to refresh the keypool, Syscoin Core will do so automatically by using the descriptors.

Derivation Path BIP Compliance
==============================

The instructions above use BIP 84 to derive keys used for P2WPKH addresses (bech32 addresses).
HWI follows BIPs 44, 84, and 49. By default, descriptors will be for P2WPKH addresses with keys derived at ``m/84h/57h/0h/0`` for normal receiving keys and ``m/84h/57h/0h/1`` for change keys.
Using the ``--addr-type legacy`` option will result in P2PKH addresses with keys derived at ``m/44h/57h/0h/0`` for normal receiving keys and ``m/44h/57h/0h/1`` for change keys.
Using the ``--addr-type sh_wit`` option will result in P2SH nested P2WPKH addresses with keys derived at ``m/49h/57h/0h/0`` for normal receiving keys and ``m/49h/57h/0h/1`` for change keys.

To actually get the correct address type when using ``getnewaddress`` from Syscoin Core, you will need to additionally set ``-addresstype=p2sh-segwit`` and ``-changetype=p2sh-segwit``.
This can be set in the command line (as shown in the example) or in your syscoin.conf file.

Alternative derivation paths can also be chosen using the ``--path`` option and specifying your own derivation path.
