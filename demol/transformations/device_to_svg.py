import jinja2
from pathlib import Path
from .base_generator import BaseCodeGenerator
from demol.definitions import TEMPLATES_DOCS
from demol.lang.semantics import get_connection_endpoints


class SvgGenerator(BaseCodeGenerator):
    """
    Generates a professional SVG diagram from a device model.
    Shows interconnection between board and peripherals at PIN level.
    Layout: Schematic style with Board in center, Peripherals on Left/Right.
    """

    OS = ""

    # --- Configuration ---
    # Colors
    COLOR_BG = "#FFFFFF"
    COLOR_BOARD_FILL = "#0F172A"  # Slate 900
    COLOR_BOARD_STROKE = "#1E293B"  # Slate 800
    COLOR_BOARD_TEXT = "#F8FAFC"  # Slate 50

    COLOR_PERIPH_FILL = "#F1F5F9"  # Slate 100
    COLOR_PERIPH_STROKE = "#CBD5E1"  # Slate 300
    COLOR_PERIPH_TEXT = "#0F172A"  # Slate 900

    COLOR_PIN_TEXT = "#64748B"  # Slate 500
    COLOR_PIN_MARKER = "#94A3B8"  # Slate 400

    COLOR_LINE_DEFAULT = "#3B82F6"  # Blue 500
    COLOR_LINE_POWER = "#EF4444"  # Red 500
    COLOR_LINE_GND = "#1E293B"  # Slate 800

    # Dimensions
    PIN_SPACING = 25
    PIN_MARGIN_TOP = 40
    PIN_MARGIN_BOTTOM = 20

    PERIPH_WIDTH = 180
    BOARD_WIDTH = 300

    GAP_BOARD_PERIPH = 200  # Space for wires
    MARGIN_X = 50
    MARGIN_Y = 50

    # Font Sizes
    FONT_TITLE = 24
    FONT_COMP_TITLE = 16
    FONT_PIN = 12

    def __init__(self, device_model, output_file=None):
        if not output_file:
            output_file = f"{device_model.metadata.name}.svg"
        self.output_file = Path(output_file)
        super().__init__(device_model, self.output_file.parent)
        self.env = self.setup_template_environment()

    def setup_template_environment(self):
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(TEMPLATES_DOCS), autoescape=jinja2.select_autoescape(["html", "xml", "j2"])
        )

    def generate(self) -> None:
        """
        Main generation method.
        """
        model = self.device_model
        connections = self.get_connections()

        if not connections:
            print("No connections found.")
            return

        # Group connections into Left and Right sets to balance the diagram
        left_peripherals = []
        right_peripherals = []

        for i, conn in enumerate(connections):
            # Extract all pins for this connection
            pin_pairs = []  # list of (board_pin, periph_pin, type)

            # Data Connections
            if hasattr(conn, "dataConns"):
                for dc in conn.dataConns:
                    for pin in dc.pins:
                        pin_pairs.append({"board": str(pin.fromPin), "periph": str(pin.toPin), "type": "data"})

            # Power Connections
            if hasattr(conn, "powerConns"):
                # Determine direction using horizontal logic
                from_ref, from_name, to_ref, to_name = get_connection_endpoints(conn)

                # We need to know which side is the board
                # If from_comp is board, then fromPin is board pin
                # If to_comp is board, then toPin is board pin

                board_is_source = False
                if self.device_model.components.board:
                    board_name = self.device_model.components.board.name
                    if from_name == board_name:
                        board_is_source = True

                for pc in conn.powerConns:
                    p_type = "power"

                    if board_is_source:
                        board_pin = str(pc.fromPin)
                        periph_pin = str(pc.toPin)
                    else:
                        board_pin = str(pc.toPin)
                        periph_pin = str(pc.fromPin)

                    if "gnd" in board_pin.lower() or "gnd" in periph_pin.lower():
                        p_type = "gnd"

                    pin_pairs.append({"board": board_pin, "periph": periph_pin, "type": p_type})

            periph_data = {
                "name": conn.peripheral.name,
                "type": conn.peripheral.ref.type if hasattr(conn.peripheral.ref, "type") else "Peripheral",
                "pins": pin_pairs,
                "height": self.PIN_MARGIN_TOP + len(pin_pairs) * self.PIN_SPACING + self.PIN_MARGIN_BOTTOM,
            }

            if i % 2 == 0:
                right_peripherals.append(periph_data)
            else:
                left_peripherals.append(periph_data)

        # --- Layout Calculation ---
        height_left = self._get_total_stack_height(left_peripherals)
        height_right = self._get_total_stack_height(right_peripherals)

        pins_on_left_edge = sum(len(p["pins"]) for p in left_peripherals)
        pins_on_right_edge = sum(len(p["pins"]) for p in right_peripherals)

        max_pins_side = max(pins_on_left_edge, pins_on_right_edge)
        min_board_height = self.PIN_MARGIN_TOP + max_pins_side * self.PIN_SPACING + self.PIN_MARGIN_BOTTOM

        total_content_height = max(height_left, height_right, min_board_height)

        canvas_height = total_content_height + 2 * self.MARGIN_Y
        canvas_width = (
            self.MARGIN_X
            + self.PERIPH_WIDTH
            + self.GAP_BOARD_PERIPH
            + self.BOARD_WIDTH
            + self.GAP_BOARD_PERIPH
            + self.PERIPH_WIDTH
            + self.MARGIN_X
        )

        center_y = canvas_height / 2

        board_x = self.MARGIN_X + self.PERIPH_WIDTH + self.GAP_BOARD_PERIPH
        board_h = max(min_board_height, total_content_height * 0.6)
        board_y = center_y - board_h / 2

        # Prepare data for template
        template_data = {
            "canvas": {"width": canvas_width, "height": canvas_height, "title": model.metadata.name},
            "colors": {
                "bg": self.COLOR_BG,
                "board_fill": self.COLOR_BOARD_FILL,
                "board_stroke": self.COLOR_BOARD_STROKE,
                "board_text": self.COLOR_BOARD_TEXT,
                "periph_fill": self.COLOR_PERIPH_FILL,
                "periph_stroke": self.COLOR_PERIPH_STROKE,
                "periph_text": self.COLOR_PERIPH_TEXT,
                "pin_text": self.COLOR_PIN_TEXT,
                "pin_marker": self.COLOR_PIN_MARKER,
                "line_default": self.COLOR_LINE_DEFAULT,
                "line_power": self.COLOR_LINE_POWER,
                "line_gnd": self.COLOR_LINE_GND,
            },
            "fonts": {"title": self.FONT_TITLE, "comp_title": self.FONT_COMP_TITLE, "pin": self.FONT_PIN},
            "board": {"x": board_x, "y": board_y, "w": self.BOARD_WIDTH, "h": board_h, "name": self.get_board().name},
            "peripherals": [],
        }

        # Process stacks
        self._process_stack(template_data, left_peripherals, True, center_y, canvas_width)
        self._process_stack(template_data, right_peripherals, False, center_y, canvas_width)

        # Render Template
        try:
            template = self.env.get_template("device.svg.j2")
            self._write_template(template, template_data, self.output_file)
            print(f"Successfully generated SVG: {self.output_file}")
        except Exception as e:
            print(f"Error generating SVG: {e}")

    def _get_total_stack_height(self, periph_list):
        h = 0
        for p in periph_list:
            h += p["height"] + 30
        return h

    def _process_stack(self, template_data, periphs, is_left_side, center_y, canvas_width):
        stack_h = self._get_total_stack_height(periphs)
        start_y = center_y - stack_h / 2
        current_y = start_y

        board_rect = template_data["board"]
        total_pins = sum(len(p["pins"]) for p in periphs)
        board_edge_x = board_rect["x"] if is_left_side else board_rect["x"] + board_rect["w"]

        req_h = total_pins * self.PIN_SPACING
        pin_start_y = board_rect["y"] + (board_rect["h"] - req_h) / 2 + self.PIN_SPACING / 2

        global_pin_idx = 0

        for p in periphs:
            p_x = self.MARGIN_X if is_left_side else canvas_width - self.MARGIN_X - self.PERIPH_WIDTH
            p_y = current_y
            p_w = self.PERIPH_WIDTH
            p_h = p["height"]

            periph_pin_x = p_x + p_w if is_left_side else p_x
            periph_text_anchor = "end" if is_left_side else "start"
            periph_text_x = periph_pin_x - 10 if is_left_side else periph_pin_x + 10

            board_text_anchor = "start" if is_left_side else "end"
            board_text_x = board_edge_x + 10 if is_left_side else board_edge_x - 10

            processed_pins = []
            for i, pin in enumerate(p["pins"]):
                pp_y = p_y + self.PIN_MARGIN_TOP + i * self.PIN_SPACING
                bp_y = pin_start_y + global_pin_idx * self.PIN_SPACING
                global_pin_idx += 1

                line_color = self.COLOR_LINE_DEFAULT
                if pin["type"] == "power":
                    line_color = self.COLOR_LINE_POWER
                elif pin["type"] == "gnd":
                    line_color = self.COLOR_LINE_GND

                # Bezier control points
                dist = abs(periph_pin_x - board_edge_x) * 0.5
                cp1x = board_edge_x + dist if periph_pin_x > board_edge_x else board_edge_x - dist
                cp2x = periph_pin_x - dist if periph_pin_x > board_edge_x else periph_pin_x + dist

                processed_pins.append(
                    {
                        "board": pin["board"],
                        "periph": pin["periph"],
                        "bp_y": bp_y,
                        "pp_y": pp_y,
                        "color": line_color,
                        "cp1x": cp1x,
                        "cp2x": cp2x,
                    }
                )

            template_data["peripherals"].append(
                {
                    "name": p["name"],
                    "x": p_x,
                    "y": p_y,
                    "w": p_w,
                    "h": p_h,
                    "pin_x": periph_pin_x,
                    "text_x": periph_text_x,
                    "text_anchor": periph_text_anchor,
                    "pins": processed_pins,
                    "board_edge_x": board_edge_x,
                    "board_text_x": board_text_x,
                    "board_text_anchor": board_text_anchor,
                }
            )

            current_y += p_h + 30


def device_to_svg(model, output_file=None):
    """
    Entry point for the SVG transformation.
    """
    generator = SvgGenerator(model, output_file)
    generator.generate()
