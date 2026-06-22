from demol.lang import build_model
from demol.transformations import m2t_device_svg
import os

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
model_path = os.path.join(PROJECT_ROOT, "examples/rpi/rpi_5_TCRT.dev")
print(f"Loading model from {model_path}")
model = build_model(model_path)
if model:
    print("Model loaded successfully.")
    m2t_device_svg(model, "output.svg")
    if os.path.exists("output.svg"):
        print("Successfully generated output.svg")
    else:
        print("Failed to generate output.svg")
else:
    print("Failed to load model.")
