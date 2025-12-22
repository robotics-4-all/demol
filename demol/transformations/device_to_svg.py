import math
from pathlib import Path
from .base_generator import BaseCodeGenerator

class SvgGenerator(BaseCodeGenerator):
    """
    Generates a professional SVG diagram from a device model.
    Shows interconnection between board and peripherals at PIN level.
    Layout: Schematic style with Board in center, Peripherals on Left/Right.
    """
    
    # --- Configuration ---
    # Colors
    COLOR_BG = "#FFFFFF"
    COLOR_BOARD_FILL = "#0F172A"   # Slate 900
    COLOR_BOARD_STROKE = "#1E293B" # Slate 800
    COLOR_BOARD_TEXT = "#F8FAFC"   # Slate 50
    
    COLOR_PERIPH_FILL = "#F1F5F9"  # Slate 100
    COLOR_PERIPH_STROKE = "#CBD5E1" # Slate 300
    COLOR_PERIPH_TEXT = "#0F172A"   # Slate 900
    
    COLOR_PIN_TEXT = "#64748B"     # Slate 500
    COLOR_PIN_MARKER = "#94A3B8"   # Slate 400
    
    COLOR_LINE_DEFAULT = "#3B82F6" # Blue 500
    COLOR_LINE_POWER = "#EF4444"   # Red 500
    COLOR_LINE_GND = "#1E293B"     # Slate 800
    
    # Dimensions
    PIN_SPACING = 25
    PIN_MARGIN_TOP = 40
    PIN_MARGIN_BOTTOM = 20
    
    PERIPH_WIDTH = 180
    BOARD_WIDTH = 300
    
    GAP_BOARD_PERIPH = 200 # Space for wires
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
        # BaseCodeGenerator creates the directory in __init__
        super().__init__(device_model, self.output_file.parent)

    def setup_template_environment(self):
        """Not using Jinja2 for SVG generation currently."""
        return None

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
            pin_pairs = [] # list of (board_pin, periph_pin, type)
            
            # Data Connections
            if hasattr(conn, 'dataConns'):
                for dc in conn.dataConns:
                    for pin in dc.pins:
                        pin_pairs.append({
                            'board': str(pin.boardPin),
                            'periph': str(pin.peripheralPin),
                            'type': 'data'
                        })
            
            # Power Connections
            if hasattr(conn, 'powerConns'):
                for pc in conn.powerConns:
                    p_type = 'power'
                    b_pin_lower = str(pc.boardPin).lower()
                    if 'gnd' in b_pin_lower:
                        p_type = 'gnd'
                    pin_pairs.append({
                        'board': str(pc.boardPin),
                        'periph': str(pc.peripheralPin),
                        'type': p_type
                    })

            periph_data = {
                'name': conn.peripheral.name,
                'type': conn.peripheral.ref.type if hasattr(conn.peripheral.ref, 'type') else 'Peripheral',
                'pins': pin_pairs,
                'height': self.PIN_MARGIN_TOP + len(pin_pairs) * self.PIN_SPACING + self.PIN_MARGIN_BOTTOM
            }
            
            if i % 2 == 0:
                right_peripherals.append(periph_data)
            else:
                left_peripherals.append(periph_data)

        # --- Layout Calculation ---
        height_left = self._get_total_stack_height(left_peripherals)
        height_right = self._get_total_stack_height(right_peripherals)
        
        pins_on_left_edge = sum(len(p['pins']) for p in left_peripherals)
        pins_on_right_edge = sum(len(p['pins']) for p in right_peripherals)
        
        max_pins_side = max(pins_on_left_edge, pins_on_right_edge)
        min_board_height = self.PIN_MARGIN_TOP + max_pins_side * self.PIN_SPACING + self.PIN_MARGIN_BOTTOM
        
        total_content_height = max(height_left, height_right, min_board_height)
        
        canvas_height = total_content_height + 2 * self.MARGIN_Y
        canvas_width = self.MARGIN_X + self.PERIPH_WIDTH + self.GAP_BOARD_PERIPH + self.BOARD_WIDTH + self.GAP_BOARD_PERIPH + self.PERIPH_WIDTH + self.MARGIN_X
        
        center_y = canvas_height / 2
        
        board_x = self.MARGIN_X + self.PERIPH_WIDTH + self.GAP_BOARD_PERIPH
        board_h = max(min_board_height, total_content_height * 0.6)
        board_y = center_y - board_h / 2
        
        board_rect = {
            'x': board_x, 'y': board_y, 'w': self.BOARD_WIDTH, 'h': board_h,
            'name': self.get_board().name
        }

        svg_elements = []
        
        # --- Draw Board ---
        svg_elements.append(f'<!-- Board -->')
        svg_elements.append(self._svg_rect(board_rect['x'], board_rect['y'], board_rect['w'], board_rect['h'], self.COLOR_BOARD_FILL, self.COLOR_BOARD_STROKE))
        svg_elements.append(self._svg_text(board_rect['x'] + board_rect['w']/2, board_rect['y'] + 30, board_rect['name'], self.FONT_COMP_TITLE, self.COLOR_BOARD_TEXT, weight="bold"))
        
        # --- Draw Peripherals & Connections ---
        self._draw_stack(svg_elements, left_peripherals, True, center_y, board_rect, canvas_width)
        self._draw_stack(svg_elements, right_peripherals, False, center_y, board_rect, canvas_width)

        # --- Final Output ---
        try:
            with open(self.output_file, "w") as f:
                f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width}" height="{canvas_height}" viewBox="0 0 {canvas_width} {canvas_height}" style="background-color: {self.COLOR_BG};">\n')
                f.write(self._svg_text(canvas_width/2, 30, f"Device Diagram: {model.metadata.name}", self.FONT_TITLE, "#333333", weight="bold"))
                f.write("\n".join(svg_elements))
                f.write('\n</svg>')
            print(f"Successfully generated SVG: {self.output_file}")
        except Exception as e:
            print(f"Error writing SVG file: {e}")

    def _get_total_stack_height(self, periph_list):
        h = 0
        for p in periph_list:
            h += p['height'] + 30
        return h

    def _svg_rect(self, x, y, w, h, fill, stroke, r=8):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="2" rx="{r}" ry="{r}" />'
    
    def _svg_text(self, x, y, text, size, color, anchor="middle", weight="normal", baseline="middle"):
        return f'<text x="{x}" y="{y}" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}" dominant-baseline="{baseline}">{text}</text>'
    
    def _svg_line(self, x1, y1, x2, y2, color):
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2" />'

    def _svg_bezier(self, x1, y1, x2, y2, color):
        dist = abs(x2 - x1) * 0.5
        cp1x = x1 + dist if x2 > x1 else x1 - dist
        cp1y = y1
        cp2x = x2 - dist if x2 > x1 else x2 + dist
        cp2y = y2
        return f'<path d="M {x1} {y1} C {cp1x} {cp1y}, {cp2x} {cp2y}, {x2} {y2}" stroke="{color}" stroke-width="2" fill="none" />'

    def _svg_circle(self, cx, cy, r, fill):
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" />'

    def _draw_stack(self, svg_elements, periphs, is_left_side, center_y, board_rect, canvas_width):
        stack_h = self._get_total_stack_height(periphs)
        start_y = center_y - stack_h / 2
        current_y = start_y
        
        total_pins = sum(len(p['pins']) for p in periphs)
        board_edge_x = board_rect['x'] if is_left_side else board_rect['x'] + board_rect['w']
        
        req_h = total_pins * self.PIN_SPACING
        pin_start_y = board_rect['y'] + (board_rect['h'] - req_h) / 2 + self.PIN_SPACING/2
        
        global_pin_idx = 0
        
        for p in periphs:
            p_x = self.MARGIN_X if is_left_side else canvas_width - self.MARGIN_X - self.PERIPH_WIDTH
            p_y = current_y
            p_w = self.PERIPH_WIDTH
            p_h = p['height']
            
            svg_elements.append(f'<!-- Peripheral: {p["name"]} -->')
            svg_elements.append(self._svg_rect(p_x, p_y, p_w, p_h, self.COLOR_PERIPH_FILL, self.COLOR_PERIPH_STROKE))
            svg_elements.append(self._svg_text(p_x + p_w/2, p_y + 25, p["name"], self.FONT_COMP_TITLE, self.COLOR_PERIPH_TEXT, weight="bold"))
            
            periph_pin_x = p_x + p_w if is_left_side else p_x
            periph_text_anchor = "end" if is_left_side else "start"
            periph_text_x = periph_pin_x - 10 if is_left_side else periph_pin_x + 10
            
            board_text_anchor = "start" if is_left_side else "end"
            board_text_x = board_edge_x + 10 if is_left_side else board_edge_x - 10
            
            for i, pin in enumerate(p['pins']):
                pp_y = p_y + self.PIN_MARGIN_TOP + i * self.PIN_SPACING
                bp_y = pin_start_y + global_pin_idx * self.PIN_SPACING
                global_pin_idx += 1
                
                line_color = self.COLOR_LINE_DEFAULT
                if pin['type'] == 'power': line_color = self.COLOR_LINE_POWER
                elif pin['type'] == 'gnd': line_color = self.COLOR_LINE_GND
                
                svg_elements.append(self._svg_bezier(board_edge_x, bp_y, periph_pin_x, pp_y, line_color))
                svg_elements.append(self._svg_circle(board_edge_x, bp_y, 4, line_color))
                svg_elements.append(self._svg_circle(periph_pin_x, pp_y, 4, line_color))
                svg_elements.append(self._svg_text(board_text_x, bp_y, pin['board'], self.FONT_PIN, self.COLOR_BOARD_TEXT, anchor=board_text_anchor))
                svg_elements.append(self._svg_text(periph_text_x, pp_y, pin['periph'], self.FONT_PIN, self.COLOR_PIN_TEXT, anchor=periph_text_anchor))

            current_y += p_h + 30

def device_to_svg(model, output_file=None):
    """
    Entry point for the SVG transformation.
    """
    generator = SvgGenerator(model, output_file)
    generator.generate()
