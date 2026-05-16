def detect_velocity(transaction):

    """
    Simple velocity fraud detection.
    """

    amount = transaction.get("amount", 0)

    if amount > 100000:

        return {
            "alert": "High Velocity Transaction",
            "amount": amount
        }

    return None