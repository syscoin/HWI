
import re
from typing import (
    List,
    Optional,
)
from .key import (
    ExtendedKey,
    KeyOriginInfo,
    parse_path,
)

from collections import namedtuple

# From: https://github.com/syscoin/syscoin/blob/master/src/script/descriptor.cpp

def PolyMod(c, val):
    c0 = c >> 35
    c = ((c & 0x7ffffffff) << 5) ^ val
    if (c0 & 1):
        c ^= 0xf5dee51989
    if (c0 & 2):
        c ^= 0xa9fdca3312
    if (c0 & 4):
        c ^= 0x1bab10e32d
    if (c0 & 8):
        c ^= 0x3706b1677a
    if (c0 & 16):
        c ^= 0x644d626ffd
    return c

def DescriptorChecksum(desc):
    INPUT_CHARSET = "0123456789()[],'/*abcdefgh@:$%{}IJKLMNOPQRSTUVWXYZ&+-.;<=>?!^_|~ijklmnopqrstuvwxyzABCDEFGH`#\"\\ "
    CHECKSUM_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

    c = 1
    cls = 0
    clscount = 0
    for ch in desc:
        pos = INPUT_CHARSET.find(ch)
        if pos == -1:
            return ""
        c = PolyMod(c, pos & 31)
        cls = cls * 3 + (pos >> 5)
        clscount += 1
        if clscount == 3:
            c = PolyMod(c, cls)
            cls = 0
            clscount = 0
    if clscount > 0:
        c = PolyMod(c, cls)
    for j in range(0, 8):
        c = PolyMod(c, 0)
    c ^= 1

    ret = [None] * 8
    for j in range(0, 8):
        ret[j] = CHECKSUM_CHARSET[(c >> (5 * (7 - j))) & 31]
    return ''.join(ret)

def AddChecksum(desc):
    return desc + "#" + DescriptorChecksum(desc)

class Descriptor:
    def __init__(self, origin_fingerprint, origin_path, base_key, path_suffix, testnet, sh_wpkh, wpkh):
        self.origin_fingerprint = origin_fingerprint
        self.origin_path = origin_path
        self.path_suffix = path_suffix
        self.base_key = base_key
        self.testnet = testnet
        self.sh_wpkh = sh_wpkh
        self.wpkh = wpkh
        self.m_path = None

        if origin_path:
            self.m_path_base = "m" + origin_path
            self.m_path = "m" + origin_path + (path_suffix or "")

    @classmethod
    def parse(cls, desc, testnet=False):
        sh_wpkh = None
        wpkh = None
        origin_fingerprint = None
        origin_path = None
        base_key_and_path_match = None
        base_key = None
        path_suffix = None

        # Check the checksum
        check_split = desc.split('#')
        if len(check_split) > 2:
            return None
        if len(check_split) == 2:
            if len(check_split[1]) != 8:
                return None
            checksum = DescriptorChecksum(check_split[0])
            if not checksum.strip():
                return None
            if checksum != check_split[1]:
                return None
        desc = check_split[0]

        if desc.startswith("sh(wpkh("):
            sh_wpkh = True
        elif desc.startswith("wpkh("):
            wpkh = True

        origin_match = re.search(r"\[(.*)\]", desc)
        if origin_match:
            origin = origin_match.group(1)
            match = re.search(r"^([0-9a-fA-F]{8})(\/.*)", origin)
            if match:
                origin_fingerprint = match.group(1)
                origin_path = match.group(2)
                # Replace h with '
                origin_path = origin_path.replace('h', '\'')

            base_key_and_path_match = re.search(r"\[.*\](\w+)([\/\)][\d'\/\*]*)", desc)
        else:
            base_key_and_path_match = re.search(r"\((\w+)([\/\)][\d'\/\*]*)", desc)

        if base_key_and_path_match:
            base_key = base_key_and_path_match.group(1)
            path_suffix = base_key_and_path_match.group(2)
            if path_suffix == ")":
                path_suffix = None
        else:
            if origin_match is None:
                return None

        return cls(origin_fingerprint, origin_path, base_key, path_suffix, testnet, sh_wpkh, wpkh)

    def serialize(self):
        descriptor_open = 'pkh('
        descriptor_close = ')'
        origin = ''
        path_suffix = ''

        if self.wpkh:
            descriptor_open = 'wpkh('
        elif self.sh_wpkh:
            descriptor_open = 'sh(wpkh('
            descriptor_close = '))'

        if self.origin_fingerprint and self.origin_path:
            origin = '[' + self.origin_fingerprint + self.origin_path + ']'

        if self.path_suffix:
            path_suffix = self.path_suffix

        return AddChecksum(descriptor_open + origin + self.base_key + path_suffix + descriptor_close)



ExpandedScripts = namedtuple("ExpandedScripts", ["output_script", "redeem_script", "witness_script"])


class MultisigDescriptor(Descriptor):
    """
    A descriptor for ``multi()`` and ``sortedmulti()`` descriptors
    """
    def __init__(
        self,
        pubkeys: List['PubkeyProvider'],
        thresh: int,
        is_sorted: bool
    ) -> None:
        r"""
        :param pubkeys: The :class:`PubkeyProvider`\ s for this descriptor
        :param thresh: The number of keys required to sign this multisig
        :param is_sorted: Whether this is a ``sortedmulti()`` descriptor
        """
        super().__init__(pubkeys, [], "sortedmulti" if is_sorted else "multi")
        self.thresh = thresh
        self.is_sorted = is_sorted
        if self.is_sorted:
            self.pubkeys.sort()

    def to_string_no_checksum(self, hardened_char: str = "h") -> str:
        return "{}({},{})".format(self.name, self.thresh, ",".join([p.to_string(hardened_char) for p in self.pubkeys]))

    def expand(self, pos: int) -> "ExpandedScripts":
        if self.thresh > 16:
            m = b"\x01" + self.thresh.to_bytes(1, "big")
        else:
            m = (self.thresh + 0x50).to_bytes(1, "big") if self.thresh > 0 else b"\x00"
        n = (len(self.pubkeys) + 0x50).to_bytes(1, "big") if len(self.pubkeys) > 0 else b"\x00"
        script: bytes = m
        der_pks = [p.get_pubkey_bytes(pos) for p in self.pubkeys]
        if self.is_sorted:
            der_pks.sort()
        for pk in der_pks:
            script += len(pk).to_bytes(1, "big") + pk
        script += n + b"\xae"

        return ExpandedScripts(script, None, None)


class PubkeyProvider(object):
    """
    A public key expression in a descriptor.
    Can contain the key origin info, the pubkey itself, and subsequent derivation paths for derivation from the pubkey
    The pubkey can be a typical pubkey or an extended pubkey.
    """

    def __init__(
        self,
        origin: Optional['KeyOriginInfo'],
        pubkey: str,
        deriv_path: Optional[str]
    ) -> None:
        """
        :param origin: The key origin if one is available
        :param pubkey: The public key. Either a hex string or a serialized extended pubkey
        :param deriv_path: Additional derivation path if the pubkey is an extended pubkey
        """
        self.origin = origin
        self.pubkey = pubkey
        self.deriv_path = deriv_path

        # Make ExtendedKey from pubkey if it isn't hex
        self.extkey = None
        try:
            unhexlify(self.pubkey)
            # Is hex, normal pubkey
        except Exception:
            # Not hex, maybe xpub
            self.extkey = ExtendedKey.deserialize(self.pubkey)

    @classmethod
    def parse(cls, s: str) -> 'PubkeyProvider':
        """
        Deserialize a key expression from the string into a ``PubkeyProvider``.
        :param s: String containing the key expression
        :return: A new ``PubkeyProvider`` containing the details given by ``s``
        """
        origin = None
        deriv_path = None

        if s[0] == "[":
            end = s.index("]")
            origin = KeyOriginInfo.from_string(s[1:end])
            s = s[end + 1:]

        pubkey = s
        slash_idx = s.find("/")
        if slash_idx != -1:
            pubkey = s[:slash_idx]
            deriv_path = s[slash_idx:]

        return cls(origin, pubkey, deriv_path)

    def to_string(self, hardened_char: str = "h") -> str:
        """
        Serialize the pubkey expression to a string to be used in a descriptor
        :return: The pubkey expression as a string
        """
        s = ""
        if self.origin:
            s += "[{}]".format(self.origin.to_string(hardened_char))
        s += self.pubkey
        if self.deriv_path:
            s += self.deriv_path
        return s

    def get_pubkey_bytes(self, pos: int) -> bytes:
        if self.extkey is not None:
            if self.deriv_path is not None:
                path_str = self.deriv_path[1:]
                if path_str[-1] == "*":
                    path_str = path_str[-1] + str(pos)
                path = parse_path(path_str)
                child_key = self.extkey.derive_pub_path(path)
                return child_key.pubkey
            else:
                return self.extkey.pubkey
        return unhexlify(self.pubkey)

    def get_full_derivation_path(self, pos: int) -> str:
        """
        Returns the full derivation path at the given position, including the origin
        """
        path = self.origin.get_derivation_path() if self.origin is not None else "m/"
        path += self.deriv_path if self.deriv_path is not None else ""
        if path[-1] == "*":
            path = path[:-1] + str(pos)
        return path

    def get_full_derivation_int_list(self, pos: int) -> List[int]:
        """
        Returns the full derivation path as an integer list at the given position.
        Includes the origin and master key fingerprint as an int
        """
        path: List[int] = self.origin.get_full_int_list() if self.origin is not None else []
        if self.deriv_path is not None:
            der_split = self.deriv_path.split("/")
            for p in der_split:
                if not p:
                    continue
                if p == "*":
                    i = pos
                elif p[-1] in "'phHP":
                    assert len(p) >= 2
                    i = int(p[:-1]) | 0x80000000
                else:
                    i = int(p)
                path.append(i)
        return path

    def __lt__(self, other: 'PubkeyProvider') -> bool:
        return self.pubkey < other.pubkey
