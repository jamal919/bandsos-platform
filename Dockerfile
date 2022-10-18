FROM ubuntu:22.04

# timezone fixing, does not impact the functionalities of the docker
ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime && echo ${TZ} > /etc/timezone

# basic packages
RUN apt-get update\
    && apt-get install -y libnetcdf-dev libnetcdff-dev mpich git cmake python-is-python3 \
    && apt-get clean

# create pschism_TVD-VL and pschism_WWM_TVD-VL executables
RUN git clone https://github.com/schism-dev/schism \
    && cd /schism \
    && git checkout master \
    && mkdir build && cd build \
    && cmake ../src -DTVD_LIM=VL -DCMAKE_Fortran_FLAGS_RELEASE="-O2 -fuse-ld=gold -ffree-line-length-none -fallow-argument-mismatch" \
    && make \
    && cmake ../src -DTVD_LIM=VL -DUSE_WWM=on -DCMAKE_Fortran_FLAGS_RELEASE="-O2 -fuse-ld=gold -ffree-line-length-none -fallow-argument-mismatch" \
    && make \
    && cp -v bin/* /usr/local/bin \
    && cp -v lib/* /usr/local/lib \
    && cp -v include/* /usr/local/include \
    && rm -rf /schism

# install python distribution and pip packages
RUN apt-get update \
    && apt-get install -y python3-numpy python3-pandas python3-xarray python3-gdal gdal-bin python3-cartopy python3-rasterio \
    && apt-get clean
RUN pip install utide cmocean rioxarray
ENV PROJ_DATA=/usr/share/proj

# install bandsos-platform toolbox
COPY . /bandsos-platform
RUN cd bandsos-platform \
    && pip install . \
    && cd scripts \
    && gfortran -o tidefac tide_fac.f \
    && cp -v tidefac /usr/bin \
    && rm -rf /bandsos-platform

WORKDIR /mnt

CMD ["/bin/bash"]