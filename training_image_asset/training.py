import numpy as np
import pandas as pd
import boto3
import sklearn
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn import metrics
import pickle
import datetime

def handler(event, context):
    s3 = boto3.resource('s3')
    bucket="cdk-ml-pipeline-iris"
    key="data/Iris.csv"
    s3.Bucket(bucket).download_file(key, "/tmp/Iris.csv")

    iris = pd.read_csv("/tmp/Iris.csv")

    train, test = train_test_split(iris, test_size = 0.3)
    # in this our main data is split into train and test
    # the attribute test_size=0.3 splits the data into 70% and 30% ratio. train=70% and test=30%

    train_X = train[['SepalLengthCm','SepalWidthCm','PetalLengthCm','PetalWidthCm']]# taking the training data features
    train_y=train.Species# output of our training data
    test_X= test[['SepalLengthCm','SepalWidthCm','PetalLengthCm','PetalWidthCm']] # taking test data features
    test_y =test.Species   #output value of test data

    model=KNeighborsClassifier(n_neighbors=3) #this examines 3 neighbours for putting the new data into a class
    model.fit(train_X,train_y)
    prediction=model.predict(test_X)
    print('The accuracy of the KNN is',metrics.accuracy_score(prediction,test_y))

    filename='finalized_model.sav'
    pickle.dump(model, open('/tmp/finalized_model.sav', 'wb'))

    t = datetime.datetime.now()
    path="models/"+t.strftime('%m-%d-%Y %H-%M-%S')+"/"+filename
    latest_path="models/"+"latest/"+filename

    s3.Bucket(bucket).upload_file('/tmp/finalized_model.sav', path)
    s3.Bucket(bucket).upload_file('/tmp/finalized_model.sav', latest_path)

    print("Successfully uploaded trained model to S3 "+bucket)
