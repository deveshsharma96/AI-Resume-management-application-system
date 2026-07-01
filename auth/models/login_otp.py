


from Organization.models.otp import OTP

class LoginOTP:
    """
    Wrapper for login OTPs using the unified OTP table.
    """

    @staticmethod
    def create_otp(user_type, user_email, expiry_minutes=5):
        return OTP.create(
            email=user_email,
            otp_type='login',
            expiry_minutes=expiry_minutes
        )

    @staticmethod
    def verify_otp(user_email, otp_code):
        return OTP.verify(email=user_email, otp=otp_code, otp_type='login')
