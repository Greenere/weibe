from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.nlp.v20190408 import nlp_client, models
import time

class Myanalysis:
    def __init__(self, param):
        self.param = param
        cred = credential.Credential("AKIDHL2YprWOo1IMCyov3B9sOl2GKAtOomcD", "WnpeEYdiZSEmvpZ3IJ9k6FCvPekgT1KR")
        httpProfile = HttpProfile()
        httpProfile.endpoint = "nlp.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = nlp_client.NlpClient(cred, "ap-guangzhou", clientProfile)

    def getparams(self, param):
        self.param = param

    def results(self):
        req = models.SentimentAnalysisRequest()
        params = '{"Flag":2,"Text":' + '\"' + self.param + '\"' + '}'
        req.from_json_string(params)
        resp = self.client.SentimentAnalysis(req)
        return eval(resp.to_json_string())

cred = credential.Credential("AKIDHL2YprWOo1IMCyov3B9sOl2GKAtOomcD", "WnpeEYdiZSEmvpZ3IJ9k6FCvPekgT1KR")
httpProfile = HttpProfile()
httpProfile.endpoint = "nlp.tencentcloudapi.com"
clientProfile = ClientProfile()
clientProfile.httpProfile = httpProfile
client = nlp_client.NlpClient(cred, "ap-guangzhou", clientProfile)

def Analysis(param):
    req = models.SentimentAnalysisRequest()
    params = '{"Flag":2,"Text":'+'\"'+param+'\"'+'}'
    req.from_json_string(params)
    resp = client.SentimentAnalysis(req)
    time.sleep(0.05)
    return eval(resp.to_json_string())['Positive']
