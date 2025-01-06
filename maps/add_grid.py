from PIL import Image, ImageDraw, ImageFont
import os

def draw_edge_axes_with_border(image_path, output_path, grid_spacing, axis_color="red", tick_length=10, border_width=50, line_width=2, label_color="black", font_size=16):
    """
    Adds a white border to an image and draws axes with numbered ticks along the edges.

    Args:
        image_path (str): Path to the input image.
        output_path (str): Path to save the output image.
        grid_spacing (int): Spacing between ticks in pixels.
        axis_color (str or tuple): Color of the axis lines and ticks (e.g., "red" or (255, 0, 0)).
        tick_length (int): Length of the ticks in pixels.
        border_width (int): Width of the white border in pixels.
        line_width (int): Width of the axis lines.
        label_color (str or tuple): Color of the labels (e.g., "black" or (0, 0, 0)).
        font_size (int): Font size for the labels.
    """
    # Load the image
    image = Image.open(image_path)
    original_width, original_height = image.size

    # Add a white border around the image
    new_width = original_width + 2 * border_width
    new_height = original_height + 2 * border_width
    bordered_image = Image.new("RGB", (new_width, new_height), "white")
    bordered_image.paste(image, (border_width, border_width))

    draw = ImageDraw.Draw(bordered_image)

    # Try to load a default font
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    # Draw the X-axis (bottom edge)
    draw.line([(border_width, new_height - border_width), (new_width - border_width, new_height - border_width)], fill=axis_color, width=line_width)
    for x in range(0, original_width + 1, grid_spacing):
        # Draw ticks on the X-axis
        tick_x = border_width + x
        draw.line([(tick_x, new_height - border_width), (tick_x, new_height - border_width + tick_length)], fill=axis_color, width=line_width)
        # Add labels
        draw.text((tick_x - font_size // 2, new_height - border_width + tick_length + 2), str(x), fill=label_color, font=font)

    # Draw the Y-axis (left edge)
    draw.line([(border_width, border_width), (border_width, new_height - border_width)], fill=axis_color, width=line_width)
    for y in range(0, original_height + 1, grid_spacing):
        # Draw ticks on the Y-axis
        tick_y = border_width + y
        draw.line([(border_width - tick_length, tick_y), (border_width, tick_y)], fill=axis_color, width=line_width)
        # Add labels
        draw.text((border_width - tick_length - font_size * 2, tick_y - font_size // 2), str(y), fill=label_color, font=font)

    # Save the output image
    bordered_image.save(output_path)
    print(f"Image with edge axes saved at {output_path}")


current_dir = '/data/claireji/maps/test_maps/'
output_dir = '/data/claireji/maps/test_maps_with_grid/'
grid_spacing = 50  # Spacing between grid lines in pixels
axis_color = "blue"  # Color of the axis lines

# Iterate through HTML files in the directory
for file in os.listdir(current_dir):
    if file.endswith(".png"):
        image_path = os.path.join(current_dir, file)
        output_path = os.path.join(output_dir, f"grid_{file}")
        draw_edge_axes_with_border(image_path, output_path, grid_spacing, axis_color)

