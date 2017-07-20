#!/usr/bin/python
# -*- coding: utf-8 -*-
from core import KsysCore

if __name__ == '__main__':
  core = KsysCore()
  # Call the router function and pass the plugin call parameters to it.
  # We use string slicing to trim the leading '?' from the plugin call paramstring
  core.router(sys.argv[2][1:])