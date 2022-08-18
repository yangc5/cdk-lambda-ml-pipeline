import os
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
    data_and_model_bucket="cdk-ml-pipeline-iris"
    key="data/Iris.csv"
    s3.Bucket(data_and_model_bucket).download_file(key, "/tmp/Iris.csv")

    iris = pd.read_csv("/tmp/Iris.csv")

    train, test = train_test_split(iris, test_size = 0.3)
    # in this our main data is split into train and test
    # the attribute test_size=0.3 splits the data into 70% and 30% ratio. train=70% and test=30%

    train_X = train[['SepalLengthCm','SepalWidthCm','PetalLengthCm','PetalWidthCm']]# taking the training data features
    train_y=train.Species# output of our training data
    test_X= test[['SepalLengthCm','SepalWidthCm','PetalLengthCm','PetalWidthCm']] # taking test data features
    test_y =test.Species   #output value of test data

    # load pre trained model
    # model_key="models/latest/finalized_model.sav"
    # s3.Bucket(data_and_model_bucket).download_file(model_key, "/tmp/finalized_model.sav")

    model=pickle.load(open("finalized_model.sav", "rb"))
    prediction=model.predict(test_X)
    print('The accuracy of the KNN is',metrics.accuracy_score(prediction,test_y))

    prediction_csv = pd.DataFrame(prediction, columns=['prediction']).to_csv('/tmp/prediction.csv')

    t = datetime.datetime.now()
    path="inference-results/"+t.strftime('%m-%d-%Y %H-%M-%S')+"/prediction.csv"

    s3.Bucket(os.environ['INFERENCE_RESULTS_BUCKET']).upload_file('/tmp/prediction.csv', path)
