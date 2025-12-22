from .component import get_component_mm
from .device import get_device_mm
from .validation import (
    ValidationStatus,
    ValidationResult,
    ValidationReporter,
    validate_model_file,
    validate_models,
)
from os.path import basename


def build_model(model_fpath, skip_semantics=False):
    model_filename = basename(model_fpath)
    if model_filename.endswith('.hwd'):
        mm = get_component_mm(skip_semantics=skip_semantics)
    elif model_filename.endswith('.dev'):
        mm = get_device_mm(skip_semantics=skip_semantics)
    else:
        raise ValueError('Not a valid model extension.')
    model = mm.model_from_file(model_fpath)
    return model
