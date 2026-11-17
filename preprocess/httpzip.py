"""Seekable HTTP file for reading single members of huge remote zips (e.g. the
194 GB RSNA archive on AWS Open Data) via range requests."""
import io
import urllib.request


class HttpFile(io.RawIOBase):
    def __init__(self, url, block=1 << 20):
        self.url, self.pos, self.block = url, 0, block
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req) as r:
            self.size = int(r.headers["Content-Length"])
        self._cache = {}

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def _fetch(self, start, end):
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end - 1}"})
        with urllib.request.urlopen(req) as r:
            return r.read()

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        if n > self.block:
            data = self._fetch(self.pos, self.pos + n)
        else:
            b0 = self.pos // self.block
            out = b""
            for b in range(b0, (self.pos + n - 1) // self.block + 1):
                if b not in self._cache:
                    if len(self._cache) > 64:
                        self._cache.clear()
                    self._cache[b] = self._fetch(b * self.block, min((b + 1) * self.block, self.size))
                out += self._cache[b]
            off = self.pos - b0 * self.block
            data = out[off:off + n]
        self.pos += len(data)
        return data

    def readinto(self, b):
        d = self.read(len(b))
        b[:len(d)] = d
        return len(d)
