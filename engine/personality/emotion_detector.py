# engine/personality/emotion_detector.py
import re
from engine.personality.modes import JKModes

class EmotionDetector:
    """
    Analyzes user text sentiment to detect emotions:
    sad, stressed, excited, neutral, angry, anxious, happy
    and maps them to JK's modes.
    """
    
    # Simple keyword-based detection for fast offline/online processing
    EMOTION_KEYWORDS = {
        "sad": ["sad", "depressed", "failed", "crying", "upset", "lonely", "heartbroken"],
        "stressed": ["stressed", "overwhelmed", "pressure", "tired", "exhausted", "too much"],
        "excited": ["excited", "won", "passed", "yay", "amazing", "best", "awesome"],
        "anxious": ["anxious", "nervous", "scared", "panic", "worry", "worried", "fear", "calm down"],
        "angry": ["angry", "mad", "hate", "frustrated", "annoyed"],
        "happy": ["happy", "glad", "good", "great", "smile"]
    }

    @classmethod
    def detect_emotion(cls, text: str) -> dict:
        text_lower = text.lower()
        scores = {e: 0 for e in cls.EMOTION_KEYWORDS.keys()}
        
        words = re.findall(r'\b\w+\b', text_lower)
        for word in words:
            for emotion, keywords in cls.EMOTION_KEYWORDS.items():
                if word in keywords:
                    scores[emotion] += 1
                    
        # Check phrases
        if "calm down" in text_lower or "panic attack" in text_lower:
            scores["anxious"] += 3
            
        if "make me laugh" in text_lower or "tell a joke" in text_lower or "tell me a joke" in text_lower:
            # Special case to trigger comedy
            return {"emotion": "neutral", "confidence": 1.0, "mode": JKModes.COMEDY_MODE}

        if "teach me" in text_lower or "how to" in text_lower or "explain" in text_lower or "what is" in text_lower:
             return {"emotion": "learning", "confidence": 1.0, "mode": JKModes.MENTOR_MODE}

        max_emotion = max(scores, key=scores.get)
        max_score = scores[max_emotion]
        
        if max_score == 0:
            return {"emotion": "neutral", "confidence": 1.0, "mode": JKModes.NORMAL_MODE}
            
        # Map emotions to modes
        mode_mapping = {
            "sad": JKModes.SUPPORT_MODE,
            "stressed": JKModes.SUPPORT_MODE,
            "anxious": JKModes.HEALING_MODE,
            "excited": JKModes.HYPE_MODE,
            "happy": JKModes.NORMAL_MODE,
            "angry": JKModes.SUPPORT_MODE
        }
        
        # Calculate a pseudo-confidence score
        confidence = min(max_score * 0.33, 1.0)
        
        mode = mode_mapping.get(max_emotion, JKModes.NORMAL_MODE)
        
        return {
            "emotion": max_emotion,
            "confidence": confidence,
            "mode": mode
        }
