from aws_cdk import core

from olx_notification.olx_notification_stack import OlxNotificationStack

app = core.App()
OlxNotificationStack(app, "OlxNotificationStack",

                     )

app.synth()
