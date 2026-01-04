import os
from textx import metamodel_from_file
import textx.scoping.providers as scoping_providers
from textx import get_location, TextXSemanticError
from demol.definitions import *


def component_model_proc(model, metamodel):
    """
    Component model processor with validation.
    """
    from demol.lang.semantics import validate_unique_pin_numbers, validate_board_ports, validate_dependency_sources
    
    # Validate unique pin numbers for the component
    if hasattr(model, 'component'):
        validate_unique_pin_numbers(model.component)
        
        # Validate dependency sources
        validate_dependency_sources(model.component)
        
        # If it's a board, validate its ports
        if model.component.__class__.__name__ == 'Board':
            validate_board_ports(model.component)
    
    from demol.lang.semantics import check_validation_errors
    skip_semantics = getattr(metamodel, 'skip_semantics', False)
    check_validation_errors(model, skip_semantics=skip_semantics)


def get_component_mm(debug=False, skip_semantics=False):
    mm = metamodel_from_file(
        os.path.join(METAMODEL_REPO_PATH, 'component.tx'),
        auto_init_attributes=True,
        textx_tools_support=True,
        debug=debug
    )

    mm.register_scope_providers(
        {
            "*.*": scoping_providers.FQN(),
        }
    )

    mm.register_model_processor(component_model_proc)

    mm.register_obj_processors({

        # EMPTY
    })

    mm.skip_semantics = skip_semantics

    return mm
