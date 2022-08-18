import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Stack,
    aws_lambda,
    aws_iam,
    aws_ecr as ecr,
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

# Read write permissions for S3 bucket where data and model artifacts are stored
        model_artifacts_bucket_read_write_statement=aws_iam.PolicyStatement(
            actions=["s3:List*","s3:Get*","s3:PutObject","s3:PutObjectAcl","s3:DeleteObject"],
            resources=["arn:aws:s3:::cdk-ml-pipeline-iris", "arn:aws:s3:::cdk-ml-pipeline-iris/*"]
        )

# Read only permission for data and model artifacts bucket
        model_artifacts_bucket_read_only_statement=aws_iam.PolicyStatement(
            actions=["s3:List*","s3:Get*"],
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
        training_lambda.role.add_to_policy(model_artifacts_bucket_read_write_statement)

# S3 bucket for inference results during inferencing process
        inference_results_bucket = aws_s3.Bucket(self, "inference-results-bucket", bucket_name="cdk-ml-pipeline-iris-model-inference-results-bucket",versioned=True)

# Inference Lambda execution role
        inference_lambda_execution_role = aws_iam.Role(self,
            'inference-lambda-execution-role',
            assumed_by=aws_iam.CompositePrincipal(
                aws_iam.ServicePrincipal('lambda.amazonaws.com')
            ),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ])

        inference_results_bucket.grant_read_write(inference_lambda_execution_role)
        inference_lambda_execution_role.add_to_policy(model_artifacts_bucket_read_only_statement)

# Inference Lambda image ECR
        inference_ecr= ecr.Repository(self, "inference-ecr", repository_name="inference-ecr")

# S3 bucket for CodeBuild artifacts including buildspec.yml
        codebuild_artifacts_bucket = aws_s3.Bucket(self, "codebuild-bucket", bucket_name="cdk-ml-pipeline-codebuild-artifacts-bucket",versioned=True)

# inference_image_codebuild project
        inference_image_codebuild_bucket_deployment = s3deploy.BucketDeployment(self, "inference-image-codebuild-artifacts-bucket-deployment",
            sources=[s3deploy.Source.asset("inference_image_codebuild"), s3deploy.Source.asset("inference_lambda")],
            destination_bucket=codebuild_artifacts_bucket,
            destination_key_prefix="inference-image-codebuild"
        )

        inference_image_codebuild_s3_source = codebuild.Source.s3(
            bucket=codebuild_artifacts_bucket,
            path="inference-image-codebuild/"
        )

        inference_image_codebuild_project = codebuild.Project(self, "inference-image-codebuild-project",
            project_name="inference-image-codebuild-project",
            source=inference_image_codebuild_s3_source,
            environment=codebuild.BuildEnvironment(
                privileged=True
            ),
            environment_variables={
                "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(
                    value=cdk.Aws.ACCOUNT_ID
                ),
                "IMAGE_REPO_NAME": codebuild.BuildEnvironmentVariable(
                    value=inference_ecr.repository_name
                )
            }
        )

        inference_image_codebuild_project.role.add_to_policy(model_artifacts_bucket_read_only_statement)
        codebuild_artifacts_bucket.grant_read(inference_image_codebuild_project.role)
        inference_ecr.grant_pull_push(inference_image_codebuild_project.role)

# create_or_update_inference_lambda_codebuild project
        create_or_update_inference_lambda_codebuild_bucket_deployment = s3deploy.BucketDeployment(self, "create-or-update-inference-lambda-codebuild-artifacts-bucket-deployment",
            sources=[s3deploy.Source.asset("create_or_update_inference_lambda_codebuild")],
            destination_bucket=codebuild_artifacts_bucket,
            destination_key_prefix="create-or-update-inference-image-codebuild"
        )

        create_or_update_inference_lambda_codebuild_s3_source = codebuild.Source.s3(
            bucket=codebuild_artifacts_bucket,
            path="create-or-update-inference-image-codebuild/"
        )

        create_or_update_inference_lambda_project = codebuild.Project(self, "create-or-update-inference-lambda-project",
            project_name="create-or-update-inference-lambda-project",
            source=create_or_update_inference_lambda_codebuild_s3_source,
            environment_variables={
                "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(
                    value=cdk.Aws.ACCOUNT_ID
                ),
                "IMAGE_REPO_NAME": codebuild.BuildEnvironmentVariable(
                    value=inference_ecr.repository_name
                ),
                "INFERENCE_IMAGE_URI":codebuild.BuildEnvironmentVariable(
                    value=cdk.Aws.ACCOUNT_ID+".dkr.ecr."+cdk.Aws.REGION+".amazonaws.com/"+inference_ecr.repository_name
                ),
                "INFERENCE_RESULTS_BUCKET":codebuild.BuildEnvironmentVariable(
                    value=inference_results_bucket.bucket_name
                ),
                "INFERENCE_LAMBDA_EXECUTION_ROLE_ARN":codebuild.BuildEnvironmentVariable(
                    value=inference_lambda_execution_role.role_arn
                )
            }
        )

        codebuild_artifacts_bucket.grant_read(create_or_update_inference_lambda_project.role)

        create_or_update_inference_lambda_project.role.attach_inline_policy(aws_iam.Policy(self, "inference-lambda-update-policy",
            statements=[
                aws_iam.PolicyStatement(
                    actions=["lambda:GetFunction", "lambda:CreateFunction","lambda:UpdateFunctionCode"],
                    resources=["arn:aws:lambda:"+cdk.Aws.REGION+":"+cdk.Aws.ACCOUNT_ID+":function:inference-lambda"]
                ),
                aws_iam.PolicyStatement(
                    actions=["iam:GetRole", "iam:PassRole"],
                    resources=[inference_lambda_execution_role.role_arn]
                )
            ]
        ))

        create_or_update_inference_lambda_project.role.attach_inline_policy(aws_iam.Policy(self, "inference-lambda-update-ecr-access-policy",
            statements=[
                aws_iam.PolicyStatement(
                    actions=["ecr:*"],
                    resources=[inference_ecr.repository_arn]
                ),
                aws_iam.PolicyStatement(
                    actions=["ecr:GetAuthorizationToken"],
                    resources=["*"]
                )
            ]
        ))
