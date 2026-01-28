import sys
import shutil
from facefusion import core

def pre_check() -> bool:
s.version_info < (3, 10):
t(f"Python version too old: {sys.version_info}")
 False

ot shutil.which('curl'):
t("curl NOT found")
 False

ot shutil.which('ffmpeg'):
t("ffmpeg NOT found")
 False
t("pre_check() PASSED")
 True

pre_check()
