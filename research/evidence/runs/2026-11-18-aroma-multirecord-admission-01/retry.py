import importlib.util
from pathlib import Path

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('original_acquisition', here / 'fetch.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.HERE = here / 'corrected'
module.HERE.mkdir(exist_ok=True)
module.SOURCES = {name: url.replace('facebookresearch/aroma/', 'facebookresearch/aroma-paper-artifacts/')
                  for name, url in module.SOURCES.items()}
module.main()
