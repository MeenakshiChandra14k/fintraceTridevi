def detect_mule_accounts(transaction):

    """
    Simple mule account detection logic.
    """

    amount = transaction.get("amount", 0)

    sender = transaction.get("nameOrig")

    receiver = transaction.get("nameDest")

    # Basic suspicious transaction rule
    if amount > 50000:

        return {
            "alert": "Possible Mule Account Activity",
            "sender": sender,
            "receiver": receiver,
            "amount": amount
        }

    return None