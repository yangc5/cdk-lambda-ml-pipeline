import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Stack,
    aws_lambda,
    aws_iam,
    aws_s3,
    aws_s3_deployment as s3deploy,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_codebuild as codebuild
)
from constructs import Construct

class CdkMlPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

# Grant training Lambda read write permissions for S3 bucket where data and model artifacts are stored
        s3_statement=aws_iam.PolicyStatement(
            actions=["s3:List*","s3:Get*","s3:PutObject","s3:PutObjectAcl","s3:DeleteObject"],
            resources=["arn:aws:s3:::cdk-ml-pipeline-iris", "arn:aws:s3:::cdk-ml-pipeline-iris/*"]
        )

# Training lambda
        training_lambda = aws_lambda.DockerImageFunction(
            self, "training-lambda",
            function_name="training-lambda",
            code=aws_lambda.DockerImageCode.from_image_asset(
                "./training_image_asset"
            ),
            memory_size=10240,
            timeout=Duration.seconds(900)
        )

# Attach S3 policy to Training Lambda execution role
        training_lambda.role.add_to_policy(s3_statement)
