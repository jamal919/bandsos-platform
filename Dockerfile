# --- STAGE 1: Builder ---
FROM debian:bookworm-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update \
    && apt-get install -y libnetcdf-dev libnetcdff-dev gcc gfortran g++ libopenmpi-dev openmpi-bin git cmake python3 python-is-python3

# Build SCHISM
RUN git clone https://github.com/schism-dev/schism /schism \
    && cd /schism && git checkout 9cdc9bb \
    && mkdir build && cd build \
    && cmake ../src -DTVD_LIM=VL \
    && make -j$(nproc) \
    && cmake ../src -DTVD_LIM=VL -DUSE_WWM=on \
    && make -j$(nproc)

# Compile tidefac
COPY . /tmp/bandsos-platform
RUN cd /tmp/bandsos-platform/scripts && gfortran -o tidefac tide_fac.f

# --- STAGE 2: Production ---
FROM debian:bookworm-slim

# Timezone and environment
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime && echo ${TZ} > /etc/timezone

# Install ONLY runtime libraries and python
# Note: --no-install-recommends keeps the image lean
RUN apt-get update && apt-get install -y libnetcdf19 libnetcdff7 openmpi-bin git wget \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Miniforge
ENV CONDA_DIR=/opt/conda
RUN wget --quiet "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh" -O /tmp/miniforge.sh && \
    /bin/bash /tmp/miniforge.sh -b -p /opt/conda && \
    rm /tmp/miniforge.sh

# Put conda in PATH
# ENV PROJ_DATA=/usr/share/proj
ENV PATH=$CONDA_DIR/bin:$PATH

# Conda environment
RUN conda install -y -n base \
    python==3.13 \
    numpy pandas netcdf4 xarray dask \
    gdal cartopy rasterio rioxarray \
    utide cmocean  f90nml \
    ghapi==1.1.0 \
    f90nml herbie-data \
    && conda clean -afy

# Copy executables from the builder stage
COPY --from=builder /schism/build/bin/* /usr/local/bin/
COPY --from=builder /schism/build/lib/* /usr/local/lib/
COPY --from=builder /schism/build/include/* /usr/local/inlucde/
COPY --from=builder /tmp/bandsos-platform/scripts/tidefac /usr/local/bin/

# Install toolbox
COPY . /opt/bandsos-platform
RUN cd /opt/bandsos-platform && pip install --break-system-packages .

# Entrypoint
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

WORKDIR /mnt
CMD ["/bin/bash"]
