import math
from pathlib import Path
from .base_generator import BaseCodeGenerator

class InfrastructureSvgGenerator(BaseCodeGenerator):
    """
    Generates a high-level infrastructure SVG diagram.
    Shows: Peripherals -> Board -> Network -> Broker -> Application Layer
    """
    
    # --- Configuration ---
    COLOR_BG = "#FFFFFF"
    COLOR_BOARD = "#0F172A"   # Slate 900
    COLOR_PERIPH = "#2563EB"  # Blue 600
    COLOR_BROKER = "#D97706"  # Amber 600
    COLOR_APP = "#059669"     # Emerald 600
    COLOR_TEXT = "#1E293B"    # Slate 800
    COLOR_TEXT_LIGHT = "#F8FAFC" # Slate 50
    COLOR_LINE = "#94A3B8"    # Slate 400
    
    BOX_WIDTH = 140
    BOX_HEIGHT = 60
    PERIPH_SPACING = 20
    
    def __init__(self, device_model, output_file=None):
        if not output_file:
            output_file = f"{device_model.metadata.name}_infrastructure.svg"
        self.output_file = Path(output_file)
        super().__init__(device_model, self.output_file.parent)

    def setup_template_environment(self):
        return None

    def generate(self) -> None:
        model = self.device_model
        board = self.get_board()
        broker = self.get_broker_config()
        connections = self.get_connections()
        
        # Layout Calculations
        num_periphs = len(connections)
        total_periph_height = num_periphs * self.BOX_HEIGHT + (num_periphs - 1) * self.PERIPH_SPACING
        
        # Application Layer elements
        apps = ["Cloud Platform", "Mobile App", "Analytics Service"]
        num_apps = len(apps)
        total_app_height = num_apps * self.BOX_HEIGHT + (num_apps - 1) * self.PERIPH_SPACING
        
        canvas_height = max(400, total_periph_height + 100, total_app_height + 100)
        canvas_width = 1200
        
        y_mid = canvas_height / 2
        x_periph = 100
        x_board = 350
        x_broker = 650
        x_apps = 1000
        
        svg_elements = []
        
        # Layer Separators (Vertical Dashed Lines) - Draw first to be in background
        sep_y1 = 80
        sep_y2 = canvas_height - 40
        svg_elements.append(self._svg_line((x_board + x_broker)/2 - 50, sep_y1, (x_board + x_broker)/2 - 50, sep_y2, self.COLOR_LINE, dashed=True))
        svg_elements.append(self._svg_line((x_broker + x_apps)/2 - 50, sep_y1, (x_broker + x_apps)/2 - 50, sep_y2, self.COLOR_LINE, dashed=True))
        
        # 1. Draw Peripherals
        periph_start_y = y_mid - total_periph_height / 2
        for i, conn in enumerate(connections):
            p_ref = conn.peripheral.ref
            p_name = conn.peripheral.name
            p_y = periph_start_y + i * (self.BOX_HEIGHT + self.PERIPH_SPACING)
            
            # Peripheral Box
            svg_elements.append(self._svg_rect(x_periph - self.BOX_WIDTH/2, p_y, self.BOX_WIDTH, self.BOX_HEIGHT, self.COLOR_PERIPH, "#2980b9"))
            svg_elements.append(self._svg_text(x_periph, p_y + 20, p_name, 12, self.COLOR_TEXT_LIGHT, weight="bold"))
            svg_elements.append(self._svg_text(x_periph, p_y + 40, f"({p_ref.type})", 10, self.COLOR_TEXT_LIGHT))
            
            # Connection to Board
            protocol = "IO"
            if hasattr(conn, 'dataConns') and conn.dataConns:
                protocols = set(dc.type.upper() for dc in conn.dataConns)
                protocol = "/".join(sorted(protocols))
            
            svg_elements.append(self._svg_line(x_periph + self.BOX_WIDTH/2, p_y + self.BOX_HEIGHT/2, x_board - self.BOX_WIDTH/2, y_mid, self.COLOR_LINE))
            
            # Protocol Label
            lx = (x_periph + self.BOX_WIDTH/2 + x_board - self.BOX_WIDTH/2) / 2
            ly = (p_y + self.BOX_HEIGHT/2 + y_mid) / 2 - 5
            svg_elements.append(self._svg_text(lx, ly, protocol, 9, self.COLOR_TEXT))

        # 2. Board Box
        svg_elements.append(self._svg_rect(x_board - self.BOX_WIDTH/2, y_mid - self.BOX_HEIGHT/2, self.BOX_WIDTH, self.BOX_HEIGHT, self.COLOR_BOARD, "#1a252f"))
        svg_elements.append(self._svg_text(x_board, y_mid - 10, board.name, 12, self.COLOR_TEXT_LIGHT, weight="bold"))
        svg_elements.append(self._svg_text(x_board, y_mid + 10, f"({board.type})", 10, self.COLOR_TEXT_LIGHT))
        
        # 3. Broker Box
        svg_elements.append(self._svg_rect(x_broker - self.BOX_WIDTH/2, y_mid - self.BOX_HEIGHT/2, self.BOX_WIDTH, self.BOX_HEIGHT, self.COLOR_BROKER, "#d35400"))
        svg_elements.append(self._svg_text(x_broker, y_mid - 10, "MQTT Broker", 14, self.COLOR_TEXT_LIGHT, weight="bold"))
        svg_elements.append(self._svg_text(x_broker, y_mid + 10, f"{broker['host']}:{broker['port']}", 10, self.COLOR_TEXT_LIGHT))
        
        # 4. Application Layer
        app_start_y = y_mid - total_app_height / 2
        for i, app_name in enumerate(apps):
            a_y = app_start_y + i * (self.BOX_HEIGHT + self.PERIPH_SPACING)
            
            # App Box
            svg_elements.append(self._svg_rect(x_apps - self.BOX_WIDTH/2, a_y, self.BOX_WIDTH, self.BOX_HEIGHT, self.COLOR_APP, "#1e8449"))
            svg_elements.append(self._svg_text(x_apps, a_y + self.BOX_HEIGHT/2, app_name, 12, self.COLOR_TEXT_LIGHT, weight="bold"))
            
            # Connection to Broker
            svg_elements.append(self._svg_line(x_broker + self.BOX_WIDTH/2, y_mid, x_apps - self.BOX_WIDTH/2, a_y + self.BOX_HEIGHT/2, self.COLOR_LINE))
            
            # Label
            lx = (x_broker + self.BOX_WIDTH/2 + x_apps - self.BOX_WIDTH/2) / 2
            ly = (y_mid + a_y + self.BOX_HEIGHT/2) / 2 - 5
            svg_elements.append(self._svg_text(lx, ly, "MQTT", 9, self.COLOR_TEXT))

        # Connection Board -> Broker
        svg_elements.append(self._svg_line(x_board + self.BOX_WIDTH/2, y_mid, x_broker - self.BOX_WIDTH/2, y_mid, self.COLOR_LINE))
        
        # Network Label
        network_type = "Network"
        if hasattr(model, 'network'):
            network_type = type(model.network).__name__.replace('Network', '')
        svg_elements.append(self._svg_text((x_board + x_broker)/2, y_mid - 15, network_type, 10, self.COLOR_TEXT, weight="bold"))
        
        # Topics
        topics_y = y_mid + 15
        for i, conn in enumerate(connections):
            topic = conn.remote if hasattr(conn, 'remote') and conn.remote else "N/A"
            svg_elements.append(self._svg_text((x_board + x_broker)/2, topics_y + i*12, topic, 8, "#7f8c8d", anchor="middle"))


        # Layer Titles
        svg_elements.append(self._svg_text(x_board, 60, "Edge Layer", 14, self.COLOR_TEXT, weight="bold"))
        svg_elements.append(self._svg_text(x_broker, 60, "Communication Layer", 14, self.COLOR_TEXT, weight="bold"))
        svg_elements.append(self._svg_text(x_apps, 60, "Application Layer", 14, self.COLOR_TEXT, weight="bold"))

        # Final SVG
        try:
            with open(self.output_file, "w") as f:
                f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width}" height="{canvas_height}" viewBox="0 0 {canvas_width} {canvas_height}" style="background-color: {self.COLOR_BG};">\n')
                f.write(self._svg_text(canvas_width/2, 30, f"Infrastructure: {model.metadata.name}", 20, self.COLOR_TEXT, weight="bold"))
                f.write("\n".join(svg_elements))
                f.write('\n</svg>')
            print(f"Successfully generated Infrastructure SVG: {self.output_file}")
        except Exception as e:
            print(f"Error writing Infrastructure SVG file: {e}")

    def _svg_rect(self, x, y, w, h, fill, stroke, r=5):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="2" rx="{r}" ry="{r}" />'
    
    def _svg_text(self, x, y, text, size, color, anchor="middle", weight="normal", baseline="middle"):
        return f'<text x="{x}" y="{y}" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}" dominant-baseline="{baseline}">{text}</text>'
    
    def _svg_line(self, x1, y1, x2, y2, color, dashed=False):
        dash_attr = ' stroke-dasharray="5,5"' if dashed else ''
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2"{dash_attr} />'

def infrastructure_to_svg(model, output_file=None):
    generator = InfrastructureSvgGenerator(model, output_file)
    generator.generate()
