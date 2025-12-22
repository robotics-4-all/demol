import os
from textx import metamodel_from_file
import textx.scoping.providers as scoping_providers
from textx import get_location, TextXSemanticError
from demol.definitions import *


GRAMMAR_BULTINS = {}


def raise_validation_error(obj, msg):
    raise TextXSemanticError(
        f'{msg}',
        **get_location(obj)
    )


def model_proc(model, metamodel):
    """
    Enhanced model processor with comprehensive validation based on formal semantics.
    
    Implements validation rules from SEMANTICS.md:
    - Section 4.1: Well-formedness rules
    - Section 6.7: Invariants
    - Section 8.1: Safety properties
    - Section 8.4: Well-formedness conditions
    """
    from demol.lang.semantics import (
        raise_validation_error,
        validate_power_connection,
        validate_gpio_connection,
        validate_i2c_connection,
        validate_spi_connection,
        validate_uart_connection,
        validate_no_pin_conflicts,
        validate_i2c_address_uniqueness,
        validate_voltage_limits,
        validate_all_peripherals_connected,
        validate_broker_requirements,
        validate_io_voltage_compatibility,
        validate_common_ground,
        validate_connections,
        validate_unique_peripheral_names,
        validate_topic_format,
        validate_single_board,
        validate_broker_security,
        clear_validation_results,
        check_validation_errors,
        get_validation_errors,
        get_passed_rules,
        report_passed_rule,
    )
    import click
    import os
    
    device_name = model.metadata.name.strip('"')

    print(f'[*] Processing model: {model._tx_filename}')
    
    # Reset validation results for this run
    clear_validation_results()

    def run_rule(name, func, *args, desc=""):
        """Helper to run a validation rule and track if it passed"""
        err_before = len(get_validation_errors())
        func(*args)
        err_after = len(get_validation_errors())
        if err_after == err_before:
            report_passed_rule(name, desc)
    
    # ========================================================================
    # Model Enrichment (including broker property processing)
    # ========================================================================
    enrich_model(model)
    
    # ========================================================================
    # Well-Formedness: Single board
    # ========================================================================
    run_rule("Single Board", validate_single_board, model, desc="Exactly one board is defined")
    
    # ========================================================================
    # Well-Formedness: All peripherals must be connected
    # ========================================================================
    run_rule("Peripheral Connectivity", validate_all_peripherals_connected, model, desc="All declared peripherals are connected")

    # ========================================================================
    # Well-Formedness: Unique peripheral names
    # ========================================================================
    run_rule("Unique Identifiers", validate_unique_peripheral_names, model, desc="All peripherals have unique names")
    
    # ========================================================================
    # Well-Formedness: Broker requirements
    # ========================================================================
    run_rule("Broker Requirements", validate_broker_requirements, model, desc="Broker is configured if remote endpoints exist")
    
    # ========================================================================
    # Safety: Broker security (authentication for remote brokers)
    # ========================================================================
    run_rule("Broker Security", validate_broker_security, model, desc="Remote brokers have authentication configured")
    
    # ========================================================================
    # Well-Formedness: Common ground check
    # ========================================================================
    run_rule("Common Ground", validate_common_ground, model, desc="Peripherals share a common ground with the board")
    
    # ========================================================================
    # Connection Validation
    # ========================================================================
    run_rule("Connection Integrity", validate_connections, model, desc="All pin-to-pin connections are valid")
    
    # ========================================================================
    # Global Safety Validations
    # ========================================================================
    
    # Safety: No pin conflicts (unique pins per connection)
    run_rule("Pin Conflicts", validate_no_pin_conflicts, model.connections, desc="No physical pin conflicts detected")
    
    # Safety: I2C addresses must be unique on the same bus
    run_rule("I2C Address Uniqueness", validate_i2c_address_uniqueness, model.connections, desc="I2C slave addresses are unique per bus")
    
    # Safety: Voltage limits must not be exceeded
    run_rule("Voltage Limits", validate_voltage_limits, model, desc="Peripheral voltage limits are respected")
    
    # Safety: IO Voltage compatibility
    run_rule("IO Voltage Compatibility", validate_io_voltage_compatibility, model, desc="Board and peripheral IO voltages match")
    
    # ========================================================================
    # Topic Format Validation (based on broker type)
    # ========================================================================
    run_rule("Topic Format", validate_topic_format, model, desc="MQTT/AMQP topics follow protocol conventions")
    
    # ========================================================================
    # Final Error Check: Stop if any errors were reported
    # ========================================================================
    skip_semantics = getattr(metamodel, 'skip_semantics', False)
    check_validation_errors(model, skip_semantics=skip_semantics)
    
    errors = get_validation_errors()
    if not errors:
        print("[✓] All validation checks passed!")
    else:
        print(f"[!] Model built with {len(errors)} semantic error(s) (skip_semantics=True)")


def enrich_model(model):
    """
    Enrich the model with auto-generated values.
    Extracts board and peripherals from USE statements.
    Creates auth object from broker auth properties.
    """
    from types import SimpleNamespace
    
    # ========================================================================
    # Process Broker Authentication (create auth object)
    # ========================================================================
    if hasattr(model, 'broker') and model.broker:
        auth_attrs = {}
        
        # Check for auth properties and collect them
        if hasattr(model.broker, 'auth_username'):
            auth_attrs['username'] = model.broker.auth_username
        if hasattr(model.broker, 'auth_password'):
            auth_attrs['password'] = model.broker.auth_password
        if hasattr(model.broker, 'auth_key'):
            auth_attrs['key'] = model.broker.auth_key
        
        # Create auth object if there are auth properties
        if auth_attrs:
            auth_obj = SimpleNamespace(**auth_attrs)
            setattr(model.broker, 'auth', auth_obj)
    
    # ========================================================================
    # Extract board and peripherals from USE statements
    # ========================================================================
    board = None
    peripherals = []
    
    for use in model.uses:
        # Check the type of use - it could be BoardUse or PeripheralUse
        use_type = use.__class__.__name__
        
        if use_type == 'BoardUse':
            board = use.board
        elif use_type == 'PeripheralUse':
            peripherals.extend(use.peripherals)
        # Fallback for backward compatibility
        elif hasattr(use, 'board') and use.board:
            board = use.board
        elif hasattr(use, 'peripherals') and use.peripherals:
            peripherals.extend(use.peripherals)
    
    # Create a synthetic 'components' object for backward compatibility
    model.components = SimpleNamespace(
        board=board,
        peripherals=peripherals
    )
    
    device_name = model.metadata.name.strip('"')
    
    for c in model.connections:
        # Set the board for easy navigation in M2M and M2T transformations
        setattr(c, 'board', board)
        
        # ====================================================================
        # Auto-generate topic if not specified
        # ====================================================================
        if not c.remote:
            peripheral_def = c.peripheral
            peripheral_ref = peripheral_def.ref
            peripheral_def_name = peripheral_def.name
            peripheral_type = type(peripheral_ref).__name__
            peripheral_msg = peripheral_ref.type
            
            default_topic = f'"{device_name}.{peripheral_type}.{peripheral_msg}.{peripheral_def_name}"'
            c.remote = default_topic.lower().strip('""')


def get_device_mm(debug: bool = False, global_repo: bool = False, skip_semantics: bool = False):
    mm = metamodel_from_file(
        os.path.join(METAMODEL_REPO_PATH, 'device.tx'),
        auto_init_attributes=True,
        global_repository=global_repo,
        textx_tools_support=True,
        debug=debug
    )

    mm.register_scope_providers(
        {
            "*.*": scoping_providers.FQN(),
            "*.*": scoping_providers.FQNImportURI(importAs=True),
            "Use.peripherals": scoping_providers.FQNGlobalRepo(
                os.path.join(PERIPHERAL_MODEL_REPO_PATH, '*.hwd')
            ),
            "Use.board": scoping_providers.FQNGlobalRepo(
                os.path.join(BOARD_MODEL_REPO_PATH, '*.hwd')
            ),

        }
    )

    mm.register_model_processor(model_proc)

    mm.register_obj_processors({

        # EMPTY
    })

    mm.skip_semantics = skip_semantics

    return mm
