def validate(command):
    # basic check (extend later)
    if command["intent"] == "unknown":
        return True # Pass to executor to handle gracefully
    return True
