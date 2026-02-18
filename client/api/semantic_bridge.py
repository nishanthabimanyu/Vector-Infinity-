
import json
from datetime import datetime

class SemanticBridge:
    """
    Refines raw astronomical vectors into semantic 'Context Packets' 
    for LLM analysis (Mythology, History, Astrology).
    """
    
    def __init__(self, ephemeris_reader=None):
        self.reader = ephemeris_reader

    def generate_context_packet(self, match_data: dict) -> dict:
        """
        Hydrates a match event with richer context.
        """
        # 1. Basic Info
        packet = {
            "timestamp": match_data.get('date'),
            "julian_date": match_data.get('jd'),
            "probability_score": match_data.get('probability'),
            "meta": {
                "source": "Vector Infinity // Chronos Engine",
                "engine": "JPL DE441"
            }
        }
        
        # 2. Heuristic Event Classification (if not provided)
        # In a real impl, we'd pass the Constraint object to know 'Conjunction' vs 'Eclipse'
        # For now, we infer or use a generic 'Significant Alignment' tag
        packet["event_type"] = "ASTRONOMICAL_ALIGNMENT" 
        
        # 3. Add prompt hints
        packet["prompt_hints"] = [
            "Analyze historical events around this date.",
            "Check for corresponding eclipses or comets in ancient records.",
            "Interpret the astrological significance of this planetary configuration."
        ]
        
        return packet

    def format_prompt(self, packet: dict) -> str:
        """
        Converts packet to a natural language prompt.
        """
        date = packet['timestamp']
        jd = packet['julian_date']
        
        return (f"Analyze the following astronomical event detected by the physics engine:\n"
                f"Date: {date} (JD {jd:.2f})\n"
                f"Event Probability: {packet['probability_score']:.1%}\n\n"
                f"Task:\n"
                f"1. Identify any significant historical events occurring within +/- 2 years of this date.\n"
                f"2. Describe the astrological or mythological significance of this alignment from a geocentric perspective.\n"
                f"3. Verify if this corresponds to a known Solar/Lunar eclipse or planetary massing.")
