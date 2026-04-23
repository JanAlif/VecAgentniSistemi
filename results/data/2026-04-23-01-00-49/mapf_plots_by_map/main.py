from PIL import Image

# List of your filenames
files = [
    "empty-8-8.map_solved.png",
    "empty-8-8.map_soc.png",
    "empty-8-8.map_makespan.png",

    "random-32-32-20.map_solved.png",
    "random-32-32-20.map_soc.png",
    "random-32-32-20.map_makespan.png",

    "random-64-64-20.map_solved.png",
    "random-64-64-20.map_soc.png",
    "random-64-64-20.map_makespan.png",
]

images = [Image.open(f) for f in files]

# Resize if necessary to make a clean grid
# Standardize the first 4 to the same size
w, h = images[0].size
canvas = Image.new("RGB", (w * 3, h * 3), (255, 255, 255))

# Paste first 4 in a 2x2 grid
canvas.paste(images[0], (0, 0))
canvas.paste(images[1], (w, 0))
canvas.paste(images[2], (w*2, 0))

canvas.paste(images[3], (0, h))
canvas.paste(images[4], (w, h))
canvas.paste(images[5], (w*2, h))

canvas.paste(images[6], (0, h*2))
canvas.paste(images[7], (w, h*2))
canvas.paste(images[8], (w*2, h*2))

# Paste the 5th (larger) one centered at the bottom
# Resize 5th to fit width if needed


canvas.save("combined_results.png")
