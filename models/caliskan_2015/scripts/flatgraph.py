from __future__ import annotations

import json
import os
import struct

from os import PathLike
from typing import Any, BinaryIO, Optional, Union

import zstandard as zstd

MAGIC_BYTES = b"FLT GRPH"
HEADER_FORMAT = f"<{len(MAGIC_BYTES)}sQ"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
assert HEADER_SIZE == 16  # Verify header format is right size


class DeserializationError(IOError):
    pass


class FlatGraph:
    def __init__(
        self,
        name: Optional[Union[str, bytes, PathLike]] = None,
        mode: str = "r",
        fileobj: Optional[BinaryIO] = None,
    ) -> None:

        if not fileobj:
            assert name is not None  # Last resort fail-safe
            fileobj = open(name, "rb")  # managed in __exit__, so pylint: disable=R1732
        else:
            if (
                name is None
                and hasattr(fileobj, "name")
                and isinstance(fileobj.name, (str, bytes))
            ):
                name = fileobj.name

        self.name = os.path.abspath(name) if name else None
        self.fileobj = fileobj

        # Internal structures (initalized during first usage)
        self._pool = None
        self._manifest = None

    @classmethod
    def open(
        cls,
        name: Optional[Union[str, bytes, PathLike]] = None,
        mode: str = "r",
        fileobj: Optional[BinaryIO] = None,
        **kwargs,
    ) -> FlatGraph:
        """Opens a flat graph database for reading, writing, or appending.

        This method serves as the primary interface for creating and managing
        flat graph databases. To interact with a database, either a file name
        or an existing I/O stream must be provided.

        Args:
            name (str | bytes | os.PathLike | None): The name of the flat graph
                database to open or create. Can be a string, bytes, or a
                path-like object.
            mode (str, default="r"): The mode in which to open the file.
                Allowed values are 'r' for reading, 'a' for appending, 'w' for
                writing, and 'x' for creating a new file exclusively.
            fileobj (BinaryIO | None): An existing binary I/O stream
                representing the flat graph database. This takes precedence
                over `name`.

        Returns:
            FlatGraph: An instance of the FlatGraph class representing the
                opened database.

        Raises:
            ValueError: If neither `name` nor `fileobj` is provided.
            FileExistsError: If `mode` is 'x' and the file already exists.
        """

        if not name and not fileobj:
            raise ValueError(
                "Both 'name' and 'fileobj' parameters were not provided. Please pass "
                "a valid file path as 'name', or an open file-like object as 'fileobj'."
            )

        if mode != "r":  # Forward compatability
            raise NotImplementedError("unsupported file mode")

        return cls(name, mode, fileobj)

    @property
    def manifest(self) -> dict[str, Any]:
        if self._manifest is not None:
            return self._manifest

        # The manifest's offset can be found within the file's header, which is
        # always the first's 16 (0x10) bytes of the graph. This header consists
        # of a 8-byte file signature, immediatly followed byte an unsigned long
        # long containing the manifest's offset within the file.
        self.fileobj.seek(0, os.SEEK_SET)
        header = self.fileobj.read(HEADER_SIZE)
        if len(header) < HEADER_SIZE:
            raise DeserializationError(
                f"corrupted file, expected at least {HEADER_SIZE} bytes, but "
                f"only found {len(header)}"
            )

        # Split and deserialize the magic bytes and manifest offset
        header: tuple[bytes, int] = struct.unpack_from(HEADER_FORMAT, header)
        if header[0] != MAGIC_BYTES:
            raise DeserializationError(
                f"corrupted file, expected header {MAGIC_BYTES} ({MAGIC_BYTES.hex(' ')}),"
                f"but found {header[0]} ({header[0].hex(' ')}) instead"
            )

        # Deserialize the manifest (JSON object)
        self.fileobj.seek(header[1], os.SEEK_SET)
        self._manifest = json.load(self.fileobj)
        return self._manifest

    @property
    def pool(self):
        if self._pool is not None:
            return self._pool
        self._pool = []  # Only try to deserialize once
        manifest = self.manifest  # Load graph's manifest

        # The graph's pool is split among two (2) compressed ZStandard streams.
        # The first stream, `stringPoolLength`, contains information regarding
        # the length of each entry, and consequently, the offset of each as
        # well. The second stream, `stringPoolBytes`, contains all of the
        # strings concatinated. All important metadata regarding the stream
        # type, offset, compressed length, and decompressed length are stored
        # within the manifest.

        index_metadata = manifest["stringPoolLength"]
        pool_metadata = manifest["stringPoolBytes"]

        # Parse the pool's index (`stringPoolLength`)
        index_offset = index_metadata["startOffset"]
        index_length = index_metadata["compressedLength"]
        index = self._zstd_decompress(index_offset, index_length)

        # Parse the pool's strings (`stringPoolBytes`)
        pool_offset = pool_metadata["startOffset"]
        pool_length = pool_metadata["compressedLength"]
        pool = self._zstd_decompress(pool_offset, pool_length)

        # Ensure that the stream has been correctly decompressed
        assert len(pool) == pool_metadata["decompressedLength"]
        assert len(index) == index_metadata["decompressedLength"]

        # Process the index into a collection of 32-bit unsigned integers
        if index_metadata["decompressedLength"] % 4:
            raise DeserializationError()
        index_entry_count = index_metadata["decompressedLength"] // 4
        index = struct.unpack(f"<{index_entry_count}I", index)
        assert len(pool) == sum(index)  # Additional error checking :)

        offset = 0  # Running offset for `stringPoolBytes` substrings
        for length in index:
            self._pool.append(pool[offset : offset + length].decode())
            offset += length  # Prepare the offset for the next string
        return self._pool

    def close(self) -> None:
        """Close the underlying file descriptor associated with this graph."""
        self.fileobj.close()

    def _zstd_decompress(self, offset: int, length: int) -> bytes:
        """
        Decompresses a ZStandard stream starting at a specified offset.

        Args:
          offset (int): The absolute byte offset within the file where the
            ZStandard stream begins.
          length (int): The compressed length of the ZStandard stream in bytes.

        Raises:
          DeserializationError: If the end-of-file (EOF) is encountered prematurely
            during decompression.
        """
        self.fileobj.seek(offset)  # Align stream's cursor to the offset

        zstd_stream = self.fileobj.read(length)
        if len(zstd_stream) < length:
            raise DeserializationError(
                "An unexpected end-of-file (EOF) was reached while "
                f"decompressing the ZStandard stream. Expected {length} bytes, "
                f"but only {len(zstd_stream)} bytes were read."
            )

        return zstd.decompress(zstd_stream)

    def __enter__(self) -> FlatGraph:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
