print(""" Linear structural analysis using PyMAPDL
     Getting started with PyMAPDL
      PyMAPDL is a verastile library of the PyAnsys ecosystem, a pythonic integration of Ansys tools designed to streamline engineering simulations within python workflows. By combining Ansys’s robust simulation engine with Python’s flexibility, PyMAPDL empowers engineers to build scalable, scriptable solutions for simple to complex mechanical problems.
      For more information visit - https://docs.pyansys.com/  
      For detailed courses on getting started - https://innovationspace.ansys.com/product/getting-started-with-ansys-pymapdl/
""")


print("""===========Getting Started===========
Install any editor of choice  
Install Python, **Python 3.10** was used to develop the following script  
Navigate to the respective working directory and paste the jupyter notebook  
Setup and activate a virtual environment named pymapdlvenv, **python -m venv pymapdlvenv**    
   
   Install  the required libraries  
   pip install ansys-mapdl-core==0.71.0
   pip install ansys-mapdl-core[graphics]  
   pip install numpy
   pip install pyvista==0.45.3
====================================   

""")


print("""Import the necessary libraries

numpy: for numerical operations (e.g.,user defined stress calculations)  
pyvista: for 3D visualization of results  
mapdl: for the MAPDL solver  """)

import numpy as np
import pyvista as pv
from ansys.mapdl.core import launch_mapdl



print("""Step 1 : MAPDL Initialization and Setup

Launch MAPDL Instance
The first step in any PyMAPDL analysis is to establish a connection with the ANSYS MAPDL solver. This creates a Python interface to the finite element solver for numerical computations.

**Key Operations:**
- Start MAPDL background process
- Clear any existing database to ensure clean workspace  
- Set analysis title for identification and documentation
""")

# Launch MAPDL
mapdl = launch_mapdl()
mapdl.clear()
mapdl.title("Tensile Test ASTM E13 Geometry with Realistic Grip Loading")

# -------------------------- PRE-PROCESSING --------------------------

print(""" Geometry Creation
      
This simulation models a tensile test using the ASTM E8 standard specimen geometry. The goal is to analyze stress distribution and deformation under realistic grip loading using PyMAPDL.

Simulation Type: Linear static structural analysis  
Material: Steel (Young’s Modulus = 210 GPa, Poisson’s Ratio = 0.3)  
Boundary Conditions: One end fixed, the other displaced to simulate tensile loading  
Output: Displacement and Von Mises stress distribution (Extracted using user-defined method)  

**Note:** MAPDL is unitless solver thus consistency in units for geometry, material properties, loads, results should be ensured and is as follows:    
Length: millimeters (mm)  
Force: Newtons (N)  
Stress: Megapascals (MPa)  
Young’s Modulus:  Megapascals (MPa)

**Key Operations:**
- Enter the preprocessor
- Define the geometry and mesh parameters converted in respective unit (mm used for the following case)
- Define the driving and derived values for the geometric parameters
- Define the parametric relation for the driving and derived parameters
- Define the Keypoints (Similar to the co-ordinates plot on a graph)
- Generate lines, arc connecting the respective Keypoints
- Merge all entities, avoides duplication and geometric errors
- Visualization of the geometry
""")


mapdl.prep7()

# Geometry and mesh parameters (in mm)
thickness = 1.5
end_width = 50
reduced_width = 40
grip_length = 75
fillet_offset = 10
red_length = 280
fillet_radius = 12.5
disp_x = 0.5
mesh_size = 1


print("""Geometry is defined in a parametric way to ensure scalablity and flexibility. This approach allows easy adjustments to specimen dimensions by simply modifying a few key parameters, which automatically update all dependent geometric calculations and also minimizes errors during geometry creation.By deriving coordinates from well-defined parameters, the keypoints are placed precisely, followed by the creation of lines and arcs to form the specimen profile. Entities are then merged to avoid duplication, and the area is plotted.""")

x_outer = grip_length + fillet_offset + red_length / 2
x_fillet_start = fillet_offset + red_length / 2
x_parallel = red_length / 2
y_end = end_width / 2
y_reduced = reduced_width / 2
y_fillet_top = y_reduced + fillet_radius
y_fillet_bot = -y_reduced - fillet_radius

# Keypoints
mapdl.k(1, -x_outer, y_end); mapdl.k(2, -x_fillet_start, y_end)
mapdl.k(3, -x_parallel, y_reduced); mapdl.k(4, x_parallel, y_reduced)
mapdl.k(5, x_fillet_start, y_end); mapdl.k(6, x_outer, y_end)
mapdl.k(7, x_outer, -y_end); mapdl.k(8, x_fillet_start, -y_end)
mapdl.k(9, x_parallel, -y_reduced); mapdl.k(10, -x_parallel, -y_reduced)
mapdl.k(11, -x_fillet_start, -y_end); mapdl.k(12, -x_outer, -y_end)
mapdl.k(13, -x_parallel, y_fillet_top); mapdl.k(14, x_parallel, y_fillet_top)
mapdl.k(15, x_parallel, y_fillet_bot); mapdl.k(16, -x_parallel, y_fillet_bot)

# Lines and arcs
mapdl.l(1,2); mapdl.larc(2,3,13,fillet_radius)
mapdl.l(3,4); mapdl.larc(4,5,14,fillet_radius)
mapdl.l(5,6); mapdl.l(6,7)
mapdl.l(7,8); mapdl.larc(8,9,15,fillet_radius)
mapdl.l(9,10); mapdl.larc(10,11,16,fillet_radius)
mapdl.l(11,12); mapdl.l(12,1)

mapdl.nummrg("ALL")
mapdl.al("ALL")
mapdl.aplot(cpos="xy", show_lines=True, title="ASTM E8 Geometry")

print("""#### Element Type & Mesh details
Considering the nature of loading and the geometry, 2D model would help tackle efficiency and accuracy. Shell elements are suitable for thin to moderately thick shell structures. Each node has 6 degrees of freedom, 3 translational and 3 rotational about x,y,z, axes. These versatile elements also support large rotation, and layered composite modeling more on this can be accessed - https://ansyshelp.ansys.com/public/account/secured?returnurl=/Views/Secured/corp/v242/en/ans_elem/Hlp_E_SHELL181.html



**Key Operations:**
- Define the element type
- Set the element properties by defining key options
- Defining section data along with the thickness for the Shell element""")


# Element and material definition
mapdl.et(1, "SHELL181")
mapdl.keyopt(1, 3, 2)
mapdl.keyopt(1, 8, 2)
mapdl.sectype(1, "SHELL")
mapdl.secdata(thickness)

print("""#### Material Properties  

Analysis uses the material "Steel" with the Young's moudulus of 210 GPa and 0.3 as Poisson's ratio.  
Cosnidering the static nature of the problem, density won't play a critical role in the material definition. Considering the redundancy it is thus not defined.  
  
**Key Operations:**
- Define the material properties
- Assign the the material properties to the elements
- Assign the section properties to the elements""")



mapdl.mp("EX", 1, 210000)  # Young's modulus in MPa
mapdl.mp("PRXY", 1, 0.3)


print("""#### Meshing the Geometry
      
**Mesh Quality Considerations**

For production analyses, additional mesh quality checks should be performed:

- **Aspect Ratio**: Elements should not be excessively elongated
- **Skewness**: Elements should be close to rectangular shape
- **Jacobian Ratio**: Measures element distortion
- **Mesh Refinement**: Consider adaptive mesh refinement for critical regions

**Advanced Meshing Options:**
- Use smaller elements near stress concentrations (fillets)
- Consider mesh transition zones for gradual size changes
- Implement mesh convergence studies to verify solution accuracy  

**Key Operations:**
- Define the element size and shape
- Discretization/ Meshing
- Mesh visualaztion
- Extracting mesh quality tolerances using "shpp"
- Extracting min/max/average for mesh quality data
- Exitting the preprocessor
      
      """)

# Mesh
mapdl.esize(mesh_size)
mapdl.mshape(0)
mapdl.amesh("ALL")
mapdl.eplot(cpos="xy", title="Mesh")


mapdl.shpp("STAT")
element_quality_tolerance_data = mapdl.shpp("STAT")
print("=== Element Quality Tolerances ===")
print(element_quality_tolerance_data)

mapdl.shpp("SUMM")
current_mesh_data = mapdl.shpp("SUMM")

print("=== min/max/average values for your current mesh ===")
print(current_mesh_data)



# Assign material and section
mapdl.emodif("ALL", "MAT", 1)
mapdl.emodif("ALL", "SECNUM", 1)

# -------------------------- SOLUTION --------------------------

print("""## Step 2 : Solution Setup and Execution

#### Analysis Configuration

The solution phase configures the finite element analysis type and output requests. For this tensile test simulation, we use static structural analysis.

**Analysis Type: Static Structural**
- **Assumption**: Loads are applied slowly (no inertial effects)
- **Response**: Equilibrium solution at final load state
- **Output**: Displacements, stresses, strains, and reaction forces

**Output Control:**
- Request all available results at all nodes and elements
- Enables comprehensive post-processing capabilities
- Provides data for stress analysis and design verification

**Key Operations:**
- Entering the solution processor
- Defining the Analysis type and the output controls
""")


mapdl.finish()
mapdl.slashsolu()
mapdl.antype("STATIC")
mapdl.outres("ALL", "ALL")

print("""#### Boundary Conditions Application

**Loading and Constraints Strategy**

Proper boundary conditions are crucial for realistic simulation of the tensile test. We simulate the specimen being gripped at both ends with one end fixed and the other displaced.

**Constraint Types:**
- **Fixed Support**: Left end grip completely constrained (all DOF = 0)
  - Simulates rigid grip attachment
  - Prevents rigid body motion
- **Displacement Loading**: Right end grip displaced in X-direction
  - Simulates controlled displacement tensile testing
  - More stable than force loading for this analysis

**Physical Interpretation:**
This setup represents a displacement-controlled tensile test where the specimen is stretched at a constant rate, typical of standard material testing procedures.


**Key Operations:**
- Selecting appropriate nodes for constrained condition and displacement condition
- Create plots for visualization
- Defining the boundary conditions by selecting appropriate nodes
      
      """)

# ---------------------- SELECT GRIP NODES ----------------------


x_min_left, x_max_left = -x_outer - 5, -x_fillet_start + 2
x_min_right, x_max_right = x_fillet_start - 2, x_outer + 5
y_min, y_max = -y_end, y_end

mapdl.nsel("S", "LOC", "X", x_min_left, x_max_left)
mapdl.nsel("R", "LOC", "Y", y_min, y_max)
mapdl.cm("GRIP_LEFT", "NODE")

mapdl.nsel("S", "LOC", "X", x_min_right, x_max_right)
mapdl.nsel("R", "LOC", "Y", y_min, y_max)
mapdl.cm("GRIP_RIGHT", "NODE")


mapdl.allsel()


print("""#### Solution Execution

**Finite Element Analysis**

The solver performs the numerical computation to determine displacements and stresses throughout the specimen under the applied loading conditions.

**Solution Process:**
1. Combine element stiffness matrices into global system
2. Apply boundary conditions and loads
3. Solve the linear system of equations K{u} = {F}
4. Calculate stresses and strains from displacements

**Convergence**: For linear static analysis, the solution converges in a single iteration since there are no nonlinearities present.


**Key Operations:**
- Executing the solution
- Exitting the solution processor post solving
      
      """)

# Get PyVista mesh
grid = mapdl.mesh.grid
node_nums = grid.point_data["ansys_node_num"]

# Get node numbers from MAPDL components
mapdl.cmsel("S", "GRIP_LEFT")
left_nodes = mapdl.mesh.nnum
mapdl.cmsel("S", "GRIP_RIGHT")
right_nodes = mapdl.mesh.nnum
mapdl.allsel()

# Create masks for visualization
selected_left = np.isin(node_nums, left_nodes)
selected_right = np.isin(node_nums, right_nodes)

# Extract and plot
plotter = pv.Plotter()
plotter.add_mesh(grid, color="lightgray", show_edges=True)

if np.any(selected_left):
    plotter.add_mesh(grid.extract_points(selected_left), color="blue", point_size=10,
                     render_points_as_spheres=True, label="Left Grip Nodes")
else:
    print("Warning: No left grip nodes found for visualization.")

if np.any(selected_right):
    plotter.add_mesh(grid.extract_points(selected_right), color="red", point_size=10,
                     render_points_as_spheres=True, label="Right Grip Nodes")
else:
    print("Warning: No right grip nodes found for visualization.")

plotter.add_legend()
plotter.view_xy()
plotter.show(title="Selected Grip Nodes Visualization")


# Apply realistic grip boundary conditions using bounding box components
mapdl.cmsel("S", "GRIP_LEFT")
mapdl.d("ALL", "UX", 0)
mapdl.d("ALL", "UY", 0)
mapdl.d("ALL", "UZ", 0)

mapdl.cmsel("S", "GRIP_RIGHT")
mapdl.d("ALL", "UX", disp_x)
mapdl.d("ALL", "UY", 0)
mapdl.d("ALL", "UZ", 0)

mapdl.allsel()
mapdl.solve()
mapdl.finish()
# ----------------------- POST-PROCESSING ----------------------


print("""## Step 3 : Post-Processing and Results Analysis

#### Result Extraction and Visualization

Post-processing is where we extract meaningful engineering insights from the numerical solution. This phase involves accessing calculated results, performing additional calculations, and creating visualizations.

**Post-Processing Workflow:**
1. **Access Results**: Load solution data from the database
2. **Extract Data**: Retrieve nodal and elemental results
3. **Calculate Derived Quantities**: Compute engineering parameters
4. **Visualize**: Create plots and contour maps for interpretation
5. **Validate**: Check results for physical reasonableness  


**Key Operations:**
- Entering the post processor
- Defining the result set for which the solution needs to be extracted
- Extracting the Displacement result
- Extracting the Stress result
- Extracting the Force reaction result
      """)



mapdl.post1()
mapdl.set("LAST")
result = mapdl.result


print("""#### Displacement Analysis

**Deformation Visualization**

Displacement results show how the specimen deforms under the applied loading. This provides insight into the global structural response and helps validate the boundary conditions.

**Key Observations to Look For:**
- **Maximum Displacement**: Should occur at the loaded end (right grip)
- **Deformation Pattern**: Should show uniform extension in the gauge section
- **Boundary Conditions**: Fixed end should show zero displacement

""")



# Displacement plot
mapdl.post_processing.plot_nodal_displacement(
    "NORM", cpos="xy", show_edges=True, show_displacement=True,
    displacement_factor=1.0, scalar_bar_args={"title": "Nodal Displacement (mm)"}
)


# # Displacement plot visualized with elements
# mapdl.post_processing.plot_nodal_displacement(  # Plot nodal displacement results
#     "NORM", cpos="xy", show_edges=True, show_displacement=True,  # Show displacement magnitude with edges and deformed shape
#     displacement_factor=1.0, scalar_bar_args={"title": "Nodal Displacement (mm)"}  # Set deformation scale and colorbar title
# )


print("""#### Stress Analysis - Von Mises Stress

**Two approaches to extracting results (what we do in this notebook):**

1. Predefined / convenience functions (used for displacement)
   - PyMAPDL provides higher-level post-processing helpers for common results (for example, `mapdl.post_processing.plot_nodal_displacement(...)` was used for displacement visualization in this notebook).
   - These helpers are convenient, well-tested, and handle many plotting and data-retrieval details (unit handling, nodal averaging, visualization options).
   - Use these when the built-in quantity matches your needs (e.g., displacement magnitude, reaction forces).

2. User-defined / manual extraction (used for Von Mises here)
   - For derived quantities that are not available as a single predefined call, we extract raw components (e.g., nodal stress components) and compute the desired scalar manually.
   - In this notebook we call the low-level extractor `result.nodal_stress(0)` to retrieve the nodal stress tensor, then compute the Von Mises equivalent stress using the full 3D formulation.
   - Reasons to use the user-defined route:
     - You want a custom definition (different Von Mises variants, plane stress vs 3D formulations).
     - You need to control averaging (nodal vs elemental), projection, or post-processing filters.
     - The built-in helper is not available or returns a different definition than required for the case study.

**Example workflow used here (high level):**
- Enter post-processing and load the solution set: `mapdl.post1(); mapdl.set("LAST")`
- Extract raw stress components with `result.nodal_stress(0)`
- Verify the extracted array is valid (non-empty, non-zero)
- Compute Equivalent Stress/ Von Mises with the chosen formula and map values back to the mesh for plotting

**Equivalent Stress Calculation**

Von Mises stress is a scalar measure of the stress state intensity, commonly used in engineering design and failure analysis. It represents the equivalent uniaxial stress that would produce the same distortion energy as the actual 3D stress state.

**Von Mises Stress Formula:**
$$\sigma_{VM} = \sqrt{\frac{1}{2}[(\sigma_x - \sigma_y)^2 + (\sigma_y - \sigma_z)^2 + (\sigma_z - \sigma_x)^2] + 3[\tau_{xy}^2 + \tau_{yz}^2 + \tau_{xz}^2]}$$

**Notes & best practices for case-study reporting:**
- Always document which extraction method you used. For reproducibility, include the exact commands (the code cell following this markdown contains them).
- Specify the Von Mises formulation used (3D vs plane stress). The notebook uses the full 3D formulation by combining σx, σy, σz and shear components.
- Be explicit about whether values are nodal or elemental, and whether any averaging or smoothing was applied.
- Check for units consistency: MAPDL is unitless — ensure Young's modulus, geometry, and load units are consistent (this notebook uses mm and MPa).
- Validate results with quick sanity checks (e.g., expected stress ranges, reaction force balance).

**When to prefer the predefined functions:**
- Quick visualization and standard results (displacement, reaction forces, principal stresses if provided by API).
- When you trust the API's averaging/plotting behavior and need speed.

**When to prefer the user-defined method:**
- Custom derived quantities (e.g., modified Von Mises, damage indicators)
- Need full control over averaging, filtering, or post-processing steps
- Verification or publication-quality processing where the exact formula and steps must be shown

This dual approach — using predefined helpers where they are appropriate and user-defined extraction where necessary — provides both convenience and full transparency for a rigorous case study.
      """)



# Extract nodal stress tensor
nnum, stress = result.nodal_stress(0)

# Check stress validity
if stress is None or np.allclose(stress, 0):
    raise ValueError("Stress data is invalid or contains only zeros.")

# Extract stress components
sx, sy, sz = stress[:, 0], stress[:, 1], stress[:, 2]
sxy, syz, sxz = stress[:, 3], stress[:, 4], stress[:, 5]

# Compute Von Mises stress (3D formulation)
von_mises = np.sqrt(
    0.5 * ((sx - sy)**2 + (sy - sz)**2 + (sz - sx)**2) +
    3 * (sxy**2 + syz**2 + sxz**2)
)

# Map stress to mesh grid
grid = mapdl.mesh.grid
grid.point_data["Von Mises Stress"] = von_mises

# Print stress range for verification
print(f"Von Mises Stress Range: min={von_mises.min():.2f} MPa, max={von_mises.max():.2f} MPa")

# Plot using PyVista
plotter = pv.Plotter()
plotter.add_mesh(grid, scalars="Von Mises Stress", cmap="jet", show_edges=True,
                 scalar_bar_args={"title": "Von Mises Stress (MPa)", "n_labels": 5, "n_colors": 256})
plotter.view_xy()
plotter.show(title="Von Mises Stress Distribution")


# Create PyVista plotter object with elements displayed
# plotter = pv.Plotter()  # Create PyVista plotter object
# plotter.add_mesh(grid, scalars="Von Mises Stress", cmap="jet", show_edges=True,  # Add mesh with stress coloring
#                  scalar_bar_args={"title": "Von Mises Stress (MPa)", "n_labels": 5, "n_colors": 256})  # Configure colorbar
# plotter.view_xy()   
# plotter.show(title="Von Mises Stress Distribution")  

# ---------------------- REACTION FORCES ------------------------

print("""#### Reaction Force Analysis

**Load Path Verification**

Reaction forces at the constrained boundary provide important information about the load transfer through the structure and can be used to verify the analysis setup.

**Engineering Significance:**
- **Force Balance**: Total reaction should equal applied load (for equilibrium)
- **Load Distribution**: Shows how forces distribute across the grip area
- **Design Validation**: Confirms that boundary conditions represent realistic constraints
      """)



mapdl.cmsel("S", "GRIP_LEFT")
print("\n" + "="*40)
print("Calculating Reaction Force Summation")
print(mapdl.fsum())
print("="*40 + "\n")
mapdl.allsel()


print("""## Step 4 : Analysis Completion
Close MAPDL session by exitting. This ensures free memoey and computational resources. It also helps in maintaining clean working environment for future analyses


- The analysis performed is **linear elastic**, meaning:
  - Stress is directly proportional to strain.
  - Strain is directly proportional to displacement.
  - No plastic deformation or material nonlinearity is considered.

- A **0.5 mm displacement** was applied to the right grip to simulate tensile loading:
  - This value was chosen to keep the stress within the **elastic range** of the material.
  - The resulting **Von Mises stress** on the gauge section is close to the **yield strength** of typical structural steels, validating the choice of displacement.

- The **reaction force summation** confirms expected tensile behavior:
  - The dominant force is in the **X-direction**, consistent with axial loading.

- These results confirm that the model behaves as expected under **linear elastic conditions**, and the stress distribution is valid for demonstrating near-yield behavior in a tensile test.

- Try changing the displacement value (e.g., 0.25 mm, 1.0 mm), mesh parameters and observe how the **Von Mises stress** and **reaction forces** scale.
- Note your conclusions about the linearity of the results and how they relate to material behavior.
- Consider plotting **stress vs. displacement** to visually confirm the linear relationship.



**Key Operations:**
- Interpret the results
- Exiting the processor
      """)


print("Simulation completed.")
mapdl.exit()