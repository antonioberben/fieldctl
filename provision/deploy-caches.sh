#!/bin/sh

nerdctl run -d \
    --restart=always \
    -v $(pwd)/registry/config-docker.yml:/etc/docker/registry/config.yml \
    -v $(pwd)/registry/data/docker:/var/lib/registry \
    -p 5001:5000 \
    --name "k3s-cache-docker" registry:2

nerdctl run -d \
    --restart=always \
    -v $(pwd)/registry/config-gcr.yml:/etc/docker/registry/config.yml \
    -v $(pwd)/registry/data/gcr:/var/lib/registry \
    -p 5002:5000 \
    --name "k3s-cache-gcr" registry:2

nerdctl run -d \
    --restart=always \
    -v $(pwd)/registry/config-k8s.yml:/etc/docker/registry/config.yml \
    -v $(pwd)/registry/data/k8s:/var/lib/registry \
    -p 5003:5000 \
    --name "k3s-cache-k8s" registry:2

nerdctl run -d \
    --restart=always \
    -v $(pwd)/registry/config-quay.yml:/etc/docker/registry/config.yml \
    -v $(pwd)/registry/data/quay:/var/lib/registry \
    -p 5004:5000 \
    --name "k3s-cache-quay" registry:2

nerdctl run -d \
    --restart=always \
    -v $(pwd)/registry/data/local-registry:/var/lib/registry \
    -p 5005:5000 \
    --name "k3s-local-registry" registry:2

sudo cp $(pwd)/registry/registries.yaml /etc/rancher/k3s/registries.yaml

sudo systemctl restart k3s