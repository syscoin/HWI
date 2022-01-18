"""
PSBT Classes and Utilities
**************************
"""

import base64
import struct

from io import BytesIO, BufferedReader
from typing import (
    Dict,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from .key import KeyOriginInfo
from .errors import PSBTSerializationError
from .tx import (
    CTransaction,
    CTxInWitness,
    CTxOut,
)
from ._serialize import (
    deser_compact_size,
    deser_string,
    Readable,
    ser_compact_size,
    ser_string,
)

def DeserializeHDKeypath(
    f: Readable,
    key: bytes,
    hd_keypaths: MutableMapping[bytes, KeyOriginInfo],
    expected_sizes: Sequence[int],
) -> None:
    """
    :meta private:

    Deserialize a serialized PSBT public key and keypath key-value pair.

    :param f: The byte stream to read the value from.
    :param key: The bytes of the key of the key-value pair.
    :param hd_keypaths: Dictionary of public key bytes to their :class:`~hwilib.key.KeyOriginInfo`.
    :param expected_sizes: List of key lengths expected for the keypair being deserialized.
    """
    if len(key) not in expected_sizes:
        raise PSBTSerializationError("Size of key was not the expected size for the type partial signature pubkey. Length: {}".format(len(key)))
    pubkey = key[1:]
    if pubkey in hd_keypaths:
        raise PSBTSerializationError("Duplicate key, input partial signature for pubkey already provided")

    hd_keypaths[pubkey] = KeyOriginInfo.deserialize(deser_string(f))

def SerializeHDKeypath(hd_keypaths: Mapping[bytes, KeyOriginInfo], type: bytes) -> bytes:
    """
    :meta private:

    Serialize a public key to :class:`~hwilib.key.KeyOriginInfo` mapping as a PSBT key-value pair.

    :param hd_keypaths: The mapping of public key to keypath
    :param type: The PSBT type bytes to use
    :returns: The serialized keypaths
    """
    r = b""
    for pubkey, path in sorted(hd_keypaths.items()):
        r += ser_string(type + pubkey)
        packed = path.serialize()
        r += ser_string(packed)
    return r

class PartiallySignedInput:
    """
    An object for a PSBT input map.
    """

    PSBT_IN_NON_WITNESS_UTXO = 0x00
    PSBT_IN_WITNESS_UTXO = 0x01
    PSBT_IN_PARTIAL_SIG = 0x02
    PSBT_IN_SIGHASH_TYPE = 0x03
    PSBT_IN_REDEEM_SCRIPT = 0x04
    PSBT_IN_WITNESS_SCRIPT = 0x05
    PSBT_IN_BIP32_DERIVATION = 0x06
    PSBT_IN_FINAL_SCRIPTSIG = 0x07
    PSBT_IN_FINAL_SCRIPTWITNESS = 0x08
    PSBT_IN_TAP_KEY_SIG = 0x13
    PSBT_IN_TAP_SCRIPT_SIG = 0x14
    PSBT_IN_TAP_LEAF_SCRIPT = 0x15
    PSBT_IN_TAP_BIP32_DERIVATION = 0x16
    PSBT_IN_TAP_INTERNAL_KEY = 0x17
    PSBT_IN_TAP_MERKLE_ROOT = 0x18

    def __init__(self) -> None:
        self.non_witness_utxo: Optional[CTransaction] = None
        self.witness_utxo: Optional[CTxOut] = None
        self.partial_sigs: Dict[bytes, bytes] = {}
        self.sighash: Optional[int] = None
        self.redeem_script = b""
        self.witness_script = b""
        self.hd_keypaths: Dict[bytes, KeyOriginInfo] = {}
        self.final_script_sig = b""
        self.final_script_witness = CTxInWitness()
        self.tap_key_sig = b""
        self.tap_script_sigs: Dict[Tuple[bytes, bytes], bytes] = {}
        self.tap_scripts: Dict[Tuple[bytes, int], Set[bytes]] = {}
        self.tap_bip32_paths: Dict[bytes, Tuple[Set[bytes], KeyOriginInfo]] = {}
        self.tap_internal_key = b""
        self.tap_merkle_root = b""
        self.unknown: Dict[bytes, bytes] = {}

    def set_null(self) -> None:
        """
        Clear all values in this PSBT input map.
        """
        self.non_witness_utxo = None
        self.witness_utxo = None
        self.partial_sigs.clear()
        self.sighash = None
        self.redeem_script = b""
        self.witness_script = b""
        self.hd_keypaths.clear()
        self.final_script_sig = b""
        self.final_script_witness = CTxInWitness()
        self.tap_key_sig = b""
        self.tap_script_sigs.clear()
        self.tap_scripts.clear()
        self.tap_bip32_paths.clear()
        self.tap_internal_key = b""
        self.tap_merkle_root = b""
        self.unknown.clear()

    def deserialize(self, f: Readable) -> None:
        """
        Deserialize a serialized PSBT input.

        :param f: A byte stream containing the serialized PSBT input
        """
        key_lookup: Set[bytes] = set()

        while True:
            # read the key
            try:
                key = deser_string(f)
            except Exception:
                break

            # Check for separator
            if len(key) == 0:
                break

            # First byte of key is the type
            key_type = struct.unpack("b", bytearray([key[0]]))[0]

            if key_type == PartiallySignedInput.PSBT_IN_NON_WITNESS_UTXO:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate Key, input non witness utxo already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("non witness utxo key is more than one byte type")
                self.non_witness_utxo = CTransaction()
                utxo_bytes = BufferedReader(BytesIO(deser_string(f))) # type: ignore
                self.non_witness_utxo.deserialize(utxo_bytes)
                self.non_witness_utxo.rehash()
            elif key_type == PartiallySignedInput.PSBT_IN_WITNESS_UTXO:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate Key, input witness utxo already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("witness utxo key is more than one byte type")
                self.witness_utxo = CTxOut()
                tx_out_bytes = BufferedReader(BytesIO(deser_string(f))) # type: ignore
                self.witness_utxo.deserialize(tx_out_bytes)
            elif key_type == PartiallySignedInput.PSBT_IN_PARTIAL_SIG:
                if len(key) != 34 and len(key) != 66:
                    raise PSBTSerializationError("Size of key was not the expected size for the type partial signature pubkey")
                pubkey = key[1:]
                if pubkey in self.partial_sigs:
                    raise PSBTSerializationError("Duplicate key, input partial signature for pubkey already provided")

                sig = deser_string(f)
                self.partial_sigs[pubkey] = sig
            elif key_type == PartiallySignedInput.PSBT_IN_SIGHASH_TYPE:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, input sighash type already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("sighash key is more than one byte type")
                sighash_bytes = deser_string(f)
                self.sighash = struct.unpack("<I", sighash_bytes)[0]
            elif key_type == PartiallySignedInput.PSBT_IN_REDEEM_SCRIPT:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, input redeemScript already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("redeemScript key is more than one byte type")
                self.redeem_script = deser_string(f)
            elif key_type == PartiallySignedInput.PSBT_IN_WITNESS_SCRIPT:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, input witnessScript already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("witnessScript key is more than one byte type")
                self.witness_script = deser_string(f)
            elif key_type == PartiallySignedInput.PSBT_IN_BIP32_DERIVATION:
                DeserializeHDKeypath(f, key, self.hd_keypaths, [34, 66])
            elif key_type == PartiallySignedInput.PSBT_IN_FINAL_SCRIPTSIG:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, input final scriptSig already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("final scriptSig key is more than one byte type")
                self.final_script_sig = deser_string(f)
            elif key_type == PartiallySignedInput.PSBT_IN_FINAL_SCRIPTWITNESS:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, input final scriptWitness already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("final scriptWitness key is more than one byte type")
                witness_bytes = BufferedReader(BytesIO(deser_string(f))) # type: ignore
                self.final_script_witness.deserialize(witness_bytes)
            elif key_type == PartiallySignedInput.PSBT_IN_TAP_KEY_SIG:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, input Taproot key signature already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("Input Taproot key signature key is more than one byte type")
                self.tap_key_sig = deser_string(f)
                if len(self.tap_key_sig) < 64:
                    raise PSBTSerializationError("Input Taproot key path signature is shorter than 64 bytes")
                elif len(self.tap_key_sig) > 65:
                    raise PSBTSerializationError("Input Taproot key path signature is longer than 65 bytes")
            elif key_type == PartiallySignedInput.PSBT_IN_TAP_SCRIPT_SIG:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, input Taproot script signature already provided")
                elif len(key) != 65:
                    raise PSBTSerializationError("Input Taproot script signature key is not 65 bytes")
                xonly = key[1:33]
                script_hash = key[33:65]
                sig = deser_string(f)
                if len(sig) < 64:
                    raise PSBTSerializationError("Input Taproot script path signature is shorter than 64 bytes")
                elif len(sig) > 65:
                    raise PSBTSerializationError("Input Taproot script path signature is longer than 65 bytes")
                self.tap_script_sigs[(xonly, script_hash)] = sig
            elif key_type == PartiallySignedInput.PSBT_IN_TAP_LEAF_SCRIPT:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, input Taproot leaf script already provided")
                elif len(key) < 34:
                    raise PSBTSerializationError("Input Taproot leaf script key is not at least 34 bytes")
                elif (len(key) - 2) % 32 != 0:
                    raise PSBTSerializationError("Input Taproot leaf script key's control block is not valid")
                script = deser_string(f)
                if len(script) == 0:
                    raise PSBTSerializationError("Intput Taproot leaf script cannot be empty")
                leaf_script = (script[:-1], int(script[-1]))
                if leaf_script not in self.tap_scripts:
                    self.tap_scripts[leaf_script] = set()
                self.tap_scripts[(script[:-1], int(script[-1]))].add(key[1:])
            elif key_type == PartiallySignedInput.PSBT_IN_TAP_BIP32_DERIVATION:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, input Taproot BIP 32 keypath already provided")
                elif len(key) != 33:
                    raise PSBTSerializationError("Input Taproot BIP 32 keypath key is not 33 bytes")
                xonly = key[1:33]
                value = deser_string(f)
                vs = BytesIO(value)
                num_hashes = deser_compact_size(vs)
                leaf_hashes = set()
                for i in range(0, num_hashes):
                    leaf_hashes.add(vs.read(32))
                self.tap_bip32_paths[xonly] = (leaf_hashes, KeyOriginInfo.deserialize(vs.read()))
            elif key_type == PartiallySignedInput.PSBT_IN_TAP_INTERNAL_KEY:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, input Taproot internal key already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("Input Taproot internal key key is more than one byte type")
                self.tap_internal_key = deser_string(f)
                if len(self.tap_internal_key) != 32:
                    raise PSBTSerializationError("Input Taproot internal key is not 32 bytes")
            elif key_type == PartiallySignedInput.PSBT_IN_TAP_MERKLE_ROOT:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, input Taproot merkle root already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("Input Taproot merkle root key is more than one byte type")
                self.tap_merkle_root = deser_string(f)
                if len(self.tap_merkle_root) != 32:
                    raise PSBTSerializationError("Input Taproot merkle root is not 32 bytes")
            else:
                if key in self.unknown:
                    raise PSBTSerializationError("Duplicate key, key for unknown value already provided")
                unknown_bytes = deser_string(f)
                self.unknown[key] = unknown_bytes

            key_lookup.add(key)

    def serialize(self) -> bytes:
        """
        Serialize this PSBT input

        :returns: The serialized PSBT input
        """
        r = b""

        if self.non_witness_utxo:
            r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_NON_WITNESS_UTXO))
            tx = self.non_witness_utxo.serialize_with_witness()
            r += ser_string(tx)

        if self.witness_utxo:
            r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_WITNESS_UTXO))
            tx = self.witness_utxo.serialize()
            r += ser_string(tx)

        if len(self.final_script_sig) == 0 and self.final_script_witness.is_null():
            for pubkey, sig in sorted(self.partial_sigs.items()):
                r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_PARTIAL_SIG) + pubkey)
                r += ser_string(sig)

            if self.sighash is not None:
                r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_SIGHASH_TYPE))
                r += ser_string(struct.pack("<I", self.sighash))

            if len(self.redeem_script) != 0:
                r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_REDEEM_SCRIPT))
                r += ser_string(self.redeem_script)

            if len(self.witness_script) != 0:
                r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_WITNESS_SCRIPT))
                r += ser_string(self.witness_script)

            r += SerializeHDKeypath(self.hd_keypaths, ser_compact_size(PartiallySignedInput.PSBT_IN_BIP32_DERIVATION))

            if len(self.tap_key_sig) != 0:
                r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_TAP_KEY_SIG))
                r += ser_string(self.tap_key_sig)

            for (xonly, leaf_hash), sig in self.tap_script_sigs.items():
                r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_TAP_SCRIPT_SIG) + xonly + leaf_hash)
                r += ser_string(sig)

            for (script, leaf_ver), control_blocks in self.tap_scripts.items():
                for control_block in control_blocks:
                    r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_TAP_LEAF_SCRIPT) + control_block)
                    r += ser_string(script + struct.pack("B", leaf_ver))

            for xonly, (leaf_hashes, origin) in self.tap_bip32_paths.items():
                r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_TAP_BIP32_DERIVATION) + xonly)
                value = ser_compact_size(len(leaf_hashes))
                for lh in leaf_hashes:
                    value += lh
                value += origin.serialize()
                r += ser_string(value)

            if len(self.tap_internal_key) != 0:
                r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_TAP_INTERNAL_KEY))
                r += ser_string(self.tap_internal_key)

            if len(self.tap_merkle_root) != 0:
                r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_TAP_MERKLE_ROOT))
                r += ser_string(self.tap_merkle_root)

        if len(self.final_script_sig) != 0:
            r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_FINAL_SCRIPTSIG))
            r += ser_string(self.final_script_sig)

        if not self.final_script_witness.is_null():
            r += ser_string(ser_compact_size(PartiallySignedInput.PSBT_IN_FINAL_SCRIPTWITNESS))
            witstack = self.final_script_witness.serialize()
            r += ser_string(witstack)

        for key, value in sorted(self.unknown.items()):
            r += ser_string(key)
            r += ser_string(value)

        r += b"\x00"

        return r

class PartiallySignedOutput:
    """
    An object for a PSBT output map.
    """

    PSBT_OUT_REDEEM_SCRIPT = 0x00
    PSBT_OUT_WITNESS_SCRIPT = 0x01
    PSBT_OUT_BIP32_DERIVATION = 0x02
    PSBT_OUT_TAP_INTERNAL_KEY = 0x05
    PSBT_OUT_TAP_TREE = 0x06
    PSBT_OUT_TAP_BIP32_DERIVATION = 0x07

    def __init__(self) -> None:
        self.redeem_script = b""
        self.witness_script = b""
        self.hd_keypaths: Dict[bytes, KeyOriginInfo] = {}
        self.tap_internal_key = b""
        self.tap_tree = b""
        self.tap_bip32_paths: Dict[bytes, Tuple[Set[bytes], KeyOriginInfo]] = {}
        self.unknown: Dict[bytes, bytes] = {}

    def set_null(self) -> None:
        """
        Clear this PSBT output map
        """
        self.redeem_script = b""
        self.witness_script = b""
        self.hd_keypaths.clear()
        self.tap_internal_key = b""
        self.tap_tree = b""
        self.tap_bip32_paths.clear()
        self.unknown.clear()

    def deserialize(self, f: Readable) -> None:
        """
        Deserialize a serialized PSBT output map

        :param f: A byte stream containing the serialized PSBT output
        """
        key_lookup: Set[bytes] = set()

        while True:
            # read the key
            try:
                key = deser_string(f)
            except Exception:
                break

            # Check for separator
            if len(key) == 0:
                break

            # First byte of key is the type
            key_type = struct.unpack("b", bytearray([key[0]]))[0]

            if key_type == PartiallySignedOutput.PSBT_OUT_REDEEM_SCRIPT:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, output redeemScript already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("Output redeemScript key is more than one byte type")
                self.redeem_script = deser_string(f)
            elif key_type == PartiallySignedOutput.PSBT_OUT_WITNESS_SCRIPT:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, output witnessScript already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("Output witnessScript key is more than one byte type")
                self.witness_script = deser_string(f)
            elif key_type == PartiallySignedOutput.PSBT_OUT_BIP32_DERIVATION:
                DeserializeHDKeypath(f, key, self.hd_keypaths, [34, 66])
            elif key_type == PartiallySignedOutput.PSBT_OUT_TAP_INTERNAL_KEY:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, output Taproot internal key already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("Output Taproot internal key key is more than one byte type")
                self.tap_internal_key = deser_string(f)
                if len(self.tap_internal_key) != 32:
                    raise PSBTSerializationError("Output Taproot internal key is not 32 bytes")
            elif key_type == PartiallySignedOutput.PSBT_OUT_TAP_TREE:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, output Taproot tree already provided")
                elif len(key) != 1:
                    raise PSBTSerializationError("Output Taproot tree key is more than one byte type")
                self.tap_tree = deser_string(f)
            elif key_type == PartiallySignedOutput.PSBT_OUT_TAP_BIP32_DERIVATION:
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, output Taproot BIP 32 keypath already provided")
                elif len(key) != 33:
                    raise PSBTSerializationError("Output Taproot BIP 32 keypath key is not 33 bytes")
                xonly = key[1:33]
                value = deser_string(f)
                vs = BytesIO(value)
                num_hashes = deser_compact_size(vs)
                leaf_hashes = set()
                for i in range(0, num_hashes):
                    leaf_hashes.add(vs.read(32))
                self.tap_bip32_paths[xonly] = (leaf_hashes, KeyOriginInfo.deserialize(vs.read()))
            else:
                if key in self.unknown:
                    raise PSBTSerializationError("Duplicate key, key for unknown value already provided")
                value = deser_string(f)
                self.unknown[key] = value

            key_lookup.add(key)

    def serialize(self) -> bytes:
        """
        Serialize this PSBT output

        :returns: The serialized PSBT output
        """
        r = b""
        if len(self.redeem_script) != 0:
            r += ser_string(ser_compact_size(PartiallySignedOutput.PSBT_OUT_REDEEM_SCRIPT))
            r += ser_string(self.redeem_script)

        if len(self.witness_script) != 0:
            r += ser_string(ser_compact_size(PartiallySignedOutput.PSBT_OUT_WITNESS_SCRIPT))
            r += ser_string(self.witness_script)

        r += SerializeHDKeypath(self.hd_keypaths, ser_compact_size(PartiallySignedOutput.PSBT_OUT_BIP32_DERIVATION))

        if len(self.tap_internal_key) != 0:
            r += ser_string(ser_compact_size(PartiallySignedOutput.PSBT_OUT_TAP_INTERNAL_KEY))
            r += ser_string(self.tap_internal_key)

        if len(self.tap_tree) != 0:
            r += ser_string(ser_compact_size(PartiallySignedOutput.PSBT_OUT_TAP_TREE))
            r += ser_string(self.tap_tree)

        for xonly, (leaf_hashes, origin) in self.tap_bip32_paths.items():
            r += ser_string(ser_compact_size(PartiallySignedOutput.PSBT_OUT_TAP_BIP32_DERIVATION) + xonly)
            value = ser_compact_size(len(leaf_hashes))
            for lh in leaf_hashes:
                value += lh
            value += origin.serialize()
            r += ser_string(value)

        for key, value in sorted(self.unknown.items()):
            r += ser_string(key)
            r += ser_string(value)

        r += b"\x00"

        return r

class PSBT(object):
    """
    A class representing a PSBT
    """

    PSBT_GLOBAL_UNSIGNED_TX = 0x00
    PSBT_GLOBAL_XPUB = 0x01

    def __init__(self, tx: Optional[CTransaction] = None) -> None:
        """
        :param tx: A Syscoin transaction that specifies the inputs and outputs to use
        """
        if tx:
            self.tx = tx
        else:
            self.tx = CTransaction()
        self.inputs: List[PartiallySignedInput] = []
        self.outputs: List[PartiallySignedOutput] = []
        self.unknown: Dict[bytes, bytes] = {}
        self.xpub: Dict[bytes, KeyOriginInfo] = {}

    def deserialize(self, psbt: str) -> None:
        """
        Deserialize a base 64 encoded PSBT.

        :param psbt: A base 64 PSBT.
        """
        psbt_bytes = base64.b64decode(psbt.strip())
        f = BufferedReader(BytesIO(psbt_bytes)) # type: ignore
        end = len(psbt_bytes)

        # Read the magic bytes
        magic = f.read(5)
        if magic != b"psbt\xff":
            raise PSBTSerializationError("invalid magic")

        key_lookup: Set[bytes] = set()

        # Read loop
        while True:
            # read the key
            try:
                key = deser_string(f)
            except Exception:
                break

            # Check for separator
            if len(key) == 0:
                break

            # First byte of key is the type
            key_type = struct.unpack("b", bytearray([key[0]]))[0]

            # Do stuff based on type
            if key_type == PSBT.PSBT_GLOBAL_UNSIGNED_TX:
                # Checks for correctness
                if key in key_lookup:
                    raise PSBTSerializationError("Duplicate key, unsigned tx already provided")
                elif len(key) > 1:
                    raise PSBTSerializationError("Global unsigned tx key is more than one byte type")

                # read in value
                tx_bytes = BufferedReader(BytesIO(deser_string(f))) # type: ignore
                self.tx.deserialize(tx_bytes)

                # Make sure that all scriptSigs and scriptWitnesses are empty
                for txin in self.tx.vin:
                    if len(txin.scriptSig) != 0 or not self.tx.wit.is_null():
                        raise PSBTSerializationError("Unsigned tx does not have empty scriptSigs and scriptWitnesses")
            elif key_type == PSBT.PSBT_GLOBAL_XPUB:
                DeserializeHDKeypath(f, key, self.xpub, [79])
            else:
                if key in self.unknown:
                    raise PSBTSerializationError("Duplicate key, key for unknown value already provided")
                unknown_bytes = deser_string(f)
                self.unknown[key] = unknown_bytes

            key_lookup.add(key)

        # make sure that we got an unsigned tx
        if self.tx.is_null():
            raise PSBTSerializationError("No unsigned trasaction was provided")

        # Read input data
        for txin in self.tx.vin:
            if f.tell() == end:
                break
            input = PartiallySignedInput()
            input.deserialize(f)
            self.inputs.append(input)

            if input.non_witness_utxo:
                input.non_witness_utxo.rehash()
                if input.non_witness_utxo.sha256 != txin.prevout.hash:
                    raise PSBTSerializationError("Non-witness UTXO does not match outpoint hash")

        if (len(self.inputs) != len(self.tx.vin)):
            raise PSBTSerializationError("Inputs provided does not match the number of inputs in transaction")

        # Read output data
        for txout in self.tx.vout:
            if f.tell() == end:
                break
            output = PartiallySignedOutput()
            output.deserialize(f)
            self.outputs.append(output)

        if len(self.outputs) != len(self.tx.vout):
            raise PSBTSerializationError("Outputs provided does not match the number of outputs in transaction")

    def serialize(self) -> str:
        """
        Serialize the PSBT as a base 64 encoded string.

        :returns: The base 64 encoded string.
        """
        r = b""

        # magic bytes
        r += b"psbt\xff"

        # unsigned tx flag
        r += ser_string(ser_compact_size(PSBT.PSBT_GLOBAL_UNSIGNED_TX))

        # write serialized tx
        tx = self.tx.serialize_with_witness()
        r += ser_compact_size(len(tx))
        r += tx

        # write xpubs
        r += SerializeHDKeypath(self.xpub, ser_compact_size(PSBT.PSBT_GLOBAL_XPUB))

        # unknowns
        for key, value in sorted(self.unknown.items()):
            r += ser_string(key)
            r += ser_string(value)

        # separator
        r += b"\x00"

        # inputs
        for input in self.inputs:
            r += input.serialize()

        # outputs
        for output in self.outputs:
            r += output.serialize()

        # return hex string
        return base64.b64encode(r).decode()
