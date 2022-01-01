#!/bin/sh

echo Install metalllb
sudo k3s kubectl apply -f metallb/metallb-namespace.yaml
sudo k3s kubectl apply -f metallb/metallb.yaml
sudo k3s kubectl create secret generic -n metallb-system memberlist --from-literal=secretkey="$(openssl rand -base64 128)"

cat << EOF | sudo k3s kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
    namespace: metallb-system
    name: config
data:
  config: |
    address-pools:
    - name: default
      protocol: layer2
      addresses:
      - 192.168.105.10-192.168.105.254
EOF