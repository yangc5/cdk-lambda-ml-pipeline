FROM public.ecr.aws/lambda/python:3.9

RUN yum update -y

RUN pip3 install numpy==1.23.2 \
    pandas==1.4.3 \
    scikit-learn==1.1.2

COPY training.py .

CMD ["training.handler"]
