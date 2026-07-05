class CommsManager:
    @staticmethod
    def send_email(to_contact: str, rough_content: str = "") -> str:
        from engine.ai.email_writer import EmailWriter
        writer = EmailWriter()
        
        if not rough_content:
            return f"Email drafted to {to_contact}. Awaiting your dictation for the body."
            
        full_email = writer.compose_from_rough(rough_content, to_contact)
        # In a real scenario, we would use smtplib here.
        return f"Email sent to {to_contact}:\n\n{full_email}"

    @staticmethod
    def send_whatsapp(message: str, contact: str) -> str:
        # On a mobile device, this would hook into Android Intent or iOS Shortcuts.
        return f"Sending WhatsApp message to {contact}: {message}"

    @staticmethod
    def read_notifications() -> str:
        # On mobile, this would query the notification listener service.
        return "You have 3 unread messages from Tony Stark."
