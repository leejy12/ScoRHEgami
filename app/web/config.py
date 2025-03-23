import os

from fastapi.templating import Jinja2Templates

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates_dir = os.path.join(base_dir, "templates")

templates = Jinja2Templates(directory=templates_dir)
