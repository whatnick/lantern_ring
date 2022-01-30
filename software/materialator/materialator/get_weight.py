material_table = {
    "9ct gold" : 11.3
}

from stl import Mesh

def compute_volume(stl_file : str) -> float:
    mesh = Mesh.from_file(stl_file)
    mass = mesh.get_mass_properties_with_density(1)
    print(mass)
    return mass

def get_weight(stl_file : str, material : str) -> float:
    density = material_table[material]
    volume = compute_volume(stl_file)
    return density*volume