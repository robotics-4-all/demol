from typing import Any, Dict


def to_plain_value(val):
    """Convert textX values to plain Python types"""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if hasattr(val, "items"):  # ListValue
        return [to_plain_value(i) for i in val.items]
    if hasattr(val, "__dict__"):
        # For other textX objects, we might need more complex logic
        # but for now let's try to return the string representation if it's a simple type
        return str(val)
    return str(val)


def parse_pins(pins):
    result = []
    for p in pins:
        class_name = p.__class__.__name__.lower()
        pin_data = {
            "name": p.name,
            "number": p.number,
            "status": "optional"
            if getattr(p, "optional", None) == "?"
            else "essential",
            "type": "power" if "power" in class_name else "io",
        }

        if pin_data["type"] == "power":
            pin_data["type"] = to_plain_value(getattr(p, "ptype", "power"))
        else:
            pin_data["functions"] = []
            funcs = getattr(p, "funcs", [])
            for f in funcs:
                if hasattr(f, "ptype"):
                    pin_data["functions"].append(to_plain_value(f.ptype))

        result.append(pin_data)
    return result


def board_to_json(comp) -> Dict[str, Any]:
    # Extract operational specs
    op: Dict[str, Any] = {"vcc": "5V", "cpu": {}, "memory": {}}  # Default

    if hasattr(comp, "operational"):
        if hasattr(comp.operational, "vcc"):
            op["vcc"] = to_plain_value(comp.operational.vcc)
        if hasattr(comp.operational, "cpu_family"):
            op["cpu"]["family"] = to_plain_value(comp.operational.cpu_family)
        if hasattr(comp.operational, "memory_ram"):
            op["memory"]["ram"] = (
                f"{comp.operational.memory_ram} {comp.operational.memory_ram_unit}"
            )

    return {
        "name": comp.name,
        "type": comp.type,
        "pins": parse_pins(comp.pins),
        "operational": op,
    }


def peripheral_to_json(comp) -> Dict[str, Any]:
    class_name = comp.__class__.__name__
    category = "sensor" if "sensor" in class_name.lower() else "actuator"

    # Extract operational specs
    op: Dict[str, Any] = {"vcc": "5V", "power": {}}  # Default

    if hasattr(comp, "operational"):
        if hasattr(comp.operational, "vcc"):
            op["vcc"] = to_plain_value(comp.operational.vcc)
        if hasattr(comp.operational, "min"):
            op["power"]["min"] = (
                f"{comp.operational.min.value} {comp.operational.min.unit}"
            )
        if hasattr(comp.operational, "max"):
            op["power"]["max"] = (
                f"{comp.operational.max.value} {comp.operational.max.unit}"
            )

    # Extract attributes
    attrs = {}
    if hasattr(comp, "attributes"):
        for attr in comp.attributes:
            attr_data = {
                "type": to_plain_value(attr.type),
                "default": to_plain_value(getattr(attr, "default", None)),
            }
            attrs[attr.name] = attr_data

    return {
        "name": comp.name,
        "type": comp.type,
        "category": category,
        "pins": parse_pins(comp.pins),
        "operational": op,
        "attributes": attrs,
    }


def powersource_to_json(comp) -> Dict[str, Any]:
    # Extract operational specs
    op = {
        "voltage": "5V",  # Default
    }

    if hasattr(comp, "operational"):
        if hasattr(comp.operational, "voltage"):
            op["voltage"] = to_plain_value(comp.operational.voltage)
        if hasattr(comp.operational, "capacity"):
            op["capacity"] = (
                f"{comp.operational.capacity} {comp.operational.capacity_unit}"
            )
        if hasattr(comp.operational, "max_current"):
            op["max_current"] = (
                f"{comp.operational.max_current} {comp.operational.max_current_unit}"
            )

    return {
        "name": comp.name,
        "type": comp.type,
        "pins": parse_pins(comp.pins),
        "operational": op,
    }


def device_to_json(model) -> Dict[str, Any]:
    res = {
        "name": model.metadata.name,
        "description": model.metadata.description,
        "author": model.metadata.author,
        "os": model.metadata.os,
        "board": None,
        "peripherals": [],
        "powerSources": [],
        "connections": [],
        "network": None,
        "broker": None,
    }

    # Map to store instances
    instances = {}

    # Find board, peripherals, and power sources in uses
    for use in model.uses:
        if hasattr(use, "board") and use.board:
            boards = use.board if isinstance(use.board, list) else [use.board]
            for b in boards:
                res["board"] = board_to_json(b)
                res["board"]["id"] = f"{b.name}.hwd"
                instances[b.name] = res["board"]

        if hasattr(use, "components") and use.components:
            for comp_def in use.components:
                ref_type = comp_def.ref.__class__.__name__.lower()
                if "powersource" in ref_type:
                    ps_json = powersource_to_json(comp_def.ref)
                    ps_json["instanceName"] = comp_def.name
                    ps_json["id"] = f"{comp_def.ref.name}.hwd"
                    res["powerSources"].append(ps_json)
                    instances[comp_def.name] = ps_json
                else:
                    p_json = peripheral_to_json(comp_def.ref)
                    p_json["instanceName"] = comp_def.name
                    p_json["id"] = f"{comp_def.ref.name}.hwd"
                    res["peripherals"].append(p_json)
                    instances[comp_def.name] = p_json

    # Connections
    for conn in model.connections:
        c_data: Dict[str, Any] = {
            "fromName": getattr(conn, "_from_name", "unknown"),
            "toName": getattr(conn, "_to_name", "unknown"),
            "type": "io",
            "mappings": [],
        }

        if conn.powerConns:
            for pc in conn.powerConns:
                c_data["mappings"].append(
                    {"section": "power", "fromPin": pc.fromPin, "toPin": pc.toPin}
                )

        if conn.dataConns:
            # Take the first data connection type
            for dc in conn.dataConns:
                c_data["type"] = dc.type
                for pin in dc.pins:
                    if hasattr(pin, "function"):  # PinMapping (I2C, SPI, UART)
                        c_data["mappings"].append(
                            {
                                "section": "data",
                                "function": pin.function,
                                "fromPin": pin.fromPin,
                                "toPin": pin.toPin,
                            }
                        )
                    else:  # PinConnection (GPIO)
                        c_data["mappings"].append(
                            {
                                "section": "data",
                                "fromPin": pin.fromPin,
                                "toPin": pin.toPin,
                            }
                        )
                if hasattr(dc, "props") and dc.props:
                    c_data["props"] = {}
                    for prop in dc.props:
                        c_data["props"][prop.name] = prop.value

                break  # Only one data connection type per block in this simplified JSON

        res["connections"].append(c_data)

    # Network
    if hasattr(model, "network") and model.network:
        net = model.network
        res["network"] = {
            "type": net.__class__.__name__.replace("Network", ""),
            "ssid": getattr(net, "ssid", None),
            "password": getattr(net, "passwd", None),
            "address": getattr(net, "address", None),
            "channel": getattr(net, "channel", None),
        }

    # Broker
    if hasattr(model, "broker") and model.broker:
        br = model.broker
        res["broker"] = {
            "type": br.__class__.__name__.replace("Broker", ""),
            "name": br.name,
            "host": br.host,
            "port": br.port,
            "vhost": getattr(br, "vhost", None),
            "topicExchange": getattr(br, "topicE", None),
            "rpcExchange": getattr(br, "rpcE", None),
            "ssl": getattr(br, "ssl", False),
            "basePath": getattr(br, "basePath", None),
            "webPath": getattr(br, "webPath", None),
            "webPort": getattr(br, "webPort", None),
            "db": getattr(br, "db", None),
            "username": getattr(br, "auth_username", None),
            "password": getattr(br, "auth_password", None),
            "key": getattr(br, "auth_key", None),
        }

    return res


def demol_to_json(model) -> Dict[str, Any]:
    """Convert DeMoL model (textX) to JSON-serializable dictionary"""
    class_name = model.__class__.__name__
    if class_name == "DeviceModel":
        return device_to_json(model)
    elif class_name == "ComponentModel":
        comp = model.component
        comp_type = comp.__class__.__name__.lower()
        if comp_type == "board":
            return board_to_json(comp)
        elif comp_type == "powersource":
            return powersource_to_json(comp)
        else:
            return peripheral_to_json(comp)
    return {}


def json_to_demol(model_data) -> str:
    """Convert JSON model data to DeMoL DSL string"""

    def get_val(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    device_data = get_val(model_data, "device", model_data)
    name = get_val(device_data, "name", "Unnamed_Device").replace(" ", "_")
    description = get_val(device_data, "description", "")
    author = get_val(device_data, "author", "")
    os_name = get_val(device_data, "os", "riot")

    # 1. Device Definition
    content = f"DEVICE {name} WITH\n"
    content += f'    description="{description}",\n'
    content += f'    author="{author}",\n'
    content += f"    os={os_name}\n"
    content += ";\n\n"

    # 3. Uses
    board = get_val(model_data, "board")
    board_name = None
    if board:
        board_name = get_val(board, "name", "").replace(" ", "_")
        content += f"USE {board_name};\n"

    peripherals = get_val(model_data, "peripherals", [])
    power_sources = get_val(model_data, "powerSources", [])

    instance_map = {}

    if peripherals or power_sources:
        content += "USE "
        use_defs = []

        for p in peripherals:
            p_name = get_val(p, "name", "").replace(" ", "_")
            p_inst_name = (
                get_val(p, "instanceName") or get_val(p, "name", "")
            ).replace(" ", "_")
            p_def = f"{p_name} [{p_inst_name}]"

            attrs = get_val(p, "attributes", {})
            if attrs:
                attr_strings = []
                for k, v in attrs.items():
                    val = get_val(v, "default")
                    if val is not None:
                        if isinstance(val, str):
                            attr_strings.append(f'{k}="{val}"')
                        else:
                            attr_strings.append(f"{k}={val}")
                if attr_strings:
                    p_def += f" WITH {', '.join(attr_strings)}"

            use_defs.append(p_def)

            node_id = get_val(p, "nodeId")
            if node_id:
                instance_map[node_id] = p_inst_name

        for ps in power_sources:
            ps_name = get_val(ps, "name", "").replace(" ", "_")
            ps_inst_name = (
                get_val(ps, "instanceName") or get_val(ps, "name", "")
            ).replace(" ", "_")
            use_defs.append(f"{ps_name} [{ps_inst_name}]")

            node_id = get_val(ps, "nodeId")
            if node_id:
                instance_map[node_id] = ps_inst_name

        content += ", ".join(use_defs)
        content += ";\n\n"

    # 3. Network
    network = get_val(model_data, "network")
    if network:
        net_type = get_val(network, "type", "WiFi")
        content += f"NETWORK [{net_type}] WITH "
        net_attrs = []
        if net_type == "WiFi":
            if get_val(network, "ssid"):
                net_attrs.append(f'ssid="{get_val(network, "ssid")}"')
            if get_val(network, "password"):
                net_attrs.append(f'password="{get_val(network, "password")}"')
            if get_val(network, "channel"):
                net_attrs.append(f'channel="{get_val(network, "channel")}"')

        if get_val(network, "address"):
            net_attrs.append(f'address="{get_val(network, "address")}"')

        content += ", ".join(net_attrs)
        content += ";\n\n"

    # 4. Broker
    broker = get_val(model_data, "broker")
    if broker:
        br_type = get_val(broker, "type", "MQTT")
        br_name = get_val(broker, "name", "my_broker")
        content += f"BROKER [{br_type}] {br_name} WITH "
        br_attrs = []
        br_attrs.append(f'host="{get_val(broker, "host", "localhost")}"')
        br_attrs.append(f"port={get_val(broker, 'port', 1883)}")

        if br_type == "AMQP":
            if get_val(broker, "vhost"):
                br_attrs.append(f'vhost="{get_val(broker, "vhost")}"')
            if get_val(broker, "topicExchange"):
                br_attrs.append(f'topicExchange="{get_val(broker, "topicExchange")}"')
            if get_val(broker, "rpcExchange"):
                br_attrs.append(f'rpcExchange="{get_val(broker, "rpcExchange")}"')
        elif br_type == "MQTT":
            if get_val(broker, "basePath"):
                br_attrs.append(f'basePath="{get_val(broker, "basePath")}"')
            if get_val(broker, "webPath"):
                br_attrs.append(f'webPath="{get_val(broker, "webPath")}"')
            if get_val(broker, "webPort"):
                br_attrs.append(f"webPort={get_val(broker, 'webPort')}")
        elif br_type == "Redis":
            if get_val(broker, "db"):
                br_attrs.append(f"db={get_val(broker, 'db')}")

        if get_val(broker, "ssl"):
            br_attrs.append("ssl=true")
        if get_val(broker, "username"):
            br_attrs.append(f'auth.username="{get_val(broker, "username")}"')
        if get_val(broker, "password"):
            br_attrs.append(f'auth.password="{get_val(broker, "password")}"')
        if get_val(broker, "key"):
            br_attrs.append(f'auth.key="{get_val(broker, "key")}"')

        content += ", ".join(br_attrs)
        content += ";\n\n"

    # 4. Connections
    connections = get_val(model_data, "connections", [])

    # Group by (fromName, toName)
    grouped_connections: dict = {}
    for conn in connections:
        from_name = get_val(conn, "fromName", "unknown").replace(" ", "_")
        to_name = get_val(conn, "toName", "unknown").replace(" ", "_")
        key = (from_name, to_name)

        if key not in grouped_connections:
            grouped_connections[key] = []

        grouped_connections[key].append(conn)

    for key, conns in grouped_connections.items():
        from_name = key[0]
        to_name = key[1]

        if to_name == board_name or to_name == "board":
            content += f"CONNECT {from_name} WITH\n"
        else:
            content += f"CONNECT {from_name} : {to_name} WITH\n"

        # Aggregate Power Mappings
        all_power_mappings = []

        # Collect Data Connections strings
        data_conn_strings = []

        for conn in conns:
            c_type = get_val(conn, "type", "io")
            mappings = get_val(conn, "mappings", [])
            props = get_val(conn, "props", {})

            # Infer sections
            current_power = []
            current_data = []

            for m in mappings:
                section = get_val(m, "section")
                if not section:
                    if c_type == "power":
                        section = "power"
                    else:
                        section = "data"

                if section == "power":
                    current_power.append(m)
                else:
                    current_data.append(m)

            all_power_mappings.extend(current_power)

            if current_data:
                # Generate DataConnection string for this group
                actual_type = c_type
                if actual_type == "io":
                    actual_type = "gpio"

                if actual_type == "gpio":
                    for m in current_data:
                        from_pin = get_val(m, "fromPin")
                        to_pin = get_val(m, "toPin")
                        dc_str = "gpio "
                        if props:
                            prop_strings = []
                            for k, v in props.items():
                                if isinstance(v, str):
                                    prop_strings.append(f'{k}="{v}"')
                                else:
                                    prop_strings.append(f"{k}={v}")
                            dc_str += f"[{', '.join(prop_strings)}] "
                        dc_str += f"{from_pin} -- {to_pin}"
                        data_conn_strings.append(dc_str)
                else:
                    dc_str = f"{actual_type} "

                    if props:
                        prop_strings = []
                        for k, v in props.items():
                            if isinstance(v, str):
                                prop_strings.append(f'{k}="{v}"')
                            else:
                                prop_strings.append(f"{k}={v}")
                        dc_str += f"[{', '.join(prop_strings)}] "

                    m_strings = []
                    for m in current_data:
                        func = get_val(m, "function")
                        from_pin = get_val(m, "fromPin")
                        to_pin = get_val(m, "toPin")
                        if func:
                            m_strings.append(f"{func} {from_pin} -- {to_pin}")
                        else:
                            m_strings.append(f"{from_pin} -- {to_pin}")

                    dc_str += ", ".join(m_strings)
                    data_conn_strings.append(dc_str)

        if all_power_mappings:
            content += "    POWER "
            m_strings = []
            for m in all_power_mappings:
                m_strings.append(f"{get_val(m, 'fromPin')} -- {get_val(m, 'toPin')}")
            content += ", ".join(m_strings) + "\n"

        if data_conn_strings:
            content += "    DATA " + ", ".join(data_conn_strings) + "\n"

        content += ";\n\n"

    return content
