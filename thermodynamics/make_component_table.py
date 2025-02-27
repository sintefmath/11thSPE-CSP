#!/usr/bin/env python3

""" Generate tables for component fluid properties.

The tables are generated using the NIST (National Institute of Standards
and Technology) Standard Reference Database Number 69
(https://doi.org/10.18434/T4D303).

Copyright for NIST Standard Reference Data is governed by the Standard
Reference Data Act (https://www.nist.gov/srd/public-law).

######################################################################
In case you are using this the data generated with this script
please cite the following publications:

P.J. Linstrom and W.G. Mallard, Eds.,
NIST Chemistry WebBook, NIST Standard Reference Database Number 69,
National Institute of Standards and Technology, Gaithersburg MD, 20899,
https://doi.org/10.18434/T4D303, (retrieved [insert date]).
######################################################################

The enthalpy values provided by NIST are given with respect to the IIR convention
reference state: the enthalpy is set to 200000 J/kg at 0°C for the saturated liquid.
"""

from io import StringIO
import argparse
import urllib
import requests  # pylint: disable=import-error
import numpy as np  # pylint: disable=import-error

parser = argparse.ArgumentParser(
    description="This script generates tables for H2O and CO2 fluid properties \n"
    "(density and enthalpy) using the NIST Chemistry WebBook.\n"
)
parser.add_argument(
    "-t1", "--min_temp", required=True, type=float, help="The minimum temperature in degree Celcius."
)
parser.add_argument(
    "-t2", "--max_temp", required=True, type=float, help="The maximum temperature in degree Celcius."
)
parser.add_argument(
    "-nt",
    "--n_temp",
    required=True,
    type=int,
    help="The number of temperature sampling points."
    "min_temp is the first sampling point, max_temp the last.",
)
parser.add_argument(
    "-p1", "--min_press", required=True, type=float, help="The minimum pressure in Pascal."
)
parser.add_argument(
    "-p2", "--max_press", required=True, type=float, help="The maximum pressure in Pascal."
)
parser.add_argument(
    "-np",
    "--n_press",
    required=True,
    type=int,
    help="The number of pressure sampling points."
    "min_press is the first sampling point, max_press the last.",
)
parser.add_argument(
    "-c", "--comp_name", required=True, help="The component name, either 'CO2' or 'H2O'."
)
cmdArgs = vars(parser.parse_args())


minTemp = cmdArgs["min_temp"]
maxTemp = cmdArgs["max_temp"]
nTemp = cmdArgs["n_temp"]
if nTemp == 1:
    delta_temperature = 0
else:
    delta_temperature = (maxTemp - minTemp) / (nTemp - 1)

minPress = cmdArgs["min_press"]
maxPress = cmdArgs["max_press"]
nPress = cmdArgs["n_press"]
if nPress < 2:
    print("n_press needs to be at least 2.")
    exit()
delta_pressure = (maxPress - minPress) / (nPress - 1)

compName = cmdArgs["comp_name"]
fileName = f"{compName.lower()}values.csv"
outFile = open(fileName, "w")
outFile.write(f"# This autogenerated file contains thermodynamical properties of {compName}.\n")
outFile.write("# The data has been obtained by querying the NIST Chemistry WebBook https://doi.org/10.18434/T4D303.\n#\n")
outFile.write("# Concerning temperature and pressure ranges, the following parameters have been used:\n")
outFile.write(f"# min temperature = {minTemp}, max temperature = {maxTemp}, #temperature sampling points = {nTemp}\n")
outFile.write(f"# min pressure = {minPress}, max pressure = {maxPress}, #pressure sampling points = {nPress}\n#\n")
outFile.write("# temperature [°C],     pressure [Pa],   density [kg/m3],  viscosity [Pa.s],   enthalpy [J/kg]\n")

# get the data
for i in range(cmdArgs["n_temp"]):
    temperature = cmdArgs["min_temp"] + i * delta_temperature
    query = {
        "Action": "Data",
        "Wide": "on",
        "ID": "C7732185" if cmdArgs["comp_name"] == "H2O" else "C124389",
        "Type": "IsoTherm",
        "Digits": "12",
        "PLow": str(cmdArgs["min_press"]),
        "PHigh": str(cmdArgs["max_press"]),
        "PInc": str(delta_pressure),
        "T": str(temperature),
        "RefState": "DEF",
        "TUnit": "C",
        "PUnit": "Pa",
        "DUnit": "kg/m3",
        "HUnit": "kJ/kg",
        "WUnit": "m/s",
        "VisUnit": "uPas",
        "STUnit": "N/m",
    }
    response = requests.get(
        "https://webbook.nist.gov/cgi/fluid.cgi?" + urllib.parse.urlencode(query)
    )
    response.encoding = "utf-8"
    text = response.text
    phase = np.genfromtxt(StringIO(text), delimiter="\t", dtype=str, usecols=[-1], skip_header=1)
    values = np.genfromtxt(StringIO(text), delimiter="\t", names=True)

    # NIST provides additional samples at the transition points (if there is a
    # phase transition within the requested data range). Since the code which
    # uses the tables generated by this script can't deal with these additional
    # sample points, they are removed.
    phaseBoundaryIndices = []
    for j in range(1, len(phase) - 1):
        if phase[j] != phase[j + 1]:
            phaseBoundaryIndices += [j, j + 1]

    pressure = np.delete(values["Pressure_Pa"], phaseBoundaryIndices)
    density = np.delete(values["Density_kgm3"], phaseBoundaryIndices)
    viscosity = np.delete(values["Viscosity_uPas"], phaseBoundaryIndices)
    # transform unit (1e-6.Pa.s -> Pa.s)
    viscosity *= 1e-6
    enthalpy = np.delete(values["Enthalpy_kJkg"], phaseBoundaryIndices)
    # transform unit (kJ/kg -> J/kg)
    enthalpy *= 1000

    for p, rho, mu, h in zip(pressure, density, viscosity, enthalpy):
        outFile.write(f" {temperature:.11e}, {p:.11e}, {rho:.11e}, {mu:.11e}, {h:.11e}\n")

print(f"A file {fileName} has been generated.")
