# The devcontainer should use the developer target and run as root with podman
# or docker with user namespaces.
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION} as developer

# Add any system dependencies for the developer/build environment here
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Install GenTL producer
ARG MATRIX_VERSION=2.29.0
RUN curl -O http://static.matrix-vision.com/mvIMPACT_Acquire/${MATRIX_VERSION}/mvGenTL_Acquire-x86_64_ABI2-${MATRIX_VERSION}.tgz \
    && wget http://static.matrix-vision.com/mvIMPACT_Acquire/${MATRIX_VERSION}/install_mvGenTL_Acquire.sh \
    && bash install_mvGenTL_Acquire.sh

# Set up a virtual environment and put it in PATH
RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH

# The build stage installs the context into the venv
FROM developer as build
COPY . /context
WORKDIR /context
RUN pip install .

# The runtime stage copies the built venv into a slim runtime container
FROM python:${PYTHON_VERSION}-slim as runtime
# Add apt-get system dependecies for runtime here if needed
COPY --from=build /venv/ /venv/
ENV PATH=/venv/bin:$PATH

COPY --from=build opt/mvIMPACT_Acquire/ opt/mvIMPACT_Acquire/

# change this entrypoint if it is not the same as the repo
ENTRYPOINT ["genicam-fastcs"]
CMD ["--version"]
