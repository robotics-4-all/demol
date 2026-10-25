"""paths"""

import os

THIS_DIR_PATH = os.path.dirname(__file__)

# CURRENT_PATH = os.path.abspath(os.getcwd())
REPO_PATH = os.path.dirname(THIS_DIR_PATH)
CODE_PATH = os.path.join(REPO_PATH, "demol")  # + "/demol"
SMAUTO_TEMPLATES = os.path.join(CODE_PATH, "templates", "smauto")
TEMPLATES = os.path.join(CODE_PATH, "templates", "riot")
TEMPLATES_RPI = os.path.join(CODE_PATH, "templates", "rpi")
TEMPLATES_DOCS = os.path.join(CODE_PATH, "templates", "docs")
TEMPLATES_ZEPHYR = os.path.join(CODE_PATH, "templates", "zephyr")
TEMPLATES_WOKWI = os.path.join(CODE_PATH, "templates", "wokwi")
TEMPLATES_RENODE = os.path.join(CODE_PATH, "templates", "renode")
METAMODEL_REPO_PATH = os.path.join(THIS_DIR_PATH, "grammar")

DEVICES_MODEL_REPO_PATH = os.getenv("DEVICES_MODEL_REPO_PATH", os.path.join(THIS_DIR_PATH, "builtin_models"))
