"""
Script to copy two identical versions spireA and spireB into spire/twins to run digital twins inside
"""
import shutil
from pathlib import Path

source = Path.cwd()
output = source / "twins"

output.mkdir(exist_ok=False)

def ignore_output(directory, names):
    if Path(directory) == source:
        return {output.name}
    return set()

for i in range(1, 3):
    if i == 1: destination = output / f"spireA"
    else: destination = output / f"spireB"

    shutil.copytree(
        source,
        destination,
        ignore=ignore_output,
        symlinks=True
    )

    print(f"Created: {destination}")

print("Done!")