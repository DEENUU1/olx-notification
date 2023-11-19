from aws_cdk import core as cdk
from aws_cdk import aws_lambda


class OlxNotificationStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        scraper = aws_lambda.Function(
            self,
            id="OlxNotification",
            code=aws_lambda.Code.from_asset("olx_notification/compute/"),
            handler="olx.lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_9
        )
