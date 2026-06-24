import logging
import os

from textx import metamodel_from_file
import textx.scoping.providers as scoping_providers
from demol.definitions import METAMODEL_REPO_PATH, DEVICES_MODEL_REPO_PATH

logger = logging.getLogger(__name__)


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
        validate_multi_broker,
        clear_validation_results,
        check_validation_errors,
        get_validation_errors,
        report_passed_rule,
    )

    if getattr(metamodel, "_skip_semantics", False):
        enrich_model(model)
        return

    logger.info("Processing model: %s", model._tx_filename)

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
    run_rule(
        "Single Board",
        validate_single_board,
        model,
        desc="Exactly one board is defined",
    )

    # ========================================================================
    # Well-Formedness: All peripherals must be connected
    # ========================================================================
    run_rule(
        "Peripheral Connectivity",
        validate_all_peripherals_connected,
        model,
        desc="All declared peripherals are connected",
    )

    # ========================================================================
    # Well-Formedness: Essential pins must be connected
    # ========================================================================
    run_rule(
        "Essential Pins",
        validate_essential_pins_connected,
        model,
        desc="All essential peripheral pins are connected",
    )

    # ========================================================================
    # Well-Formedness: Unique peripheral names
    # ========================================================================
    run_rule(
        "Unique Identifiers",
        validate_unique_peripheral_names,
        model,
        desc="All peripherals have unique names",
    )

    # ========================================================================
    # SmartConnect: Validate declarations
    # ========================================================================
    if hasattr(model, "smartConnections") and model.smartConnections:
        from demol.lang.semantics.validators.smart_connection import (
            validate_smart_connections,
        )

        run_rule(
            "SmartConnect Validation",
            validate_smart_connections,
            model,
            desc="SmartConnect declarations are valid",
        )

    # ========================================================================
    # Well-Formedness: Broker requirements
    # ========================================================================
    run_rule(
        "Broker Requirements",
        validate_broker_requirements,
        model,
        desc="Broker is configured",
    )

    # ========================================================================
    # Well-Formedness: Multi-broker uniqueness and VIA resolution
    # ========================================================================
    run_rule(
        "Multi-Broker Validation",
        validate_multi_broker,
        model,
        desc="Broker names are unique and VIA references resolve",
    )

    # ========================================================================
    # Well-Formedness: Network requirements (network is configured)
    # ========================================================================
    run_rule(
        "Network Requirements",
        validate_network_requirements,
        model,
        desc="Network is configured",
    )

    # ========================================================================
    # Safety: Broker security (authentication for remote brokers)
    # ========================================================================
    run_rule(
        "Broker Security",
        validate_broker_security,
        model,
        desc="Remote brokers have authentication configured",
    )

    # ========================================================================
    # Connection Validation
    # ========================================================================
    run_rule(
        "Connection Integrity",
        validate_connections,
        model,
        desc="All pin-to-pin connections are valid",
    )

    # ========================================================================
    # Well-Formedness: Common ground check
    # ========================================================================
    run_rule(
        "Common Ground",
        validate_common_ground,
        model,
        desc="Peripherals share a common ground with the board",
    )

    # ========================================================================
    # Safety: Power Paths
    # ========================================================================
    run_rule(
        "Power Paths",
        validate_power_paths,
        model,
        desc="All components have a path to a power source",
    )

    # ========================================================================
    # Global Safety Validations
    # ========================================================================

    # Safety: No pin conflicts (unique pins per connection)
    run_rule(
        "Pin Conflicts",
        validate_no_pin_conflicts,
        model,
        desc="No physical pin conflicts detected",
    )

    # Safety: I2C addresses must be unique on the same bus
    run_rule(
        "I2C Address Uniqueness",
        validate_i2c_address_uniqueness,
        model.connections,
        desc="I2C slave addresses are unique per bus",
    )

    # Safety: Voltage limits must not be exceeded
    run_rule(
        "Voltage Limits",
        validate_voltage_limits,
        model,
        desc="Peripheral voltage limits are respected",
    )

    # Safety: IO Voltage compatibility
    run_rule(
        "IO Voltage Compatibility",
        validate_io_voltage_compatibility,
        model,
        desc="Board and peripheral IO voltages match",
    )

    # ========================================================================
    # Safety: Power Budget Analysis
    # ========================================================================
    from demol.lang.semantics.validators.power_budget import validate_power_budget

    run_rule(
        "Power Budget",
        validate_power_budget,
        model,
        desc="Total peripheral power within board supply capability",
    )

    # ========================================================================
    # Warning: Pin Function Oversubscription
    # ========================================================================
    from demol.lang.semantics.validators.pin_oversubscription import (
        validate_pin_oversubscription,
    )

    run_rule(
        "Pin Oversubscription",
        validate_pin_oversubscription,
        model,
        desc="Multi-function pins not silently losing bus capabilities",
    )

    # ========================================================================
    # Sampling Configuration Validation
    # ========================================================================
    from demol.lang.semantics.validators.sampling import validate_sampling

    run_rule(
        "Sampling Config",
        validate_sampling,
        model,
        desc="SAMPLING blocks are well-formed (rate, mode, duplicates)",
    )

    # ========================================================================
    # User-Defined Constraints
    # ========================================================================
    from demol.lang.semantics.validators.user_constraints import (
        validate_user_constraints,
    )

    run_rule(
        "User Constraints",
        validate_user_constraints,
        model,
        desc="User-defined CONSTRAINT expressions are satisfied",
    )

    # ========================================================================
    # Protocol Frequency / Bus Speed Validation
    # ========================================================================
    from demol.lang.semantics.validators.protocol_frequency import (
        validate_protocol_frequency,
    )

    run_rule(
        "Protocol Frequency",
        validate_protocol_frequency,
        model,
        desc="I2C/SPI bus speeds are within standard limits",
    )

    # ========================================================================
    # Peripheral PROPERTIES Validation (must run before alert codegen)
    # ========================================================================
    from demol.lang.semantics.validators.peripheral_properties import (
        validate_peripheral_properties,
    )

    run_rule(
        "Peripheral Properties",
        validate_peripheral_properties,
        model,
        desc="PROPERTIES blocks on peripherals are well-formed",
    )

    # ========================================================================
    # Alert Trigger Validation
    # ========================================================================
    from demol.lang.semantics.validators.alert import validate_alerts

    run_rule(
        "Alert Triggers",
        validate_alerts,
        model,
        desc="ALERT triggers are well-formed (source, targets, VIA)",
    )

    # ========================================================================
    # Topic Format Validation (based on broker type)
    # ========================================================================
    run_rule(
        "Topic Format",
        validate_topic_format,
        model,
        desc="MQTT/AMQP topics follow protocol conventions",
    )

    # ========================================================================
    # Final Error Check: Stop if any errors were reported
    # ========================================================================
    skip_semantics = getattr(metamodel, "skip_semantics", False)
    check_validation_errors(model, skip_semantics=skip_semantics)

    errors = get_validation_errors()
    if not errors:
        logger.info("All validation checks passed!")
    else:
        logger.warning("Model built with %d semantic error(s) (skip_semantics=True)", len(errors))


def enrich_model(model):
    """
    Enrich the model with auto-generated values.
    Extracts board and peripherals from USE statements.
    Creates auth object from broker auth properties.
    """
    from types import SimpleNamespace

    # ========================================================================
    # Multiple Brokers: backward-compat 'model.broker' property
    # ========================================================================
    brokers = getattr(model, "brokers", [])
    # Provide backward-compatible 'model.broker' pointing to first broker
    if brokers:
        model.broker = brokers[0]
    else:
        model.broker = None

    # Build broker lookup by name for VIA resolution
    broker_map = {}
    for b in brokers:
        broker_map[b.name] = b
    model._broker_map = broker_map

    # ========================================================================
    # Process Broker Authentication (create auth object for ALL brokers)
    # ========================================================================
    for broker in brokers:
        auth_attrs = {}

        # Check for auth properties and collect them
        if hasattr(broker, "auth_username"):
            auth_attrs["username"] = broker.auth_username
        if hasattr(broker, "auth_password"):
            auth_attrs["password"] = broker.auth_password
        if hasattr(broker, "auth_key"):
            auth_attrs["key"] = broker.auth_key

        # Create auth object if there are auth properties
        if auth_attrs:
            auth_obj = SimpleNamespace(**auth_attrs)
            setattr(broker, "auth", auth_obj)

    # ========================================================================
    # Extract board and peripherals from USE statements
    # ========================================================================
    board = None
    peripherals = []
    power_sources = []

    for use in model.uses:
        if hasattr(use, "components") and use.components:
            for comp_inst in use.components:
                # Determine type based on the referenced component
                ref_class = comp_inst.ref.__class__.__name__
                if "Board" in ref_class:
                    if not board:
                        board = comp_inst.ref
                    if not comp_inst.name:
                        comp_inst.name = comp_inst.ref.name
                elif "PowerSource" in ref_class:
                    power_sources.append(comp_inst)
                else:  # Peripheral (Sensor or Actuator)
                    peripherals.append(comp_inst)

    # Create a synthetic 'components' object for backward compatibility
    model.components = SimpleNamespace(board=board, peripherals=peripherals, powerSources=power_sources)

    # ========================================================================
    # Resolve SmartConnect declarations into synthetic connections
    # ========================================================================
    if hasattr(model, "smartConnections") and model.smartConnections:
        from demol.lang.smart_connection import resolve_smart_connections

        resolve_smart_connections(model)

    device_name = model.metadata.name.strip('"')

    for c in model.connections:
        # Set the board for easy navigation in M2M and M2T transformations
        setattr(c, "board", board)

        def resolve_target(comp_inst):
            if not comp_inst:
                return None, "unknown", None
            # comp_inst is now a ComponentInstance (BoardDef, PeripheralDef, or PowerSourceDef)
            if hasattr(comp_inst, "ref"):
                return (
                    comp_inst.ref,
                    getattr(comp_inst, "name", comp_inst.ref.name),
                    comp_inst,
                )
            else:
                return comp_inst, getattr(comp_inst, "name", "unknown"), None

        from_ref, from_name, from_inst = resolve_target(c.from_comp)

        if hasattr(c, "to_comp") and c.to_comp:
            to_ref, to_name, to_inst = resolve_target(c.to_comp)
        else:
            # Default to board if to_comp is missing
            to_ref, to_name, to_inst = board, board.name if board else "board", None

        # Store resolved endpoints on the connection object
        setattr(c, "_from_ref", from_ref)
        setattr(c, "_from_name", from_name)
        setattr(c, "_from_inst", from_inst)
        setattr(c, "_to_ref", to_ref)
        setattr(c, "_to_name", to_name)
        setattr(c, "_to_inst", to_inst)

        # Backward compatibility: set 'peripheral' and 'target' attributes
        # We assume the 'from_comp' is the primary peripheral if it's not the board
        # Otherwise, we check 'to_comp'.
        primary_inst = from_inst if from_inst else to_inst
        if primary_inst:
            setattr(c, "peripheral", primary_inst)
            # 'target' attribute for backward compatibility with some older logic
            # that might expect c.target.target
            setattr(c, "target", SimpleNamespace(target=primary_inst))

        target_ref = from_ref if from_inst else to_ref
        target_name = from_name if from_inst else to_name

        # ====================================================================
        # Resolve VIA broker reference for this connection
        # ====================================================================
        via_name = getattr(c, "via", None)
        if via_name and via_name in model._broker_map:
            setattr(c, "_resolved_broker", model._broker_map[via_name])
        elif model.broker:
            setattr(c, "_resolved_broker", model.broker)
        else:
            setattr(c, "_resolved_broker", None)

        # ====================================================================
        # Auto-generate topic if not specified (if broker or network is present)
        # ====================================================================
        has_net = (model.broker is not None) or (hasattr(model, "network") and model.network)
        if has_net and not c.remote and target_ref and hasattr(target_ref, "type"):
            peripheral_type = type(target_ref).__name__
            peripheral_msg = target_ref.type

            default_topic = f'"{device_name}.{peripheral_type}.{peripheral_msg}.{target_name}"'
            c.remote = default_topic.lower().strip('""')


def get_device_mm(debug: bool = False, global_repo: bool = False, skip_semantics: bool = False):
    mm = metamodel_from_file(
        os.path.join(METAMODEL_REPO_PATH, "device.tx"),
        auto_init_attributes=True,
        global_repository=global_repo,
        textx_tools_support=True,
        debug=debug,
    )

    from textx import register_language, registration as textx_registration
    from demol.lang.component import get_component_mm

    component_mm = get_component_mm(skip_semantics=skip_semantics)

    # Register component language explicitly for .hwd files so that
    # FQNGlobalRepo uses the correct metamodel. The entry-point scan
    # that textX runs on first use can fail on malformed third-party
    # textx_languages entries, which previously caused the FQNGlobalRepo
    # to fall back to the device metamodel for .hwd files (producing
    # "Syntax Error ... => '*BOARD[ESP]'"). Pre-initializing the
    # languages dict bypasses that scan.
    if textx_registration.languages is None:
        textx_registration.languages = {}
    textx_registration.languages.pop("demol-component", None)
    register_language(
        "demol-component",
        pattern="*.hwd",
        description="DeMoL component language",
        metamodel=component_mm,
    )

    mm.register_scope_providers(
        {
            "*.*": scoping_providers.FQNImportURI(importAs=True),
            "ComponentInstance.ref": scoping_providers.FQNGlobalRepo(os.path.join(DEVICES_MODEL_REPO_PATH, "*/*.hwd")),
            "Connect.from_comp": "~uses.components",
            "Connect.to_comp": "~uses.components",
            "SmartConnect.target": "~uses.components",
            "SamplingConfig.target": "~uses.components",
            "AlertTrigger.source": "~uses.components",
            "AlertActivate.target": "~uses.components",
        }
    )

    # Register component metamodel for cross-metamodel scoping (+m:component)
    mm.referenced_languages["component"] = component_mm

    mm.register_model_processor(model_proc)
    mm._skip_semantics = skip_semantics

    mm.register_obj_processors(
        {
            # EMPTY
        }
    )

    mm.skip_semantics = skip_semantics

    return mm
