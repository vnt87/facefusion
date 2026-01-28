import sys
import traceback
from facefusion import core

sys.argv = ['facefusion.py', 'run-api', '--modal']
try:
    print("Calling core.cli()...")
    core.cli()
    print("core.cli() returned normally")
except SystemExit as e:
    print(f"SystemExit caught: {e.code}")
    traceback.print_exc()
except Exception as e:
    print(f"Exception caught: {e}")
    traceback.print_exc()
