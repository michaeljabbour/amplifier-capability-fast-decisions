#!/usr/bin/env python3
"""Meaningful local functional checks; no provider calls or production activation."""
import asyncio
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

class Gate(unittest.TestCase):
    def test_installed_deterministic_diagnosis_uses_explicit_isolated_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            r=subprocess.run([sys.executable,'-m','amplifier_fast_decisions.smart_cli','diagnose','--offline','--events',str(Path(d)/'events'),'--state-file',str(Path(d)/'state.json')],cwd=d,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            out=json.loads(r.stdout);self.assertIsInstance(out,dict)
            self.assertFalse((Path(d)/'events').exists())

if __name__=='__main__':unittest.main(verbosity=2)
