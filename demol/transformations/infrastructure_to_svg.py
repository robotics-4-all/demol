import jinja2
from pathlib import Path
from .base_generator import BaseCodeGenerator
from demol.definitions import TEMPLATES_DOCS

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
        self.env = self.setup_template_environment()

    def setup_template_environment(self):
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(TEMPLATES_DOCS),
            autoescape=jinja2.select_autoescape(['html', 'xml', 'j2'])
        )

    def generate(self) -> None:
        model = self.device_model
        board = self.get_board()
        broker = self.get_broker_config()
        connections = self.get_connections()
        
        # Layout Calculations
        num_periphs = len(connections)
        total_periph_height = num_periphs * self.BOX_HEIGHT + (num_periphs - 1) * self.PERIPH_SPACING
        
        # Application Layer elements
        apps_list = ["Cloud Platform", "Mobile App", "Analytics Service"]
        num_apps = len(apps_list)
        total_app_height = num_apps * self.BOX_HEIGHT + (num_apps - 1) * self.PERIPH_SPACING
        
        canvas_height = max(400, total_periph_height + 100, total_app_height + 100)
        canvas_width = 1200
        
        y_mid = canvas_height / 2
        x_periph = 100
        x_board = 350
        x_broker = 650
        x_apps = 1000
        
        # Prepare data for template
        peripherals = []
        periph_start_y = y_mid - total_periph_height / 2
        for i, conn in enumerate(connections):
            if not hasattr(conn, 'peripheral') or not conn.peripheral:
                continue
            p_ref = conn.peripheral.ref
            p_name = conn.peripheral.name
            p_y = periph_start_y + i * (self.BOX_HEIGHT + self.PERIPH_SPACING)
            
            protocol = "IO"
            if hasattr(conn, 'dataConns') and conn.dataConns:
                protocols = set(dc.type.upper() for dc in conn.dataConns)
                protocol = "/".join(sorted(protocols))
            
            peripherals.append({
                'name': p_name,
                'type': p_ref.type,
                'x': x_periph,
                'y': p_y,
                'protocol': protocol
            })

        apps = []
        app_start_y = y_mid - total_app_height / 2
        for i, app_name in enumerate(apps_list):
            a_y = app_start_y + i * (self.BOX_HEIGHT + self.PERIPH_SPACING)
            apps.append({
                'name': app_name,
                'x': x_apps,
                'y': a_y
            })

        network_type = "Network"
        if hasattr(model, 'network'):
            network_type = type(model.network).__name__.replace('Network', '')

        topics = []
        topics_y = y_mid + 15
        for i, conn in enumerate(connections):
            if not hasattr(conn, 'peripheral') or not conn.peripheral:
                continue
            topic = conn.remote if hasattr(conn, 'remote') and conn.remote else "N/A"
            topics.append({
                'text': topic,
                'y': topics_y + i*12
            })

        template_data = {
            "canvas": {
                "width": canvas_width,
                "height": canvas_height,
                "bg_color": self.COLOR_BG,
                "title": model.metadata.name
            },
            "colors": {
                "text": self.COLOR_TEXT,
                "text_light": self.COLOR_TEXT_LIGHT,
                "line": self.COLOR_LINE,
                "periph": self.COLOR_PERIPH,
                "board": self.COLOR_BOARD,
                "broker": self.COLOR_BROKER,
                "app": self.COLOR_APP
            },
            "box": {
                "width": self.BOX_WIDTH,
                "height": self.BOX_HEIGHT
            },
            "layers": [
                {"name": "Edge Layer", "x": x_board},
                {"name": "Communication Layer", "x": x_broker},
                {"name": "Application Layer", "x": x_apps}
            ],
            "separators": [
                {"x": (x_board + x_broker)/2 - 50},
                {"x": (x_broker + x_apps)/2 - 50}
            ],
            "peripherals": peripherals,
            "board": {
                "name": board.name,
                "type": board.type,
                "x": x_board,
                "y_mid": y_mid
            },
            "broker": {
                "host": broker['host'],
                "port": broker['port'],
                "x": x_broker,
                "y_mid": y_mid
            },
            "apps": apps,
            "network": {
                "type": network_type
            },
            "topics": topics
        }

        # Render Template
        try:
            template = self.env.get_template("infrastructure.svg.j2")
            output = template.render(**template_data)
            
            with open(self.output_file, "w") as f:
                f.write(output)
            print(f"Successfully generated Infrastructure SVG: {self.output_file}")
        except Exception as e:
            print(f"Error generating Infrastructure SVG: {e}")

def infrastructure_to_svg(model, output_file=None):
    generator = InfrastructureSvgGenerator(model, output_file)
    generator.generate()
