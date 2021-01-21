import sys
import os

from pyspark.sql import SparkSession


if __name__ == "__main__":
	
	spark = SparkSession.builder \
		.appName("my_app") \
		.config("fs.s3a.access.key", os.environ.get('S3_ACCESS_KEY'))  \
		.config("fs.s3a.secret.key", os.environ.get('S3_SECRET_KEY'))  \
		.config("fs.s3a.impl","org.apache.hadoop.fs.s3a.S3AFileSystem")  \
		.config("fs.s3a.endpoint", "https://hb.bizmrg.com")  \
		.getOrCreate()

	S3_PATH = os.environ.get('S3_PATH')
			
	df = spark.read.csv(S3_PATH, header=True)
	df.show(10,0)
	spark.stop()