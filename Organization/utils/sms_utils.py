import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


def send_sms_code(phone, code):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")

    api_instance = sib_api_v3_sdk.TransactionalSMSApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    # ✅ MUST MATCH YOUR DLT TEMPLATE EXACTLY
    message = f"Your OTP for mobile number verification is {code}. It is valid for 5 minutes. Do not share this OTP with anyone. – Team Yuktic"

    sms = sib_api_v3_sdk.SendTransacSms(
        sender=os.getenv("BREVO_SENDER"),   
        recipient=phone,                   
        content=message,
        type="transactional"
    )

    try:
        response = api_instance.send_transac_sms(sms)
        print("SMS SENT:", response)
        return True
    except ApiException as e:
        print("SMS FAILED:", e)
        return False