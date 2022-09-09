"""Generate colorised tiles sprites."""
from pathlib import Path
from PIL import Image
import numpy as np

COLOR_TO_RGB = {
    'red': (1, 0, 0),
    'orange': (1, 0.4, 0),
    'yellow': (1, 0.9, 0),
    'green': (0, 0.8, 0.1),
    'blue': (0, 0.3, 0.9),
    'purple': (0.8, 0, 1.0),
    'gray': (0.6, 0.6, 0.6),
}

root = Path('images/pixel_platformer_blocks/tiles/marble')
for source_file in root.glob('*.png'):
    source_img = Image.open(source_file).convert('RGBA')
    pixels = np.array(source_img).astype(np.float32)

    for name, color in COLOR_TO_RGB.items():
        dest_path = Path('images', f"{source_file.stem}_{name}.png")
        colorised = pixels.copy()
        colorised[:,:,:3] *= color
        dest = Image.fromarray(colorised.astype(np.uint8))
        dest.save(dest_path)
        print(dest_path)
