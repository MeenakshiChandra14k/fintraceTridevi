def raise_alert(reason, txn):

    print("\n🚨 FRAUD ALERT 🚨")

    print(f"Reason: {reason}")

    print(f"Sender: {txn['nameOrig']}")

    print(f"Receiver: {txn['nameDest']}")

    print(f"Amount: {txn['amount']}")