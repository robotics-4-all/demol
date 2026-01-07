import os, sys
from demol.definitions import *
from demol.lang import build_model
import jinja2
import codecs
import warnings

fsloader = jinja2.FileSystemLoader(SMAUTO_TEMPLATES)
env = jinja2.Environment(loader=fsloader)
broker_data = {}
device_name = ""
peripherals_data = []


def get_broker_info(device_model):
    #Device name to name the output file
    global device_name
    device_name = device_model.metadata.name
    #Gather Broker info
    broker_type = device_model.broker.__class__.__name__
    # keep only the type name, without the "Broker" suffix
    broker_data["broker_type"] = broker_type.replace("Broker", "")
    broker_data["broker_host"] = device_model.broker.host
    broker_data["broker_port"] = device_model.broker.port
    broker_data["broker_name"] = device_model.broker.name
    #Set username and password if plain auth is used, otherwise warn and set to None because SmAuto requires username and password
    if hasattr(device_model.broker, "auth") and str(device_model.broker.auth.__class__.__name__) == "AuthPlain":
        broker_data["broker_username"] = device_model.broker.auth.username
        broker_data["broker_password"] = device_model.broker.auth.password
    else:
        warnings.warn(
        "SmAuto currently supports only plain authentication for all brokers.",
        category=UserWarning
        )
        broker_data["broker_username"] = None
        broker_data["broker_password"] = None

    #Gather additional info for specific brokers
    if broker_data["broker_type"] == "AMQP" and hasattr(device_model.broker, "vhost"):
        broker_data["broker_vhost"] = device_model.broker.vhost
    if broker_data["broker_type"] == "AMQP" and hasattr(device_model.broker, "topicE"):
        broker_data["broker_topicExchange"] = device_model.broker.topicE

    if broker_data["broker_type"] == "Redis" and hasattr(device_model.broker, "db"):
        broker_data["broker_db"] = device_model.broker.db


def get_peripherals_info(device_model):
    global peripherals_data

    for i, conn in enumerate(device_model.connections):
        peripheral_data = {}
        per_frequency = 0
        
        # Skip if not a peripheral connection (e.g. board-to-powersource)
        if not hasattr(conn, 'peripheral') or not conn.peripheral:
            continue
            
        # Gather peripheral info
        per_dev_name = conn.peripheral.name
        per_real_name = conn.peripheral.ref.name
        per_type =  type(conn.peripheral.ref).__name__
        per_topic = conn.remote if conn.remote else f"device/{per_dev_name}"
        per_broker = broker_data["broker_name"]
        per_msg_type = conn.peripheral.ref.type
        peripheral_data = {"per_name": per_dev_name, "per_real_name": per_real_name, "per_type": per_type, "per_topic": per_topic, "per_broker": per_broker, "per_msg_type": per_msg_type}

        for attribute in conn.peripheral.ref.attributes:
            if attribute.name == "frequency":
                per_frequency = attribute.default
                peripheral_data = peripheral_data | {"per_frequency": per_frequency}
 
        # Create a dictionary for each peripheral and append it to the list
        peripherals_data.append(peripheral_data)


#Generate SmAuto model
def demol2smauto(model, output_dir='.'):
    get_broker_info(model)
    get_peripherals_info(model)
    
    if output_dir != '.' and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    template = env.get_template("BrokerAndEntity.j2")
    rt = template.render(**broker_data, peripherals=peripherals_data)
    filepath = os.path.join(output_dir, f"{device_name}SmAutoModel.auto")
    ofh = codecs.open(filepath, "w", encoding="utf-8")
    ofh.write(rt)
    ofh.close()


def main(dev_model, output_dir):
    rpi5_device_path = os.path.join(REPO_PATH, "examples", dev_model)
    rpi5_device = build_model(rpi5_device_path)

    output = os.path.join(REPO_PATH, output_dir)

    print("Collecting broker info...")
    get_broker_info(rpi5_device) 
    print("Collecting peripherals info...")
    get_peripherals_info(rpi5_device)
    print(peripherals_data)
    print("Generating SmAuto model...")
    demol2smauto(output_dir = output)

if __name__ == "__main__":
    main("ThesisExamples\\ThesisExample.dev", "rpi5_out\\ThesisExample")