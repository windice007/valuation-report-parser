#!/bin/bash
version=$(python vrp/run.py --version)
echo "Publish tools-vrp:$version"

echo "Step1:Generate executable application."
pyinstaller -F -n vrp vrp/run.py

echo "Step2:Publish to nexus."
flit publish --repository nexus

echo "Step3:Build image"
image=harbor.iquantex.com/data-gateway/vrp:$version
docker build -t $image .
docker push $image
docker tag $image harbor.iquantex.com/data-gateway/vrp:latest
docker push harbor.iquantex.com/data-gateway/vrp:latest
