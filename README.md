# Webinar_spark_k8s

UPDATED for Spark 3.1.3

### We will install Spark Operator, test Spark on Kubernetes, build and launch our own custom images in VK Cloud
#### Tested with Kubernetes 1.20.4, Spark 3.1.3, Client VM Ubuntu 20.04 

## Running Spark on Kubernetes useful links

### Official doc
https://spark.apache.org/docs/latest/running-on-kubernetes.html

### Spark Operator
https://github.com/GoogleCloudPlatform/spark-on-k8s-operator

### Spark Operator quick start guide
https://github.com/GoogleCloudPlatform/spark-on-k8s-operator/blob/master/docs/quick-start-guide.md

### Spark Operator user guide
https://github.com/GoogleCloudPlatform/spark-on-k8s-operator/blob/master/docs/user-guide.md


### Helpful intro articles
https://www.lightbend.com/blog/how-to-manage-monitor-spark-on-kubernetes-introduction-spark-submit-kubernetes-operator

https://www.lightbend.com/blog/how-to-manage-monitor-spark-on-kubernetes-deep-dive-kubernetes-operator-for-spark

### Comparsion Spark perfomance on Yarn and Kubernetes
https://www.datamechanics.co/blog-post/apache-spark-performance-benchmarks-show-kubernetes-has-caught-up-with-yarn

### S7 data team experience with Spark on Kubernetes 
https://youtu.be/hQI-QYJXlVU?t=12317




## Prerequisites

### (Optional) Create host VM  
It would be easier to create a host VM in cloud  
All work in the cloud can be done from that VM  
You can install kubectl, Helm, Docker and all other things on this VM and don`t mess with your own local machine  

How to create VM: https://mcs.mail.ru/help/ru_RU/create-vm/vm-quick-create  
How to connect: https://mcs.mail.ru/help/ru_RU/vm-connect/vm-connect-nix  
Steps:  
1. Create VM  
2. Connect to VM with SSH  
3. Perform all steps described further in this instruction from this VM  

### Download dataset for S3 practice part
Dataset: https://disk.yandex.ru/d/gn19jm6mVBnwzQ  

### Create K8s cluster in VK Cloud and download kubeconfig
Instruction: https://mcs.mail.ru/help/kubernetes/clusterfast  
You may have trouble with Gatekeeper.   
So please delete it. https://mcs.mail.ru/docs/base/k8s/k8s-addons/k8s-gatekeeper/k8s-opa#udalenie

Kubernetes as a Service: https://mcs.mail.ru/app/services/containers/add/

### Install kubectl
https://mcs.mail.ru/docs/base/k8s/connect/kubectl

### Set path to kubeconfig for kubectl
```console
export KUBECONFIG=/replace_with_path/to_your_kubeconfig.yaml
```
### also it will be easier to work with kubectl while enabling autocomplete and using alias
```console
alias k=kubectl
source <(kubectl completion bash)
complete -F __start_kubectl k
```

### Install helm
https://helm.sh/docs/intro/install/  

### Install Docker and log into a Docker registry
https://docs.docker.com/engine/install/ubuntu/  
https://docs.docker.com/engine/reference/commandline/login/  
https://ropenscilabs.github.io/r-docker-tutorial/04-Dockerhub.html   

### Download spark 
This part used if you want to build your own image.

http://spark.apache.org/downloads.html  
Please note. For this tutorial i am using spark-3.1.3-bin-hadoop3.2

Extract the Tarball
```console
wget https://archive.apache.org/dist/spark/spark-3.1.3/spark-3.1.3-bin-hadoop3.2.tgz  

tar -xvzf spark-3.1.3-bin-hadoop3.2.tgz

nano ~/.profile

export SPARK_HOME=~/spark-3.1.3-bin-hadoop3.2
alias spark-shell=”$SPARK_HOME/bin/spark-shell”

source ~/.profile
```



## Part 1. Spark operator installation

```console
git clone https://github.com/GoogleCloudPlatform/spark-on-k8s-operator.git  

##Here we install specific version (1.1.25) because sometimes last versions has bugs.
helm install my-release spark-on-k8s-operator/charts/spark-operator-chart --namespace spark-operator --create-namespace --set webhook.enable=true --version 1.1.25  

#create service account, role and rolebinding for spark
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: spark-role
rules:
- apiGroups: [""]
  resources: ["*"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: spark-role-binding
  namespace: default
subjects:
- kind: ServiceAccount
  name: spark
  namespace: default
roleRef:
  kind: Role
  name: spark-role
  apiGroup: rbac.authorization.k8s.io
EOF
```

### Run demo example
```console
git clone https://github.com/stockblog/webinar_spark_k8s

kubectl apply -f webinar_spark_k8s/yamls_configs/spark-pi.yaml      
kubectl get sparkapplications.sparkoperator.k8s.io
kubectl describe sparkapplications.sparkoperator.k8s.io spark-pi
kubectl get pods 
kubectl logs spark-pi-driver | grep 3.1
```

If you get message like check that your cluster has 2 data-nodes (in VK UI) and try again.
Don't forget to delete previos one using "kubectl delete sparkapplication.sparkoperator.k8s.io/spark-pi"
```console
Initial job has not accepted any resources; check your cluster UI to ensure that workers are registered and have sufficient resources
```


## Part 2. Running custom app

We will use docker-image-tool.sh and docker build context for this tool is $SPARK_HOME.
So we need to clone spark .py files inside $SPARK_HOME, so they will be accessible within docker image.

You could read more about docker-image-tool.sh: https://spark.apache.org/docs/latest/running-on-kubernetes.html#docker-images

More information about docker build context: https://docs.docker.com/engine/reference/builder/

Additonal info about custom docker image for spark: https://www.waitingforcode.com/apache-spark/docker-images-apache-spark-applications/read 

### Clone repo with examples
```console
cd
git clone https://github.com/stockblog/webinar_spark_k8s/ webinar_spark_k8s

mv webinar_spark_k8s/custom_jobs/ $SPARK_HOME
```

### Build image
```console
export YOUR_DOCKER_REPO=
#example export YOUR_DOCKER_REPO=mcscloud


sudo /$SPARK_HOME/bin/docker-image-tool.sh -r $YOUR_DOCKER_REPO -t spark_k8s_intel -p ~/webinar_spark_k8s/yamls_configs/Dockerfile build
sudo /$SPARK_HOME/bin/docker-image-tool.sh -r $YOUR_DOCKER_REPO -t spark_k8s_intel -p ~/webinar_spark_k8s/yamls_configs/Dockerfile push
```

### Create Secret with credintials for accessing data in S3
You can obtain credintials for S3 access and create buckets with this help:
https://mcs.mail.ru/help/ru_RU/s3-start/s3-account 
https://mcs.mail.ru/help/ru_RU/s3-start/create-bucket  
Attention: create simple bucket name without _ or any special symbols. Because sometimes there are strange glitches with special symbols in bucket names.
```console
kubectl create secret generic s3-secret --from-literal=S3_ACCESS_KEY='PLACE_YOUR_S3_CRED_HERE' --from-literal=S3_SECRET_KEY='PLACE_YOUR_S3_CRED_HERE'
```

### Create ConfigMap for accessing data in S3
```console
#REPLACE S3_PATH AND S3_WRITE_PATH WITH YOUR PARAMETERS
kubectl create configmap s3path-config --from-literal=S3_PATH='s3a://s3-demo/evo_train_new.csv' --from-literal=S3_WRITE_PATH='s3a://s3-demo/write/evo_train_csv/'
```

### Launch spark job
```console
#choose one of example yamls in directory yamls_configs, edit yaml, add your parameters such as docker repo, image, path to files in s3
kubectl apply -f ~/webinar_spark_k8s/yamls_configs/s3read_write_with_secret_cfgmap.yaml
```

### Monitoring execution and getting status of job
```
kubectl get sparkapplications.sparkoperator.k8s.io
kubectl describe sparkapplications.sparkoperator.k8s.io s3read-write-test
kubectl get pods
kubectl logs pod_name
kubectl get events
```


## Spark History Server

https://github.com/helm/charts/tree/master/stable/spark-history-server

### Install Spark History Server
```console
#create namespace for History Server
kubectl create ns spark-history-server

#create secret so History Server could write to S3
kubectl create secret generic s3-secret --from-literal=S3_ACCESS_KEY='PLACE_YOUR_S3_CRED_HERE' --from-literal=S3_SECRET_KEY='PLACE_YOUR_S3_CRED_HERE' -n spark-history-server

#create yaml file with config for History Server
#you should create bucket in S3 named spark-hs and directory inside bucket named spark-hs or change names in s3.logDirectory parameter

helm repo add stable https://charts.helm.sh/stable
#Edit values-hs.yaml. You should specify your logDirectory param.
helm install -f ~/webinar_spark_k8s/yamls_configs/values-hs.yaml my-spark-history-server stable/spark-history-server --namespace spark-history-server
```

### Get External IP of History Server
```console
kubectl get service -n spark-history-server
```


### Launch Spark app with History Server support
```console
#Edit s3_hs_server_test.yaml before launch. Fill with your own params.
kubectl apply -f ~/webinar_spark_k8s/yamls_configs/s3_hs_server_test.yaml
```
Go to external IP of History Server and check logs of your spark app
WARNING: In prod you should not expose your Spark History Server to all internet.
Use service type ClusterIp with VPNaaS or other solutions.


