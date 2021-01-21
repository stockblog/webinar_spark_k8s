# Webinar_spark_k8s
Spark in Kubernetes

### We will install Spark Operator, test Spark on Kubernetes, build and launch our own custom images in Mail.ru Cloud Solutions
#### Tested with Kubernetes 1.17.4, Spark 3.0.1, Client VM Ubuntu 18.04 

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

### Create K8s cluster in mcs and download kubeconfig
Instruction: https://mcs.mail.ru/help/kubernetes/clusterfast

Kubernetes as a Service: https://mcs.mail.ru/app/services/containers/add/

### Install kubectl
https://mcs.mail.ru/help/ru_RU/k8s-start/connect-k8s

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

### Install Docker and log in to a Docker registry
https://docs.docker.com/engine/install/ubuntu/
https://docs.docker.com/engine/reference/commandline/login/
https://ropenscilabs.github.io/r-docker-tutorial/04-Dockerhub.html 

### Download spark
http://spark.apache.org/downloads.html
Please note. For this tutorial i am using spark-3.0.1-bin-hadoop3.2

Extract the Tarball
```console
tar -xvzf spark-3.0.1-bin-hadoop3.2.tgz

nano ~/.profile

export SPARK_HOME=~/spark-3.0.1-bin-hadoop3.2
alias spark-shell=”$SPARK_HOME/bin/spark-shell”

source ~/.profile
```



## Part 1. Spark operator installation

```console
helm repo add spark-operator https://googlecloudplatform.github.io/spark-on-k8s-operator
helm install my-release spark-operator/spark-operator --namespace spark-operator --create-namespace --set sparkJobNamespace=default --set webhook.enable=true

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
  resources: ["pods"]
  verbs: ["*"]
- apiGroups: [""]
  resources: ["services"]
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
git clone https://github.com/GoogleCloudPlatform/spark-on-k8s-operator spark-operator

kubectl apply -f spark-operator/examples/spark-pi.yaml      
kubectl get sparkapplications.sparkoperator.k8s.io
kubectl describe sparkapplications.sparkoperator.k8s.io spark-pi
kubectl get pods 
kubectl logs spark-pi-driver | grep 3.14
```

## Part 2. Running custom app

We will use docker-image-tool.sh and docker build context for this tool is $SPARK_HOME.
So we need to clone spark .py files inside $SPARK_HOME, so they will be accessible within docker image. 
You could read more about docker-image-tool.sh: https://spark.apache.org/docs/latest/running-on-kubernetes.html#docker-images
More information about docker build context: https://docs.docker.com/engine/reference/builder/
Additonal info about custom docker image for spark: https://www.waitingforcode.com/apache-spark/docker-images-apache-spark-applications/read 

### Clone repo with examples
```console
cd $SPARK_HOME
git clone https://github.com/stockblog/webinar_spark_k8s/custom_jobs custom_jobs

cd
git clone https://github.com/stockblog/webinar_spark_k8s/custom_jobs_yaml custom_jobs_yaml
```

### Build image
```console
export YOUR_DOCKER_REPO=
#example export YOUR_DOCKER_REPO=mcscloud


sudo /$SPARK_HOME/bin/docker-image-tool.sh -r $YOUR_DOCKER_REPO -t s3read_write_test -p ~/custom_jobs_yaml/Dockerfile build
sudo /$SPARK_HOME/bin/docker-image-tool.sh -r $YOUR_DOCKER_REPO -t s3read_write_test -p ~/custom_jobs_yaml/Dockerfile push
```

### Create Secret with credintials for accessing data in S3
```console
kubectl create secret generic s3-secret --from-literal=S3_ACCESS_KEY='PLACE_YOUR_S3_CRED_HERE' --from-literal=S3_SECRET_KEY='PLACE_YOUR_S3_CRED_HERE'
```

### Create ConfigMap for accessing data in S3
```console
kubectl create configmap s3path-config --from-literal=S3_PATH=s3a://s3-demo/evo_train_new.csv --from-literal=S3_WRITE_PATH=s3a://s3-demo/write/evo_train_csv/
```

### Launch spark job
```consile
cat <<EOF | kubectl apply -f -
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
metadata:
  name: s3read-write-test
  namespace: default
spec:
  type: Python
  pythonVersion: "3"
  mode: cluster
  image: mcscloud/spark-py:s3read_write_test
  imagePullPolicy: Always
  mainApplicationFile: local:///opt/spark/my_examples/s3read_write.py
  sparkVersion: "3.0.1"
  restartPolicy:
    type: OnFailure
    onFailureRetries: 3
    onFailureRetryInterval: 10
    onSubmissionFailureRetries: 5
    onSubmissionFailureRetryInterval: 20
  driver:
    cores: 1
    coreLimit: "1200m"
    memory: "512m"
    labels:
      version: 3.0.1
    serviceAccount: spark
    envFrom:
    - secretRef:
        name: s3-secret
    - configMapRef:
        name: s3path-config
  executor:
    cores: 1
    instances: 1
    memory: "512m"
    labels:
      version: 3.0.1
    envFrom:
    - secretRef:
        name: s3-secret
    - configMapRef:
        name: s3path-config    
EOF
```

### Monitoring execution and getting status of job
```
kubectl get sparkapplications.sparkoperator.k8s.io
kubectl describe sparkapplications.sparkoperator.k8s.io s3read-write-test
kubectl get pods
kubectl logs s3read-write-test-driver
kubectl get events
```


## Spark History Server

https://github.com/helm/charts/tree/master/stable/spark-history-server

```console
#create namespace for History Server
kubectl create ns spark-history-server

#create secret so History Server could write to S3
kubectl create secret generic s3-secret --from-literal=S3_ACCESS_KEY='PLACE_YOUR_S3_CRED_HERE' --from-literal=S3_SECRET_KEY='PLACE_YOUR_S3_CRED_HERE' -n spark-history-server

#create yaml file with config for History Server
#you should create bucket in S3 named spark-hs and directory inside bucket named spark-hs or change names in s3.logDirectory parameter
cat <<EOF >> values-hs.yaml -
s3:
  enableS3: true
  enableIAM: false
  logDirectory: s3a://spark-hs/spark-hs
  # accessKeyName is an AWS access key ID. Omit for IAM role-based or provider-based authentication.
  secret: s3-secret
  accessKeyName: S3_ACCESS_KEY
  # secretKey is AWS secret key. Omit for IAM role-based or provider-based authentication.
  secretKeyName: S3_SECRET_KEY
  endpoint: https://hb.bizmrg.com

gcs:
  enableGCS: false
  logDirectory: gs://spark-hs/

pvc:
  enablePVC: false

nfs:
  enableExampleNFS: false
EOF

helm repo add stable https://charts.helm.sh/stable

helm install -f values-hs.yaml my-spark-history-server stable/spark-history-server --namespace spark-history-server
```
