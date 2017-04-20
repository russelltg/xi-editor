# Copyright 2017 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
from __future__ import unicode_literals

import sys

from .rpc import RpcPeer
from .cache import LineCache

# max bytes of buffer per request
MAX_FETCH_SIZE = 1024*1024


class PluginPeer(RpcPeer):
    """A proxy object which wraps RPC methods implemented in xi-core."""

    def n_lines(self):
        return self.send_rpc_sync('n_lines', [])

    def get_line(self, i):
        return self.send_rpc_sync('get_line', {'line': i})

    def set_line_fg_spans(self, i, spans):
        self.send_rpc('set_line_fg_spans', {'line': i, 'spans': spans})

    def get_data(self, from_offset, rev, max_size=MAX_FETCH_SIZE):
        return self.send_rpc_sync('get_data', {'offset': from_offset,
                                               "max_size": max_size,
                                               "rev": rev})


class Plugin(object):
    """Base class for python plugins.

    RPC requests are converted to methods with the same same signature.
    A cache of the open buffer is available at `self.lines`.
    """
    def __init__(self):
        self.cache = None

    def __call__(self, method, params, peer):
        params = params or {}
        # intercept these to do bookkeeping, so subclasses don't have to call super
        if method == "init_buf":
            self._init_buf(peer, **params)
        if method == "update":
            self._update(peer, params)
        return getattr(self, method, self.noop)(peer, **params)

    def print_err(self, err):
        print("PLUGIN.PY {}>>> {}".format(type(self).__name__, err),
              file=sys.stderr)
        sys.stderr.flush()

    def ping(self, peer, **kwargs):
        self.print_err("ping")

    def _init_buf(self, peer, rev, buf_size):
        self.print_err("init_buf")
        # fetch an initial chunk (this isn't great: we don't know
        # where the cursor is)
        self.lines = LineCache(buf_size, peer, rev)

    def _update(self, peer, params):
        self.lines.apply_update(peer, **params)

    def noop(self, *args, **kwargs):
        """Default responder for unimplemented RPC methods."""
        return None


def start_plugin(plugin):
    """Opens an RPC connection and runs indefinitely."""
    # this doesn't need to be exported
    peer = PluginPeer(plugin)
    peer.mainloop()
    plugin.print_err("ended main loop")
