# Installation
The bandsos toolbox is written in python3, and tested in python v3.6+. The source-code is freely available under GPL-3
license at our [github repository](https://github.com/jamal919/bandsos-platform). The source-code can be obtained through
`git` using `git clone https://github.com/jamal919/bandsos-platform`, or directly downloading from the repository.

The toolbox is published at python package repository (pypi/pip) at https://pypi.org/project/bandsos/, and typically can
be installed through `pip install bandsos`. However, some modules depends on some external open-source tools, that might
be complicated to install in some system, and all the functionalities (mainly tile generation) might not work. A fully 
functioning version of the toolbox can be installed and used in several ways - 

* [system-wide installation](#system-wide-installation)
* [Conda/Anaconda installation](#condaanaconda-installation)
* [docker container](#stand-alone-installation)

## System-wide installation
bandsos toolbox relies on a moderate number of external packages and opensource softwares. Particularly, the toolbox 
relies on gdal - a command-line based geographical data processing toolbox - for postprocessing the model outputs to 
webtiles. The rest of the python packages are installable from the pip. Gdal is often 
available through the software distribution system of linux, but on windows it is particularly difficult to get it
working with the rest of the system and python. For this reason - *we strongly advice to use conda installation system*. 

To install the toolbox system-wide in linux, install `python`, `numpy`, `scipy`, `gdal-python`, `gdal`, `proj`, `xarray`, 
`netcdf4`, `f90nml`, `utide`, `rioxarray`, `beautifulsoup4`. Install as many packages from the system repository as 
possible, then the rest can be installed through pip using `pip install <packagename>` (where <packagename> is to be 
replaced with your needed package name).

The system-wide installation is tested while developing the [docker container](#docker-container). Please consult the
`Dockerfile` to see which packages were installed in a Ubuntu 22.04 LTS system.

## Conda/Anaconda installation
Conda is a python environment management system, which can install not only python-only programs (e.g., environments created
with venv) but also supplementary/required binary programs.

A brief installation procedure can be found here - https://docs.anaconda.com/anaconda/install/index.html.

## Docker container
Docker is a containerization technique to isolate the necessary dependency-components for running a software into an isolated
environment. Docker has the added benefit the ability to run in windows, linux, mac, or other ported platforms typically
without any change in the containarized system. It also allows easy deployment into cloud computing systems, or large
computing clusters very quickly.

Installation of the system using docker goes in two step - 
1. Installation of the docker software itself.
2. Installation of the bandsos platform, using `docker pull` command

First lets install docker software itself in your platform of choice - [Windows](#windows), 
### Windows
- Activate container hypervisor feature in BIOS for best performance.
- Activate `Subsystem for Linux` in Windows feature.
- Install `docker desktop` using the executable from https://docs.docker.com/engine/install/
- Note: You might need to update the `linux-kernel-package`, update if promted.

### Linux
- Install docker normally from https://docs.docker.com/engine/install/
- Activate `sudo systemctl start docker`
- Enable for load on startup `sudo systemctl enable docker`
- Add `docker` group: `sudo groupadd docker`
- Add the current user to the `docker` group : `sudo usermod -aG docker $USER`

## Run folder structure
```
- ROOTDIR
    |- config
    |- fluxes
        |- gfs
        |- hwrf
        |- jtwc
        |- discharge
    |- forecasts
    |- scripts
```
## How to run
- bandsos.py
- bandsos.env

```bash
docker run --rm --env-file=bandsos.env -v `pwd`/config:/bandsos/config -v `pwd`/fluxes:/bandsos/fluxes
```
