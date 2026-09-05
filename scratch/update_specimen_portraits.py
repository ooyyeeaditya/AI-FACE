from pathlib import Path
import re

p = Path("/Users/aaryamanrana/Documents/Facesih /generators/specimen_generator.py")
content = p.read_text()

# Update _draw_synthetic_portrait definition
content = content.replace(
    '''def _draw_synthetic_portrait(
    size=(160, 200),
    skin_tone=(215, 175, 140),
    hair_color=(40, 30, 25),
    shirt_color=(50, 70, 100),
) -> Image.Image:
    """Draw a clean synthetic traveler portrait icon."""
    img = Image.new("RGB", size, (230, 235, 240))''',
    '''def _draw_synthetic_portrait(
    size=(160, 200),
    skin_tone=(215, 175, 140),
    hair_color=(40, 30, 25),
    shirt_color=(50, 70, 100),
    bg_color=(230, 235, 240),
) -> Image.Image:
    """Draw a clean synthetic traveler portrait icon."""
    img = Image.new("RGB", size, bg_color)'''
)

# Update generate_traveler_live_photo
content = content.replace(
    '''    else:
        # Visibly distinct person (dark skin, blonde hair, bright orange coat)
        img = _draw_synthetic_portrait(
            size=(320, 400),
            skin_tone=(110, 70, 45),
            hair_color=(240, 210, 60),
            shirt_color=(220, 100, 20),
        )''',
    '''    else:
        # Visibly distinct person (dark skin, blonde hair, bright orange coat, dark studio background)
        img = _draw_synthetic_portrait(
            size=(320, 400),
            skin_tone=(100, 60, 40),
            hair_color=(240, 210, 60),
            shirt_color=(220, 80, 20),
            bg_color=(70, 80, 95),
        )'''
)

p.write_text(content)
print("Updated specimen_generator.py successfully!")
