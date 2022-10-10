# BandSOS Platform
Experimented on the Bengal delta in Bangladesh, BanD-SOS aims to establish a pre-operational service for forecasting cyclonic flooding and the associated societal risk. This service will have two components: a forecast of the flooding hazard in real time when a tropical cyclone hits the coast, and a coupling of this forecast with a mapping of the vulnerability of the exposed populations.

This repository contains the softwares and scripts necessary for running the BandSOS platform. 

# How to use
1. Install the conda envrionment using the enviornment_[platform].yml file
2. Create the following folders - 
   1. config : the model configuration files
   2. fluxes : save directory for fluxes
   3. forecasts : save directory for forecasts
   4. scripts : other helper scripts
3. Run update_forecast.sh as daemon, separate process
4. Use the script bandsos.py to prepare the model simulation files
5. Use your preferred computing system - local, cluster to run the model. Take advantage of the helper scripts.