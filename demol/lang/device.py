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
        validate_pwm_connection,
        validate_no_pin_conflicts,
        validate_i2c_address_uniqueness,
        validate_voltage_limits,
        validate_all_peripherals_connected,
        validate_essential_pins_connected,
        validate_broker_requirements,
        validate_io_voltage_compatibility,
        validate_common_ground,
        validate_power_paths,
        validate_connections,
        validate_unique_peripheral_names,
        validate_topic_format,
        validate_single_board,
        validate_broker_security,
        validate_network_requirements,
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
    # Well-Formedness: Essential pins must be connected
    # ========================================================================
    run_rule("Essential Pins", validate_essential_pins_connected, model, desc="All essential peripheral pins are connected")

    # ========================================================================
    # Well-Formedness: Unique peripheral names
    # ========================================================================
    run_rule("Unique Identifiers", validate_unique_peripheral_names, model, desc="All peripherals have unique names")
    
    # ========================================================================
    # Well-Formedness: Broker requirements
    # ========================================================================
    run_rule("Broker Requirements", validate_broker_requirements, model, desc="Broker is configured")
    
    # ========================================================================
    # Well-Formedness: Network requirements (network is configured)
    # ========================================================================
    run_rule("Network Requirements", validate_network_requirements, model, desc="Network is configured")
    
    # ========================================================================
    # Safety: Broker security (authentication for remote brokers)
    # ========================================================================
    run_rule("Broker Security", validate_broker_security, model, desc="Remote brokers have authentication configured")
    
    # ========================================================================
    # Connection Validation
    # ========================================================================
    run_rule("Connection Integrity", validate_connections, model, desc="All pin-to-pin connections are valid")
    
    # ========================================================================
    # Well-Formedness: Common ground check
    # ========================================================================
    run_rule("Common Ground", validate_common_ground, model, desc="Peripherals share a common ground with the board")
    
    # ========================================================================
    # Safety: Power Paths
    # ========================================================================
    run_rule("Power Paths", validate_power_paths, model, desc="All components have a path to a power source")
    
    # ========================================================================
    # Global Safety Validations
    # ========================================================================
    
    # Safety: No pin conflicts (unique pins per connection)
    run_rule("Pin Conflicts", validate_no_pin_conflicts, model, desc="No physical pin conflicts detected")
    
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
    power_sources = []
    
    for use in model.uses:
        if hasattr(use, 'components') and use.components:
            for comp_inst in use.components:
                # Determine type based on the referenced component
                ref_class = comp_inst.ref.__class__.__name__
                if 'Board' in ref_class:
                    if not board:
                        board = comp_inst.ref
                    if not comp_inst.name:
                        comp_inst.name = comp_inst.ref.name
                elif 'PowerSource' in ref_class:
                    power_sources.append(comp_inst)
                else:  # Peripheral (Sensor or Actuator)
                    peripherals.append(comp_inst)
    
    # Create a synthetic 'components' object for backward compatibility
    model.components = SimpleNamespace(
        board=board,
        peripherals=peripherals,
        powerSources=power_sources
    )
    
    device_name = model.metadata.name.strip('"')
    
    for c in model.connections:
        # Set the board for easy navigation in M2M and M2T transformations
        setattr(c, 'board', board)
        
        def resolve_target(comp_inst):
            if not comp_inst:
                return None, "unknown", None
            # comp_inst is now a ComponentInstance (BoardDef, PeripheralDef, or PowerSourceDef)
            if hasattr(comp_inst, 'ref'):
                return comp_inst.ref, getattr(comp_inst, 'name', comp_inst.ref.name), comp_inst
            else:
                return comp_inst, getattr(comp_inst, 'name', 'unknown'), None

        from_ref, from_name, from_inst = resolve_target(c.from_comp)
        
        if hasattr(c, 'to_comp') and c.to_comp:
            to_ref, to_name, to_inst = resolve_target(c.to_comp)
        else:
            # Default to board if to_comp is missing
            to_ref, to_name, to_inst = board, board.name if board else "board", None

        # Store resolved endpoints on the connection object
        setattr(c, '_from_ref', from_ref)
        setattr(c, '_from_name', from_name)
        setattr(c, '_from_inst', from_inst)
        setattr(c, '_to_ref', to_ref)
        setattr(c, '_to_name', to_name)
        setattr(c, '_to_inst', to_inst)

        # Backward compatibility: set 'peripheral' and 'target' attributes
        # We assume the 'from_comp' is the primary peripheral if it's not the board
        # Otherwise, we check 'to_comp'.
        primary_inst = from_inst if from_inst else to_inst
        if primary_inst:
            setattr(c, 'peripheral', primary_inst)
            # 'target' attribute for backward compatibility with some older logic
            # that might expect c.target.target
            setattr(c, 'target', SimpleNamespace(target=primary_inst))
        
        target_ref = from_ref if from_inst else to_ref
        target_name = from_name if from_inst else to_name

        # ====================================================================
        # Auto-generate topic if not specified (if broker or network is present)
        # ====================================================================
        has_net = (hasattr(model, 'broker') and model.broker) or (hasattr(model, 'network') and model.network)
        if has_net and not c.remote and target_ref and hasattr(target_ref, 'type'):
            peripheral_type = type(target_ref).__name__
            peripheral_msg = target_ref.type
            
            default_topic = f'"{device_name}.{peripheral_type}.{peripheral_msg}.{target_name}"'
            c.remote = default_topic.lower().strip('""')
            

def get_device_mm(debug: bool = False, global_repo: bool = False, skip_semantics: bool = False):
    mm = metamodel_from_file(
        os.path.join(METAMODEL_REPO_PATH, 'device.tx'),
        auto_init_attributes=True,
        global_repository=global_repo,
        textx_tools_support=True,
        debug=debug
    )

    from textx import register_language
    from demol.lang.component import get_component_mm
    component_mm = get_component_mm(skip_semantics=skip_semantics)

    # Register component language explicitly for .hwd files.
    # This ensures that FQNGlobalRepo uses the correct metamodel.
    try:
        register_language('demol-component', pattern='*.hwd', metamodel=component_mm)
    except Exception:
        pass

    mm.register_scope_providers(
        {
            "*.*": scoping_providers.FQN(),
            "*.*": scoping_providers.FQNImportURI(importAs=True),
            "ComponentInstance.ref": scoping_providers.FQNGlobalRepo(
                os.path.join(DEVICES_MODEL_REPO_PATH, '*/*.hwd')
            ),
            "Connect.from_comp": "~uses.components",
            "Connect.to_comp": "~uses.components"
        }
    )

    # Register component metamodel for cross-metamodel scoping (+m:component)
    mm.referenced_languages['component'] = component_mm

    mm.register_model_processor(model_proc)

    mm.register_obj_processors({
        # EMPTY
    })

    mm.skip_semantics = skip_semantics

    return mm
