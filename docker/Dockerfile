FROM condaforge/mambaforge:latest

LABEL description='DSWX-SWOT'

# For opencontainers label definitions, see:
#    https://github.com/opencontainers/image-spec/blob/master/annotations.md
LABEL org.opencontainers.image.title="dswx-swot"
LABEL org.opencontainers.image.description=""
LABEL org.opencontainers.image.authors="Marin Govorcin<marin.govorcin@jpl.nasa.gov>"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.url="https://github.com/opera-adt/dswx-swot"
LABEL org.opencontainers.image.source="https://github.com/opera-adt/dswx-swot"
LABEL org.opencontainers.image.documentation="https://github.com/opera-adt/dswx-swot"

# Dynamic lables to define at build time via `docker build --label`
# LABEL org.opencontainers.image.created=""
# LABEL org.opencontainers.image.version=""
# LABEL org.opencontainers.image.revision=""

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=true

# Install dependencies in a single RUN command
RUN apt-get update && apt-get install -y --no-install-recommends \
    git unzip vim && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# run commands in a bash login shell
SHELL ["/bin/bash", "-l", "-c"]

# Create non-root user/group with default inputs
ARG CONDA_UID=1000
ARG CONDA_GID=1000

RUN groupadd -g "${CONDA_GID}" --system opera_user && \
    useradd -l -u "${CONDA_UID}" -g "${CONDA_GID}" --system -d /home/ops -m  -s /bin/bash opera_user && \
    chown -R opera_user:opera_user /home/ops /opt

USER ${CONDA_UID}
WORKDIR /home/ops

# Copy files while preserving ownership
# https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#leverage-build-cach
COPY --chown=opera_user:opera_user environment.yml /home/ops/opera/environment.yml
COPY --chown=opera_user:opera_user . /home/ops/opera

# Ensure all files are read/write by the user
RUN chown -R opera_user:opera_user /home/ops && chmod -R 777 /home/ops


# Create the environment with mamba
RUN mamba env create -f /home/ops/opera/environment.yml && \
    conda clean -afy

ENV CONDA_DEFAULT_ENV=dswx-swot
ENV PATH="/opt/conda/envs/${CONDA_DEFAULT_ENV}/bin:$PATH"

# Install repository with pip
RUN python -m pip install --no-cache-dir /home/ops/opera
