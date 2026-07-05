class EmailWriter:
    SYSTEM_PROMPT = """You are a professional email assistant. 
Convert rough input into polished, professional communication.
Keep it concise, warm, and appropriate. Return ONLY the email body."""
    
    def compose_from_rough(self, rough: str, recipient: str = "Sir/Ma'am") -> str:
        """
        Input:  "send mail to sir i cant attend class today"
        Output: "Dear Sir,\n\nI hope you are doing well. I would like 
                 to inform you that I will not be able to attend 
                 today's class. Thank you for your understanding.\n\nRegards"
        """
        from engine.ai.local_llm import LLMEngine
        
        # Extract just the message content
        rough_message = rough.lower().replace("send mail to", "").replace("send email to", "").strip()
        # Remove recipient prefix  
        parts = rough_message.split(' ', 1)
        if len(parts) > 1:
            rough_message = parts[1]
        
        enhanced = LLMEngine.enhance_text(
            rough_text=rough_message,
            context=f"professional email to {recipient}"
        )
        return f"Dear {recipient.title()},\n\n{enhanced}\n\nRegards"
    
    def correct_grammar(self, text: str) -> str:
        from engine.ai.local_llm import LLMEngine
        return LLMEngine.enhance_text(text, context="grammatically correct professional message")
