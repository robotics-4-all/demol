import os
from textx import metamodel_from_file
import textx.scoping.providers as scoping_providers
from textx import get_location, TextXSemanticError
from demol.definitions import *

from demol.mm_classes import (
    Metadata, Network, BrokerAuthPlain, AMQPBroker, MQTTBroker, RedisBroker,
)

CUSTOM_CLASSES = [
    Metadata, Network, BrokerAuthPlain, AMQPBroker, MQTTBroker, RedisBroker,
]


def class_provider(name):
    classes = dict(map(lambda x: (x.__name__, x), CUSTOM_CLASSES))
    return classes.get(name)


def raise_validation_error(obj, msg):
    raise TextXSemanticError(
        f'[Validation Error]: {msg}',
        **get_location(obj)
    )


def get_device_mm(debug=False):
    mm = metamodel_from_file(
        os.path.join(METAMODEL_REPO_PATH, 'device.tx'),
        classes=class_provider,
        auto_init_attributes=True,
        global_repository=True,
        debug=debug
    )

    mm.register_scope_providers(
        {
            # "*.*": scoping_providers.FQNImportURI(
            #     importAs=True,
            # ),
            "*.*": scoping_providers.FQN(),
            "Connection.board": scoping_providers.FQNGlobalRepo(
                os.path.join(BOARD_MODEL_REPO_PATH, '*.hwd')
            ),
            "Connection.peripheral": scoping_providers.FQNGlobalRepo(
                os.path.join(PERIPHERAL_MODEL_REPO_PATH, '*.hwd')
            ),
            # 'Connection.board': 'devices.board'
            # "Connection.board": scoping_providers.PlainName(
            #     "devices.board"
            # ),
        }
    )

    def model_proc(model, metamodel):
        for c in model.connections:
            board_pins = [p.name for p in c.board.pins]
            per_pins = [p.name for p in c.peripheral.pins]
            # if c.peripheral not in model.components.peripherals:
            #     raise TextXSemanticError(
            #         f'Peripheral {c.peripheral.name} not defined in Bag of components!'
            #     )
            # if c.board != model.components.board:
            #     raise TextXSemanticError(
            #         f'Board {c.board.name} not defined in Bag of components!'
            #     )
            for pconn in c.powerConns:
                print(
                    f'PowerPinConnection:\n'
                    f'  {pconn.boardPin} -> {pconn.peripheralPin}'
                )
                if pconn.boardPin not in board_pins:
                    raise TextXSemanticError(
                        f'Board {c.board.name} does not have a pin '
                        'named {pconn.boardPin}'
                    )
                if pconn.peripheralPin not in per_pins:
                    raise TextXSemanticError(
                        f'Peripheral {c.peripheral.name} does not have a '
                        'pin named {pconn.peripheralPin}'
                    )

            for ioconn in c.ioConns:
                if ioconn.__class__.__name__ == 'GPIOConnection':
                    pin_conn = ioconn.pinConn
                    print(
                        f'GPIO-Connection:\n'
                        f'  {pin_conn.boardPin} -> {pin_conn.peripheralPin}'
                    )
                    if pin_conn.boardPin not in board_pins:
                        raise_validation_error(
                            pin_conn,
                            f'Board {c.board.name} does not have a pin '
                            f'named {pin_conn.boardPin}'
                        )
                    if pin_conn.peripheralPin not in per_pins:
                        raise_validation_error(
                            pin_conn,
                            f'Peripheral {c.peripheral.name} does not have a '
                            f'pin named {pin_conn.peripheralPin}'
                        )
                elif ioconn.__class__.__name__ == 'SPIConnection':
                    miso = ioconn.miso
                    mosi = ioconn.mosi
                    sck = ioconn.sck
                    cs = ioconn.cs
                    print(
                        f'SPI-Connection: \n'
                        f'  {miso.boardPin} -> {miso.peripheralPin}\n'
                        f'  {mosi.boardPin} -> {mosi.peripheralPin}\n'
                        f'  {sck.boardPin} -> {sck.peripheralPin}\n'
                        f'  {cs.boardPin} -> {cs.peripheralPin}'
                    )
                    pin_conns = [miso, mosi, sck, cs]
                    for pc in pin_conns:
                        if pc.boardPin not in board_pins:
                            raise_validation_error(
                                pc,
                                f'Board {c.board.name} does not have a pin '
                                f'named {pc.boardPin}',
                            )
                        if pc.peripheralPin not in per_pins:
                            raise_validation_error(
                                pc,
                                f'Peripheral {c.peripheral.name} does not have a '
                                f'pin named {pc.peripheralPin}'
                            )
                elif ioconn.__class__.__name__ == 'I2CConnection':
                    sda = ioconn.sda
                    scl = ioconn.scl
                    print(
                        f'I2C-Connection:\n'
                        f'  SDA: {sda.boardPin} -> {sda.peripheralPin}\n'
                        f'  SCL: {scl.boardPin} -> {scl.peripheralPin}'
                    )
                    pin_conns = [sda, scl]
                    for pc in pin_conns:
                        if pc.boardPin not in board_pins:
                            raise_validation_error(
                                pc,
                                f'Board {c.board.name} does not have a pin '
                                f'named {pc.boardPin}',
                            )
                        if pc.peripheralPin not in per_pins:
                            raise_validation_error(
                                pc,
                                f'Peripheral {c.peripheral.name} does not have a '
                                f'pin named {pc.peripheralPin}'
                            )

    mm.register_model_processor(model_proc)

    mm.register_obj_processors({
        # EMPTY
    })

    return mm
